import os
import json
import datetime
import time
from google.cloud import firestore
from app.services.ai_studio import CreativeService

# --- 1. THE ARCHITECT (Curriculum + Metaphor) ---
def generate_curriculum_blueprint(topic, profile, campaign_context):
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    prompt = f"""
    Act as a Lead Instructional Designer.
    Create a Curriculum Blueprint for a course on: "{topic}".
    
    ### USER CONTEXT
    - Knowledge: {profile.get('marketing_knowledge', 'NOVICE')}
    - Style: {profile.get('learning_style', 'VISUAL')}
    - Data: {campaign_context}

    ### PEDAGOGICAL STRATEGY
    Select a **Visual Metaphor** to explain this concept.
    *Example: SEO = Gardening.*
    *Example: Paid Ads = Auction House.*

    ### OUTPUT JSON
    {{
        "title": "Course Title",
        "pedagogical_metaphor": "Gardening", 
        "sections": [
            {{ "title": "The Concept", "goal": "Explain the foundation...", "type": "activation" }},
            {{ "title": "The Strategy", "goal": "Explain the process...", "type": "demonstration" }},
            {{ "title": "The Execution", "goal": "Explain the optimization...", "type": "application" }}
        ]
    }}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        print(f"❌ Blueprint Failed: {e}")
        raise e

# --- 2. THE PROFESSOR (Pass 1: Text Only) ---
def write_section_narrative(section_meta, topic, metaphor, profile):
    """
    Writes the educational text. 
    FIX: Now strictly bans conversational filler ("Of course...").
    """
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    prompt = f"""
    Act as an Expert Tutor. Write the **Educational Text** for one section of "{topic}".
    
    - **Section:** {section_meta['title']}
    - **Goal:** {section_meta['goal']}
    - **Metaphor:** {metaphor} (Weave this analogy throughout).
    - **Tone:** Professional, encouraging, data-driven.
    
    **STRICT OUTPUT RULES:**
    1. **Start IMMEDIATELY** with the lesson content. 
    2. **DO NOT** write "Here is the text" or "Sure, I can help".
    3. **DO NOT** use H1 (#) headers. Use H2 (##) or H3 (###) only.
    4. Write approx 300 words of deep, high-value content.
    """
    response = model.generate_content(prompt)
    # Double check to strip any lingering quotes or whitespace
    return response.text.strip().strip('"')

# --- 3. THE DESIGNER (Pass 2: Assets & Quiz) ---
def design_section_assets(section_text, section_meta, metaphor):
    """
    Generates supporting assets.
    FIX: Enforces 'correct_answer' (Integer) for ALL quizzes to prevent scoring errors.
    """
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    # Determine required assets based on section type
    requirements = ""
    if section_meta['type'] == 'activation':
        requirements = "1. `video_clip` (Metaphor visualization). 2. `quiz_single` (Scenario based)."
    elif section_meta['type'] == 'demonstration':
        requirements = "1. `audio_note` (Mentor script). 2. `image_diagram` (Flowchart). 3. `callout_pro_tip` (High value advice)."
    elif section_meta['type'] == 'application':
        requirements = "1. `callout_pro_tip`. 2. `quiz_final` (5 Questions)."

    prompt = f"""
    Act as an Instructional Designer.
    Analyze the Lesson Text and generate JSON assets.

    ### LESSON TEXT
    "{section_text[:1500]}..." 

    ### REQUIRED ASSETS (Strict JSON):
    {requirements}

    **RULES:**
    1. **Video:** Prompt must be "Cinematic, abstract shot of {metaphor}...". NO TEXT.
    2. **Pro Tip:** GENERATE a new high-value tip relevant to the topic. Do NOT return an empty string.
    3. **Quiz Standardization (CRITICAL):** - ALL correct answers must be **INTEGER INDICES** (0, 1, 2, or 3). Do NOT use text strings.
       - Use the key `correct_answer` for everything.
       
       *Schema:*
       - `quiz_single`: {{ "question": "...", "options": ["A","B","C","D"], "correct_answer": 0 }}
       - `quiz_final`: {{ "questions": [ {{ "question": "...", "options": ["A","B"], "correct_answer": 2 }}, ... ] }}

    ### OUTPUT JSON FORMAT
    {{
        "assets": [
            {{ "type": "video_clip", "visual_prompt": "..." }},
            {{ "type": "callout_pro_tip", "content": "Always check your..." }}
        ]
    }}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except:
        return {"assets": []}
# --- MAIN CONTROLLER ---
def generate_tutorial(user_id: str, topic: str, is_delta: bool = False, context: str = None, progress_callback=None):
    db = firestore.Client()
    creative = CreativeService()
    
    # Fetch Context
    user_doc = db.collection('users').document(user_id).get()
    profile = user_doc.to_dict().get("profile", {})
    campaigns_ref = db.collection('users').document(user_id).collection('campaign_performance').limit(3).stream()
    campaign_context = json.dumps([c.to_dict() for c in campaigns_ref], default=str)

    print(f"🎓 Agent: Blueprinting '{topic}'...")

    # PHASE 1: BLUEPRINT
    blueprint = generate_curriculum_blueprint(topic, profile, campaign_context)
    metaphor = blueprint.get('pedagogical_metaphor', 'Abstract Concept')
    
    final_sections = []

    # PHASE 2: SECTION LOOP
    for index, sec_meta in enumerate(blueprint.get('sections', [])):
        print(f"   Writing Section {index+1}: {sec_meta['title']} ({metaphor})...")
        
        if progress_callback:
            progress_callback(f"Crafting Section {index+1}: {sec_meta['title']}...")
         
         try:
             # PASS 1: Narrative (Text)
            narrative_text = write_section_narrative(sec_meta, topic, metaphor, profile)
            
            # PASS 2: Assets (JSON)
            assets_data = design_section_assets(narrative_text, sec_meta, metaphor)
            
            # MERGE
            combined_blocks = []
            assets = assets_data.get('assets', [])
            
            # Order: Visuals -> Text -> Audio/Tips -> Quiz
            visuals = [b for b in assets if b['type'] in ['video_clip', 'image_diagram']]
            audios = [b for b in assets if b['type'] in ['audio_note', 'callout_pro_tip']]
            quizzes = [b for b in assets if b['type'] in ['quiz_single', 'quiz_final']]
            
            for block in visuals:
                processed = fabricate_block(block, topic, creative)
                if processed: combined_blocks.append(processed)

            combined_blocks.append({ "type": "text", "content": narrative_text })

            for block in audios:
                processed = fabricate_block(block, topic, creative)
                if processed: combined_blocks.append(processed)

            for block in quizzes:
                combined_blocks.append(block)

            final_sections.append({
                "title": sec_meta['title'],
                "blocks": combined_blocks
            })

        except Exception as e:
            print(f"❌ Section Failed: {e}")
            raise RuntimeError(f"Failed to generate Section {index+1}")

    # Save
    tutorial_data = {
        "title": blueprint.get("title", topic),
        "category": "Adaptive Course",
        "difficulty": profile.get("marketing_knowledge", "NOVICE"),
        "sections": final_sections,
        "owner_id": user_id,
        "is_public": False,
        "tags": [profile.get("learning_style", "VISUAL"), metaphor],
        "timestamp": firestore.SERVER_TIMESTAMP,
        "is_completed": False
    }
    
    # SENIOR DEV FIX: Save to user's subcollection so the frontend listener picks it up immediately
    doc_ref = db.collection("users").document(user_id).collection("tutorials").add(tutorial_data)
    tutorial_data["id"] = doc_ref[1].id
    return tutorial_data

def fabricate_block(block, topic, creative):
    """ Helper to call Creative Service safely """
    try:
        if block["type"] == "video_clip":
            p = block.get("visual_prompt", f"Cinematic {topic}")
            safe_p = f"Cinematic, abstract, photorealistic, 4k shot of {p}. High quality. No text, no screens."
            print(f"      🎥 Video: {p}")
            url = creative.generate_video(safe_p, style="cinematic")
            if url and url.startswith("http"):
                return { "type": "video", "url": url, "prompt": p }
        
        elif block["type"] == "image_diagram":
            p = block.get("visual_prompt", f"Diagram of {topic}")
            url = creative.generate_image(p)
            if url and url.startswith("http"):
                return { "type": "image", "url": url, "prompt": p }
        
        elif block["type"] == "audio_note":
            s = block.get("script", "")
            # Safety fill if script is empty
            if not s: s = f"Let's focus on the key strategy for {topic}."
            url = creative.generate_audio(s)
            if url and url.startswith("http"):
                return { "type": "audio", "url": url, "transcript": s }
        
        else:
            return block 
    except Exception as e:
        print(f"      ⚠️ Asset Error: {e}")
        return None