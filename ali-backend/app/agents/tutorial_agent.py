import os
import json
import datetime
import time
import logging
import re
import uuid
import hashlib
from typing import Dict, List, Any, Optional
from app.services.ai_studio import CreativeService
from app.services.llm_factory import get_model
from app.core.security import db
from firebase_admin import firestore
from app.services.metricool_client import MetricoolClient
from concurrent.futures import ThreadPoolExecutor
from app.types.tutorial_lifecycle import TutorialStatus
from app.services import research_service

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


def _build_evidence_bundle(topic: str) -> Dict[str, Any]:
    if os.getenv("ENABLE_TUTORIAL_RESEARCH", "true").lower() != "true":
        return {"sources": [], "citations": [], "truthSourceJson": None, "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat()}

    scout_sources = research_service.scout_sources(topic, limit=8)
    urls = [source["url"] for source in scout_sources]
    deep_sources = research_service.deep_dive(urls)
    bundle = {
        "id": str(uuid.uuid4()),
        "topic": topic,
        "sources": deep_sources,
        "citations": [],
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    bundle["truthSourceJson"] = research_service.store_evidence_bundle(bundle)
    bundle["citations"] = [
        {"title": src.get("title"), "url": src.get("url"), "retrievedAt": src.get("retrievedAt")}
        for src in deep_sources
    ]
    return bundle


def _build_citations(evidence_bundle: Dict[str, Any], max_items: int = 2) -> List[Dict[str, Any]]:
    citations = evidence_bundle.get("citations", [])
    return citations[:max_items] if citations else []


def _build_game_block(section_meta: Dict[str, Any], topic: str) -> Dict[str, Any]:
    game_type = section_meta.get("game_type") or "sorter"
    base = {
        "type": "game",
        "game_type": game_type,
        "title": section_meta.get("title", "Practice"),
        "instructions": f"Apply the concepts from {topic} in this quick challenge."
    }
    if game_type == "fixer":
        base["config"] = {
            "prompt": "Fix the flawed strategy by choosing the best correction.",
            "options": ["Clarify target audience", "Align KPI with objective", "Refine CTA language"],
            "correctIndex": 1
        }
    elif game_type == "scenario":
        base["config"] = {
            "prompt": "Choose the best next step for the campaign.",
            "choices": [
                {"label": "Analyze results and iterate", "value": "iterate"},
                {"label": "Increase budget immediately", "value": "scale"},
                {"label": "Pause and gather feedback", "value": "pause"}
            ],
            "correctValue": "iterate"
        }
    else:
        base["config"] = {
            "leftLabel": "Best Practices",
            "rightLabel": "Anti-Patterns",
            "items": [
                {"label": "Segment audience by intent", "category": "left"},
                {"label": "Ignore negative feedback", "category": "right"},
                {"label": "Test creative variations", "category": "left"},
                {"label": "Set vague success metrics", "category": "right"}
            ]
        }
    return base

# --- NEW: THE INSPECTOR (QA) ---
def review_tutorial_quality(tutorial_data: Dict[str, Any], original_blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """
    Audits the final tutorial against the original blueprint.
    Ensures 4C/ID compliance and Constructivist alignment.
    """
    model = get_model(intent='complex')

    sections = tutorial_data.get('sections', [])

    def _collect_text_blocks():
        blocks = []
        for sec in sections:
            for block in sec.get('blocks', []):
                if block.get("type") == "text":
                    blocks.append({
                        "section_title": sec.get("title"),
                        "content": block.get("content", "") or ""
                    })
        return blocks

    def _word_count(text: str) -> int:
        return len([w for w in re.split(r"\s+", text.strip()) if w])

    def _contains_any(text: str, phrases: List[str]) -> bool:
        lowered = text.lower()
        return any(p in lowered for p in phrases)

    # Extract simplified structure for the LLM
    final_structure = []
    for sec in sections:
        blocks = [b.get('type') for b in sec.get('blocks', [])]
        final_structure.append(f"{sec.get('title', 'Untitled')}: {blocks}")

    # Pre-compute rubric checks for structure and citations
    text_blocks = _collect_text_blocks()
    card_word_counts = [_word_count(b["content"]) for b in text_blocks if b["content"]]
    oversized_cards = [count for count in card_word_counts if count > 220]
    undersized_cards = [count for count in card_word_counts if count < 120]

    combined_text = "\n".join([b["content"] for b in text_blocks])
    structure_checks = {
        "why_this_matters": _contains_any(combined_text, ["why this matters", "why it matters", "importance"]),
        "example": _contains_any(combined_text, ["example", "for instance", "case study"]),
        "watch_out_for": _contains_any(combined_text, ["watch out", "common mistake", "pitfall"]),
        "cheat_sheet": _contains_any(combined_text, ["cheat sheet", "quick recap", "summary"]),
    }
    missing_structure = [k for k, v in structure_checks.items() if not v]

    citation_blocks = 0
    for sec in sections:
        for block in sec.get('blocks', []):
            if block.get("type") == "text" and block.get("citations"):
                citation_blocks += 1
    citation_coverage = {
        "text_blocks": len(text_blocks),
        "blocks_with_citations": citation_blocks,
    }

    prompt = f"""
    Act as a Pedagogical Quality Assurance Auditor.
    Compare the Produced Tutorial against the Approved Blueprint.
    
    ### BLUEPRINT
    - Metaphor: {original_blueprint.get('pedagogical_metaphor')}
    - Planned Sections: {[s['title'] for s in original_blueprint.get('sections', [])]}
    
    ### PRODUCED CONTENT
    - Title: {tutorial_data.get('title')}
    - Structure: {final_structure}
    
    ### AUDIT CRITERIA (Score 0-100)
    1. **Metaphor Integrity**: Is the metaphor used consistently?
    2. **Asset Relevance**: Do sections have appropriate media (Video for Support, Quiz for Practice)?
    3. **Completeness**: Are all planned sections present?
    
    ### OUTPUT JSON
    {{
        "score": 85,
        "status": "PASSED" | "FLAGGED",
        "feedback": "Metaphor well integrated...",
        "flags": ["Missing video in section 2"]
    }}
    Threshold: < 70 = FLAGGED.
    """
    try:
        response = model.generate_content(prompt)
        report = extract_json_safe(response.text)
        report["rubric"] = {
            "card_word_counts": {
                "total_cards": len(card_word_counts),
                "oversized_cards": len(oversized_cards),
                "undersized_cards": len(undersized_cards),
            },
            "structure_requirements": {
                "missing": missing_structure,
                "checks": structure_checks,
            },
            "citation_coverage": citation_coverage,
        }
        if missing_structure:
            report.setdefault("flags", []).append(
                f"Missing structure elements: {', '.join(missing_structure)}"
            )
        if oversized_cards or undersized_cards:
            report.setdefault("flags", []).append(
                f"Card length out of range (min 120, max 220). Oversized: {len(oversized_cards)}, undersized: {len(undersized_cards)}"
            )
        return report
    except Exception as e:
        logger.warning(f"⚠️ QA Audit Failed: {e}")
        return {"score": 0, "status": "FLAGGED", "feedback": "Audit failed due to error.", "flags": [str(e)]}

# --- 1. THE ARCHITECT (Curriculum + Metaphor) ---
def generate_curriculum_blueprint(topic, profile, campaign_context, struggles, struggle_topics: Optional[List[Dict[str, Any]]] = None, connected_channels: List[str] = None):
    # UPGRADE: Using Gemini 2.5 Pro for High-Level Instructional Design
    model = get_model(intent='complex') 
    
    prompt = f"""
    Act as a Lead Instructional Designer using **4C/ID Theory** (Four-Component Instructional Design).
    Create a Curriculum Blueprint for a course on: "{topic}".
    
    ### USER CONTEXT
    - Knowledge: {profile.get('marketing_knowledge', 'NOVICE')}
    - Style: {profile.get('learning_style', 'VISUAL')}
    - **Active Channels**: {connected_channels if connected_channels else "None specific"}
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
        # MUST have a Visual demonstration for mental models
        requirements = "1. `image_diagram` (Visualization of the Metaphor). 2. `quiz_single` (Reflection)."
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
    1. **Visuals:** Prompt must be "Cinematic, abstract, photorealistic shot of {metaphor}...". NO TEXT/CHARACTERS.
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
            {{ "type": "image_diagram", "visual_prompt": "..." }},
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


from app.services.image_agent import ImageAgent
from app.services.audio_agent import AudioAgent

# ... (imports remain)

    # --- MAIN CONTROLLER ---
def generate_tutorial(user_id: str, topic: str, is_delta: bool = False, context: str = None, progress_callback=None):
    try:
        # Initialize all Creative Agents
        # creative = CreativeService() # DEPRECATED
        # video_agent = VideoAgent() # DEPRECATED

        image_agent = ImageAgent()
        audio_agent = AudioAgent()
        
        # Fetch Context (Profile + Campaigns)
        # ... (existing context fetching logic) ...
        user_doc = db.collection('users').document(user_id).get()
        profile = user_doc.to_dict().get("profile", {})
        campaigns_ref = db.collection('users').document(user_id).collection('campaign_performance').limit(3).stream()
        campaign_context = json.dumps([c.to_dict() for c in campaigns_ref], default=str)

        # 0. NEW: Fetch Connected Channels (Metricool)
        connected_channels = []
        try:
            mc = MetricoolClient()
            # Mocking blog_id logic or assuming fetching first available for context
            # In a real scenario we might need the user's specific blog_id
            # For now, we use get_account_info which is safe
            # Note: MetricoolClient needs env vars, assuming they are set
            acct_info = mc.get_account_info()
            connected_channels = acct_info.get('connected', [])
            logger.info(f"   📱 User Channels: {connected_channels}")
        except Exception as e:
            logger.warning(f"   ⚠️ Metricool Context Failed: {e}")

        if progress_callback:
            progress_callback("Step 0/5: Gathering research sources...")
        evidence_bundle = _build_evidence_bundle(topic)

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
        if progress_callback:
            progress_callback(f"Step 1/5: Creating curriculum blueprint for '{topic}'...")

        # PHASE 1: BLUEPRINT
        blueprint = generate_curriculum_blueprint(topic, profile, campaign_context, struggles, struggle_topics, connected_channels)
        metaphor = blueprint.get('pedagogical_metaphor', 'Abstract Concept')
        
        if progress_callback:
            progress_callback(f"Step 2/5: Blueprint complete! Found {len(blueprint.get('sections', []))} sections to generate...")
        
        final_sections = []

        # PHASE 2: PARALLEL SECTION GENERATION
        final_sections = [None] * len(blueprint.get('sections', [])) # Pre-allocate to maintain order
        
        def process_section(index, sec_meta):
            """Helper to process a single section fully."""
            try:
                logger.info(f"   🚀 Starting Section {index+1}: {sec_meta['title']}...")
                if progress_callback:
                    progress_callback(f"Generating Section {index+1}/{len(blueprint['sections'])}...")

                section_result = None
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
                        visuals = [b for b in assets if b['type'] in ['video_clip', 'image_diagram']]
                        audios = [b for b in assets if b['type'] in ['audio_note', 'callout_pro_tip']]
                        quizzes = [b for b in assets if b['type'] in ['quiz_single', 'quiz_final']]
                        
                        # PARALLEL GENERATION INSIDE SECTION (Nested ThreadPool)
                        # Note: Nesting ThreadPools is generally safe in Python but we should be mindful of worker limits.
                        # Since the outer loop will use threads, this inner part assumes sufficient workers or runs sequentially if saturated.
                        
                        processed_visuals = []
                        processed_audios = []

                        # We use a context manager for the inner execution to ensure clean-up
                        max_asset_workers = int(os.getenv("TUTORIAL_ASSET_WORKERS", 3))
                        with ThreadPoolExecutor(max_workers=max_asset_workers) as inner_executor:
                             fab_task = lambda b: fabricate_block(b, topic, None, image_agent, audio_agent)
                             processed_visuals = list(inner_executor.map(fab_task, visuals))
                             processed_audios = list(inner_executor.map(fab_task, audios))

                        # Assemble Block
                        for pv in processed_visuals:
                            if pv: combined_blocks.append(pv)

                        combined_blocks.append({
                            "type": "text",
                            "content": narrative_text,
                            "citations": _build_citations(evidence_bundle)
                        })

                        for pa in processed_audios:
                            if pa: combined_blocks.append(pa)

                        if sec_meta.get("type") == "practice":
                            combined_blocks.append(_build_game_block(sec_meta, topic))

                        for block in quizzes:
                            combined_blocks.append(block)

                        section_result = {
                            "title": sec_meta['title'],
                            "type": sec_meta.get("type", "general"),
                            "blocks": combined_blocks
                        }
                        break # Success

                    except Exception as e:
                        logger.warning(f"⚠️ Section {index+1} Attempt {attempt+1} Failed: {e}")
                        if attempt == max_retries - 1:
                            raise RuntimeError(f"Mixed-Media Generation Failed for Section {index+1}: {e}")
                        time.sleep(2)
                
                return index, section_result
                
            except Exception as e:
                logger.error(f"❌ Critical Failure in Section {index+1}: {e}")
                raise e

        # EXECUTE PARALLEL SECTIONS
        logger.info(f"   ⚡ Launching {len(blueprint['sections'])} sections in parallel...")
        if progress_callback:
            progress_callback(f"Generating {len(blueprint['sections'])} sections simultaneously...")

        max_sec_workers = int(os.getenv("TUTORIAL_SECTION_WORKERS", 5))
        with ThreadPoolExecutor(max_workers=max_sec_workers) as executor:
            futures = []
            for i, sec in enumerate(blueprint.get('sections', [])):
                futures.append(executor.submit(process_section, i, sec))
                
            for future in futures:
                idx, result = future.result() # This re-raises exceptions from threads
                final_sections[idx] = result # Store in correct order

        # Final Validation
        if not all(final_sections):
             raise RuntimeError("One or more sections failed to generate.")

        # STRICT MEDIA VALIDATION: Prevent tutorial save if any media failed
        # User requirement: "No tutorial should be created without the necessary media"
        failed_media_blocks = []
        for sec_idx, sec in enumerate(final_sections):
            if not sec:
                continue
            for block_idx, block in enumerate(sec.get('blocks', [])):
                if block.get('status') == 'failed':
                    failed_media_blocks.append({
                        "section_index": sec_idx,
                        "section_title": sec.get('title', f'Section {sec_idx + 1}'),
                        "block_index": block_idx,
                        "original_type": block.get('original_type', block.get('type', 'unknown')),
                        "prompt": block.get('prompt') or block.get('script', 'N/A'),
                        "error": block.get('error') or block.get('info', 'Unknown failure')
                    })
        
        if failed_media_blocks:
            failure_details = "; ".join([
                f"{fb['section_title']}:{fb['original_type']}" 
                for fb in failed_media_blocks
            ])
            logger.error(f"❌ STRICT VALIDATION: {len(failed_media_blocks)} media block(s) failed: {failure_details}")
            
            # Create admin alert for failed generation attempt
            try:
                db.collection('admin_tasks').add({
                    "type": "generation_blocked",
                    "severity": "high",
                    "status": "pending",
                    "user_id": user_id,
                    "tutorial_topic": topic,
                    "failed_blocks": failed_media_blocks,
                    "reason": "Strict media validation prevented tutorial creation",
                    "created_at": firestore.SERVER_TIMESTAMP
                })
            except Exception as admin_e:
                logger.warning(f"Failed to create admin alert: {admin_e}")
            
            raise RuntimeError(
                f"Tutorial generation blocked: {len(failed_media_blocks)} required media asset(s) failed to generate. "
                f"Failed: {failure_details}. No tutorial saved."
            )

        # PHASE 3: FINAL AUDIO SUMMARY
        try:
            logger.info("   🎙️ Generating Course Summary Audio...")
            if progress_callback: progress_callback("Finalizing: Generating Audio Summary...")
            
            summary_script = f"Congratulations on completing this course on {topic}. To recap: We explored {metaphor} to understand the core concepts. Remember to apply these strategies on your channels like {', '.join(connected_channels) if connected_channels else 'social media'}. Keep experimenting!"
            
            summary_url = audio_agent.generate_audio(summary_script, folder="tutorials")
            if summary_url:
                final_sections.append({
                    "title": "Course Summary",
                    "blocks": [{ "type": "audio", "url": summary_url, "transcript": summary_script }]
                })
        except Exception as e:
            logger.warning(f"⚠️ Summary Audio Failed: {e}")

        # PHASE 4: QA AUDIT
        if progress_callback:
            progress_callback(f"Step 4/5: Running quality assurance audit...")
        audit_report = review_tutorial_quality({ "title": blueprint.get("title", topic), "sections": final_sections }, blueprint)
        logger.info(f"   🧐 QA Score: {audit_report.get('score')}/100 - {audit_report.get('status')}")

        # Save
        version_id = str(uuid.uuid4())
        content_hash = hashlib.sha256(json.dumps(final_sections, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        tutorial_data = {
            "title": blueprint.get("title", topic),
            "category": "Adaptive Course",
            "difficulty": profile.get("marketing_knowledge", "NOVICE"),
            "sections": final_sections,
            "owner_id": user_id,
            "status": TutorialStatus.DRAFT.value,
            "is_public": False,
            "tags": [profile.get("learning_style", "VISUAL"), metaphor],
            "timestamp": firestore.SERVER_TIMESTAMP,
            "is_completed": False,
            "audit_report": audit_report,
            "evidence_bundle": evidence_bundle,
            "versions": [{
                "versionId": version_id,
                "hash": content_hash,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "modelVersion": os.getenv("MODEL_VERSION", "unknown"),
                "publishedBy": None
            }],
            "currentVersion": version_id,
            "generation_alerts": [] # Populated by blocks if needed
        }
        
        # Collect Alerts from blocks
        alerts = []
        for i, sec in enumerate(final_sections):
            if not sec: continue
            for block in sec.get('blocks', []):
                if block.get('status') == 'failed':
                    alerts.append({
                        "section_index": i,
                        "section_title": sec['title'],
                        "type": block.get('original_type'),
                        "prompt": block.get('prompt'),
                        "timestamp": datetime.datetime.now().isoformat()
                    })
        tutorial_data['generation_alerts'] = alerts

        # Create Admin Task if Alerts Exist
        if alerts:
            try:
                db.collection('admin_tasks').add({
                    "type": "content_alert",
                    "status": "pending",
                    "user_id": user_id,
                    "tutorial_title": tutorial_data['title'],
                    "alerts": alerts,
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                logger.warning(f"   ⚠️ Created Admin Task for {len(alerts)} generation failures.")
            except Exception as e:
                logger.error(f"Failed to create admin task: {e}")
        
        # Step 5: Save to database
        if progress_callback:
            progress_callback(f"Step 5/5: Saving your tutorial to the database...")
        
        # Save to User's Private Collection
        doc_ref = db.collection("users").document(user_id).collection("tutorials").add(tutorial_data)
        tutorial_data["id"] = doc_ref[1].id
        
        # Save to Global Index
        try:
            global_ref = db.collection("tutorials").document(tutorial_data["id"])
            global_ref.set(tutorial_data)
            logger.info(f"   🧾 Draft saved to Global Library: {tutorial_data['id']}")

            try:
                global_ref.collection("versions").document(version_id).set({
                    "versionId": version_id,
                    "hash": content_hash,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "modelVersion": os.getenv("MODEL_VERSION", "unknown"),
                    "status": TutorialStatus.DRAFT.value,
                    "data": tutorial_data
                })
            except Exception as version_err:
                logger.warning(f"Failed to store tutorial version snapshot: {version_err}")
            
            # NOTIFICATION: SUCCESS
            try:
                db.collection('users').document(user_id).collection('notifications').add({
                    "title": "Tutorial Draft Ready",
                    "message": f"'{topic}' has been generated and is awaiting review.",
                    "type": "info",
                    "link": f"/tutorials/{tutorial_data['id']}",
                    "is_read": False,
                    "created_at": firestore.SERVER_TIMESTAMP
                })
            except Exception as ne:
                logger.warning(f"Failed to send success notification: {ne}")

        except Exception as e:
            logger.error(f"   ⚠️ Failed to publish globally: {e}")
            
        return tutorial_data

    except Exception as e:
        logger.error(f"❌ Critical Tutorial System Failure: {e}")
        
        # NOTIFICATION: FAILURE
        try:
            db.collection('users').document(user_id).collection('notifications').add({
                "title": "Generation Failed",
                "message": f"We couldn't generate '{topic}'. Our engineers have been alerted.",
                "type": "error",
                "is_read": False,
                "created_at": firestore.SERVER_TIMESTAMP
            })
        except:
            pass

        # Create CRITICAL ALERT (admin_tasks for workflow)
        try:
            db.collection('admin_tasks').add({
                "type": "system_failure",
                "severity": "critical",
                "status": "pending",
                "user_id": user_id,
                "context": {"topic": topic},
                "error": str(e),
                "created_at": firestore.SERVER_TIMESTAMP
            })
        except:
            pass # Last resort
        
        # ALSO write to admin_alerts for Troubleshooting Agent Watchdog visibility
        try:
            db.collection('admin_alerts').add({
                "type": "tutorial_generation_failure",
                "message": f"Tutorial '{topic}' generation failed: {str(e)[:200]}",
                "context": "tutorial_agent",
                "user_id": user_id,
                "severity": "critical",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
        except:
            pass
        raise e

def fabricate_block(block, topic, video_agent, image_agent, audio_agent, progress_callback=None):
    """ Helper to call Creative Agents safely. Handles Fallbacks and Alerts. """
    try:
        if block["type"] == "video_clip":
            p = block.get("visual_prompt", f"Cinematic {topic}")
            safe_p = f"Cinematic, abstract, photorealistic, 4k shot of {p}. High quality. No text, no screens."
            # Legacy support: Redirect video requests to Image Agent
            logger.info(f"      🎥 VEO Request Redirected to Image Agent: {p}")
            
            # Use Image Agent instead
            result = image_agent.generate_image(f"Cinematic photorealistic image of {p}", folder="tutorials")
            
            url = result
            gcs_key = None
            if isinstance(result, dict):
                url = result.get("url")
                gcs_key = result.get("gcs_object_key")
            
            if url:
                 logger.info("      ✅ Fallback Image Created for Video Request")
                 return { "type": "image", "url": url, "prompt": p, "fallback": True, "gcs_object_key": gcs_key }
            
            return {
                     "type": "placeholder",
                     "original_type": "video",
                     "prompt": p,
                     "status": "failed",
                     "info": "Video generation disabled. Image fallback failed."
                 }

            # Original Video Logic Removed
            """
            # Use Video Agent
            result = video_agent.generate_video(safe_p, folder="tutorials", progress_callback=progress_callback)
            
            url = result
            gcs_key = None
            if isinstance(result, dict):
                url = result.get("url")
                gcs_key = result.get("gcs_object_key")
            """
            
            # Fallback 1: Try Image if Video fails
            if not url or not str(url).startswith("http"):
                logger.warning(f"      ⚠️ VEO Failed. Falling back to Image Agent for: {p}")
                result = image_agent.generate_image(f"Cinematic photorealistic image of {p}", folder="tutorials")
                
                url = result
                gcs_key = None
                if isinstance(result, dict):
                    url = result.get("url")
                    gcs_key = result.get("gcs_object_key")
                
                if url:
                    logger.info("      ✅ Fallback Image Created")
                    return { "type": "image", "url": url, "prompt": p, "fallback": True, "gcs_object_key": gcs_key }
            
            # Fallback 2: Alert (Soft Failure)
            if not url or not str(url).startswith("http"):
                 logger.error(f"      ❌ All Visual Generation Failed on: {p}")
                 return { 
                     "type": "placeholder", 
                     "original_type": "video",
                     "prompt": p, 
                     "status": "failed",
                     "info": "Generation failed. Admin regeneration required." 
                 }
            
            logger.info(f"      ✅ Video Created: {url[:30]}...")
            return { "type": "video", "url": url, "prompt": p, "gcs_object_key": gcs_key }
        
        elif block["type"] == "image_diagram":
            p = block.get("visual_prompt", f"Diagram of {topic}")
            
            # Use Image Agent
            result = image_agent.generate_image(p, folder="tutorials")
            
            url = result
            gcs_key = None
            if isinstance(result, dict):
                url = result.get("url")
                gcs_key = result.get("gcs_object_key")
            
            if url and str(url).startswith("http"):
                logger.info(f"      ✅ Image Created")
                return { "type": "image", "url": url, "prompt": p, "gcs_object_key": gcs_key }
            
            logger.warning("      ⚠️ Image generation failed, recording alert.")
            return {
                "type": "placeholder",
                "original_type": "image",
                "prompt": p,
                "status": "failed",
                "info": "Image generation failed."
            }
        
        elif block["type"] == "audio_note":
            s = block.get("script", "")
            if not s: s = f"Let's focus on {topic}."
            logger.info(f"      🎙️ TTS Generating...")
            
            # Use Audio Agent (Persistent)
            result = audio_agent.generate_audio(s, folder="tutorials")
            
            url = result
            gcs_key = None
            if isinstance(result, dict):
                url = result.get("url")
                gcs_key = result.get("gcs_object_key")
            
            # Alert on Audio Fail
            if not url or not str(url).startswith("http"):
                logger.error("      ❌ TTS Failed.")
                return {
                    "type": "placeholder",
                    "original_type": "audio",
                    "script": s,
                    "status": "failed",
                    "info": "Audio generation failed."
                }
                
            logger.info(f"      ✅ Audio Created")
            return { "type": "audio", "url": url, "transcript": s, "gcs_object_key": gcs_key }
        
        else:
            return block 
    except Exception as e:
        logger.error(f"      ⚠️ Asset Error: {e}")
        # Soft Fail for unexpected exceptions too
        return {
            "type": "placeholder",
            "original_type": block.get("type", "unknown"),
             "status": "failed",
             "error": str(e)
        }
