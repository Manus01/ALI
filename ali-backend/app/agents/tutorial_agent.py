import os
import json
import datetime
import time
import logging
import re
from typing import Dict, List, Any, Optional
from app.services.ai_studio import CreativeService
from app.services.llm_factory import get_model
from app.core.security import db
from firebase_admin import firestore

# Configure Logger
logger = logging.getLogger("ali_platform.agents.tutorial_agent")

def extract_json_safe(text: str) -> Dict[str, Any]:
    """
    Robustly extracts JSON from an LLM response string.
    Handles markdown code blocks (```json ... ```) or raw JSON.
    """
    try:
        # 1. Try cleaning markdown syntax first
        clean_text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except json.JSONDecodeError:
        # 2. Fallback: Use Regex to find the first JSON object '{...}'
        try:
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except:
            pass
        # 3. Final Fallback: Raise error to be caught by caller
        raise ValueError(f"Failed to parse JSON from response: {text[:100]}...")

def validate_quiz_data(assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validates and corrects Quiz Data to prevent Frontend crashes.
    Ensures 'correct_answer' is a valid integer index.
    """
    for block in assets:
        if block['type'] in ['quiz_single', 'quiz_final']:
            to_process = [block] if block['type'] == 'quiz_single' else block.get('questions', [])
            
            for q in to_process:
                options = q.get('options', [])
                ans = q.get('correct_answer')
                
                # Correction 1: Convert string number to int
                if isinstance(ans, str) and ans.isdigit():
                    q['correct_answer'] = int(ans)
                    
                # Correction 2: Bounds Check
                final_ans = q.get('correct_answer')
                if not isinstance(final_ans, int) or final_ans < 0 or final_ans >= len(options):
                    logger.warning(f"⚠️ Invalid Quiz Answer detected: {final_ans} for options {len(options)}. Defaulting to 0.")
                    q['correct_answer'] = 0 # Safety Fallback
                    
    return assets

# --- 1. THE ARCHITECT (Curriculum + Metaphor) ---
def generate_curriculum_blueprint(topic, profile, campaign_context, struggles, struggle_topics: Optional[List[Dict[str, Any]]] = None):
    # UPGRADE: Using Gemini 2.5 Pro for High-Level Instructional Design
    model = get_model(intent='complex') 
    
    prompt = f"""
    Act as a Lead Instructional Designer using **4C/ID Theory** (Four-Component Instructional Design).
    Create a Curriculum Blueprint for a course on: "{topic}".
    
    ### USER CONTEXT
    - Knowledge: {profile.get('marketing_knowledge', 'NOVICE')}
    - Style: {profile.get('learning_style', 'VISUAL')}
    - Data: {campaign_context}
    - **Identified Struggles**: {struggles if struggles else "None detected."} (Address these explicitly if present).
    - **Quiz Weak Points**: {struggle_topics if struggle_topics else "None provided."}

    ### PEDAGOGICAL STRATEGY (4C/ID & Gamification)
    1. **Learning Tasks**: Authentic, whole-task experiences.
    2. **Supportive Information**: Theory/Mental Models (Must use a strong Visual Metaphor).
    3. **Just-in-Time Information**: Procedural steps/Rules.
    4. **Part-Task Practice**: Quizzes and Drills.
    
    Select a **Visual Metaphor** to explain this concept (e.g., SEO = Gardening).

    ### OUTPUT JSON
    {{
        "title": "Course Title",
        "pedagogical_metaphor": "Gardening", 
        "sections": [
            {{ "title": "The Big Picture (Supportive)", "goal": "Explain the mental model...", "type": "supportive" }},
            {{ "title": "The Process (Procedural)", "goal": "Step-by-step execution...", "type": "procedural" }},
            {{ "title": "The Drill (Practice)", "goal": "Reinforce through gamified quiz...", "type": "practice" }}
        ]
    }}
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            data = extract_json_safe(response.text)
            
            # Validation: Ensure sections exist
            if not data.get("sections") or len(data["sections"]) == 0:
                logger.warning(f"⚠️ Blueprint Warning: No sections found in response: {data}")
                raise ValueError("AI generated a blueprint with no sections.")
                
            return data
        except Exception as e:
            logger.warning(f"⚠️ Blueprint Attempt {attempt+1} Failed: {e}")
            if attempt == max_retries - 1:
                logger.error(f"❌ Blueprint Failed after {max_retries} attempts.")
                raise e
            time.sleep(2)

# --- 2. THE PROFESSOR (Pass 1: Text Only) ---
def write_section_narrative(section_meta, topic, metaphor, profile, struggle_topics: Optional[List[Dict[str, Any]]] = None):
    """
    Writes the educational text using Constructivist principles.
    """
    model = get_model(intent='complex') # gemini-2.5-pro suggested
    
    prompt = f"""
    Act as an Expert Tutor applying **Constructivist Learning Theory**.
    Write the **Educational Text** for one section of "{topic}".
    
    - **Section:** {section_meta['title']}
    - **Type:** {section_meta.get('type', 'general')}
    - **Goal:** {section_meta['goal']}
    - **Metaphor:** {metaphor} (Weave this analogy throughout).
    - **Remediation Targets:** {struggle_topics if struggle_topics else "None"}
    
    **STRICT OUTPUT RULES:**
    1. **Start IMMEDIATELY** with the lesson content. 
    2. **Tone**: Scaffolded, interactive, questioning (Encourage reflection).
    3. **DO NOT** use H1 (#) headers. Use H2 (##) or H3 (###) only.
    4. Write approx 300 words of deep, high-value content.
    """
    response = model.generate_content(prompt)
    return response.text.strip().strip('"')

# --- 3. THE DESIGNER (Pass 2: Assets & Quiz) ---
def design_section_assets(section_text, section_meta, metaphor, struggle_topics: Optional[List[Dict[str, Any]]] = None):
    """
    Generates supporting assets.
    STRICT ENFORCEMENT of Mixed-Media (VEO/TTS).
    """
    model = get_model(intent='complex')
    
    # Determine required assets based on 4C/ID Phase
    requirements = ""
    section_type = section_meta.get('type', 'general')
    
    if section_type == 'supportive' or section_type == 'activation':
        # MUST have a VEO demonstration for mental models
        requirements = "1. `video_clip` (VEO: Cinematic visualization of the Metaphor). 2. `quiz_single` (Reflection)."
    elif section_type == 'procedural' or section_type == 'demonstration':
        # Procedural needs TTS guidance and Diagrams
        requirements = "1. `audio_note` (TTS: Step-by-step summary). 2. `image_diagram` (Flowchart). 3. `callout_pro_tip`."
    else: # Practice/Application
        requirements = "1. `callout_pro_tip`. 2. `quiz_final` (Gamified Assessment)."

    prompt = f"""
    Act as an Instructional Designer.
    Analyze the Lesson Text and generate JSON assets.

    ### LESSON TEXT
    "{section_text[:1500]}..." 

    ### REQUIRED ASSETS (Strict JSON):
    {requirements}

    **RULES:**
    1. **VEO Video:** Prompt must be "Cinematic, abstract, photorealistic shot of {metaphor}...". NO TEXT/CHARACTERS.
    2. **TTS Audio:** Script must be a concise, engaging summary of the key concept.
    3. **Quiz Standardization (CRITICAL):**
       - `correct_answer` must be an INTEGER index (0-3).
       - Integrate remediation for these quiz weaknesses: {struggle_topics if struggle_topics else "None"}.
       
       *Schema:*
       - `quiz_single`: {{ "question": "...", "options": ["A","B","C","D"], "correct_answer": 0 }}
       - `quiz_final`: {{ "questions": [ {{ "question": "...", "options": ["A","B"], "correct_answer": 2 }}, ... ] }}

    ### OUTPUT JSON FORMAT
    {{
        "assets": [
            {{ "type": "video_clip", "visual_prompt": "..." }},
            {{ "type": "audio_note", "script": "..." }}
        ]
    }}
    """
    try:
        response = model.generate_content(prompt)
        data = extract_json_safe(response.text)
        data['assets'] = validate_quiz_data(data.get('assets', []))
        return data
    except Exception as e:
        logger.warning(f"⚠️ Asset Generation Parsing Failed: {e}. Returning empty assets.")
        return {"assets": []}

from app.services.video_agent import VideoAgent
from app.services.image_agent import ImageAgent

# ... (imports remain)

# --- MAIN CONTROLLER ---
def generate_tutorial(user_id: str, topic: str, is_delta: bool = False, context: str = None, progress_callback=None):
    # Initialize all Creative Agents
    creative = CreativeService() # Still used for Audio (TTS)
    video_agent = VideoAgent()
    image_agent = ImageAgent()
    
    # Fetch Context (Profile + Campaigns)
    # ... (existing context fetching logic) ...
    user_doc = db.collection('users').document(user_id).get()
    profile = user_doc.to_dict().get("profile", {})
    campaigns_ref = db.collection('users').document(user_id).collection('campaign_performance').limit(3).stream()
    campaign_context = json.dumps([c.to_dict() for c in campaigns_ref], default=str)

    # 1. NEW: Fetch Past Quiz Results (Private Collection) to find "Struggles"
    struggles = []
    struggle_topics: List[Dict[str, Any]] = []
    try:
        past_tutorials = db.collection('users').document(user_id).collection('tutorials').where('is_completed', '==', True).limit(5).stream()
        for t_doc in past_tutorials:
            t_data = t_doc.to_dict()
            # Analyze quiz_results if available
            results = t_data.get('quiz_results', [])
            if results:
                # Assuming simple logic: Any quiz < 50% is a struggle
                for q_res in results:
                    score = q_res.get('score', 100)
                    if score < 60:
                        struggles.append(f"Weak in: {t_data.get('title', 'Unknown')} (Score: {score}%)")
                        struggle_topics.append({
                            "topic": t_data.get('title', 'Unknown'),
                            "section_title": q_res.get('section_title') or q_res.get('question', 'Unknown Section'),
                            "score": score,
                            "detail": q_res
                        })

            # Fallback: Check global completion score
            elif t_data.get('completion_score', 100) < 70:
                struggles.append(f"Struggled with: {t_data.get('title')}")
                struggle_topics.append({
                    "topic": t_data.get('title', 'Unknown'),
                    "section_title": "Overall Course",
                    "score": t_data.get('completion_score', 0),
                    "detail": {"note": "Low completion score"}
                })

        # Deep dive on the current topic if it exists in the private collection
        targeted_stream = db.collection('users').document(user_id).collection('tutorials').where('title', '==', topic).limit(1).stream()
        for t_doc in targeted_stream:
            targeted_data = t_doc.to_dict()
            for q_res in targeted_data.get('quiz_results', []):
                score = q_res.get('score', 100)
                if score < 80:
                    struggles.append(f"Needs remediation in '{q_res.get('section_title', 'section')}' for {topic} (Score: {score}%)")
                    struggle_topics.append({
                        "topic": topic,
                        "section_title": q_res.get('section_title', 'Unknown Section'),
                        "score": score,
                        "detail": q_res
                    })

    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch study history: {e}")

    logger.info(f"🎓 Agent: Blueprinting '{topic}' (Struggles: {len(struggles)})...")

    # PHASE 1: BLUEPRINT
    blueprint = generate_curriculum_blueprint(topic, profile, campaign_context, struggles, struggle_topics)
    metaphor = blueprint.get('pedagogical_metaphor', 'Abstract Concept')
    
    final_sections = []

    # PHASE 2: SECTION LOOP
    for index, sec_meta in enumerate(blueprint.get('sections', [])):
        logger.info(f"   Writing Section {index+1}: {sec_meta['title']} ({metaphor})...")
        
        if progress_callback:
            progress_callback(f"Crafting Section {index+1}: {sec_meta['title']}...")
        
        section_success = False
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # PASS 1: Narrative (Text)
                narrative_text = write_section_narrative(sec_meta, topic, metaphor, profile, struggle_topics)
                
                if not narrative_text or len(narrative_text) < 50:
                    raise ValueError("Narrative text too short or empty")

                # PASS 2: Assets (JSON)
                assets_data = design_section_assets(narrative_text, sec_meta, metaphor, struggle_topics)
                
                # MERGE
                combined_blocks = []
                assets = assets_data.get('assets', [])
                
                # Processing Order & STRICT FABRICATION
                # Order: Visuals -> Text -> Audio/Tips -> Quiz
                visuals = [b for b in assets if b['type'] in ['video_clip', 'image_diagram']]
                audios = [b for b in assets if b['type'] in ['audio_note', 'callout_pro_tip']]
                quizzes = [b for b in assets if b['type'] in ['quiz_single', 'quiz_final']]
                
                for block in visuals:
                    processed = fabricate_block(block, topic, creative, video_agent, image_agent)
                    if processed: combined_blocks.append(processed)

                combined_blocks.append({ "type": "text", "content": narrative_text })

                for block in audios:
                    processed = fabricate_block(block, topic, creative, video_agent, image_agent)
                    if processed: combined_blocks.append(processed)

                for block in quizzes:
                    combined_blocks.append(block)

                final_sections.append({
                    "title": sec_meta['title'],
                    "blocks": combined_blocks
                })
                section_success = True
                break # Success, exit retry loop

            except Exception as e:
                logger.warning(f"⚠️ Section {index+1} Attempt {attempt+1} Failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    logger.error(f"❌ Section {index+1} Failed after {max_retries} attempts.")
                    # CRITICAL: Re-raise to abort entire tutorial if mixed-media fails
                    raise RuntimeError(f"Mixed-Media Generation Failed for Section {index+1}: {e}")
        
        if not section_success:
             raise RuntimeError(f"Failed to generate Section {index+1}: {sec_meta['title']}")

    # Final Validation
    if not final_sections:
        raise RuntimeError("Tutorial generation resulted in 0 sections. Aborting save.")

    # Save
    tutorial_data = {
        "title": blueprint.get("title", topic),
        "category": "Adaptive Course",
        "difficulty": profile.get("marketing_knowledge", "NOVICE"),
        "sections": final_sections,
        "owner_id": user_id,
        "is_public": True, 
        "tags": [profile.get("learning_style", "VISUAL"), metaphor],
        "timestamp": firestore.SERVER_TIMESTAMP,
        "is_completed": False
    }
    
    # Save to User's Private Collection
    doc_ref = db.collection("users").document(user_id).collection("tutorials").add(tutorial_data)
    tutorial_data["id"] = doc_ref[1].id
    
    # Save to Global Index
    try:
        global_ref = db.collection("tutorials").document(tutorial_data["id"])
        global_ref.set(tutorial_data)
        logger.info(f"   🌍 Published to Global Library: {tutorial_data['id']}")
    except Exception as e:
        logger.error(f"   ⚠️ Failed to publish globally: {e}")
        
    return tutorial_data

def fabricate_block(block, topic, creative, video_agent, image_agent):
    """ Helper to call Creative Agents safely. Raises Error on Critical Failure. """
    try:
        if block["type"] == "video_clip":
            p = block.get("visual_prompt", f"Cinematic {topic}")
            safe_p = f"Cinematic, abstract, photorealistic, 4k shot of {p}. High quality. No text, no screens."
            logger.info(f"      🎥 VEO Generating: {p}")
            
            # Use Video Agent
            url = video_agent.generate_video(safe_p)
            
            # STRICT CHECK: Must have a URL
            if not url or not url.startswith("http"):
                raise RuntimeError(f"VEO Generation returned invalid URL for prompt: {p}")
            
            logger.info(f"      ✅ Video Created: {url[:30]}...")
            return { "type": "video", "url": url, "prompt": p }
        
        elif block["type"] == "image_diagram":
            p = block.get("visual_prompt", f"Diagram of {topic}")
            
            # Use Image Agent
            url = image_agent.generate_image(p)
            
            if url and url.startswith("http"):
                logger.info(f"      ✅ Image Created")
                return { "type": "image", "url": url, "prompt": p }
            logger.warning("      ⚠️ Image generation failed, skipping block (Semi-critical).")
            return None # Skip block but don't crash
        
        elif block["type"] == "audio_note":
            s = block.get("script", "")
            if not s: s = f"Let's focus on {topic}."
            logger.info(f"      🎙️ TTS Generating...")
            
            # Use Legacy Creative Service for Audio
            url = creative.generate_audio(s)
            
            # STRICT CHECK: Must have a URL
            if not url or not url.startswith("http"):
                raise RuntimeError("TTS Generation returned invalid output.")
                
            logger.info(f"      ✅ Audio Created")
            return { "type": "audio", "url": url, "transcript": s }
        
        else:
            return block 
    except Exception as e:
        logger.error(f"      ⚠️ Asset Error: {e}")
        # Re-raise to trigger the section retry loop
        raise e
