import sys
import os
import json
import logging
from unittest.mock import MagicMock, patch

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Firebase
mock_db = MagicMock()
mock_collection = MagicMock()
mock_doc = MagicMock()
mock_db.collection.return_value = mock_collection
mock_collection.document.return_value = mock_doc
mock_doc.get.return_value.to_dict.return_value = {
    "profile": {"marketing_knowledge": "NOVICE", "learning_style": "VISUAL"}
}
# Mock stream for campaigns
mock_stream = MagicMock()
mock_stream.stream.return_value = []
mock_collection.document.return_value.collection.return_value.limit.return_value = mock_stream

# Mock modules BEFORE importing app code
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.firestore'] = MagicMock()
sys.modules['firebase_admin.firestore'].client.return_value = mock_db
sys.modules['firebase_admin.firestore'].SERVER_TIMESTAMP = "TIMESTAMP"
sys.modules['app.core.security'] = MagicMock()
sys.modules['app.core.security'].db = mock_db

# Mock LLM Factory
mock_model = MagicMock()
mock_response = MagicMock()
mock_model.generate_content.return_value = mock_response

# Mock Agents
mock_video_agent = MagicMock()
mock_image_agent = MagicMock()
mock_audio_agent = MagicMock()

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFIER")

# --- TEST LOGIC ---
def test_tutorial_logic():
    print("\n[START] TUTORIAL LOGIC VERIFICATION\n")

    # 1. Setup Data Mocks
    # Blueprint Response
    blueprint_json = {
        "title": "Test Course",
        "pedagogical_metaphor": "Gardening",
        "sections": [
            {"title": "Section 1", "type": "supportive", "goal": "Explain basics"}
        ]
    }
    
    # Asset Response
    assets_json = {
        "assets": [
            {"type": "video_clip", "visual_prompt": "Gardening Intro"},
            {"type": "audio_note", "script": "Summary"}
        ]
    }
    
    # QA Response
    qa_json = {
        "score": 85,
        "status": "PASSED",
        "feedback": "Good job"
    }

    # Complex Mocking for generate_content based on prompt content
    def side_effect(prompt):
        if "Curriculum Blueprint" in prompt:
            print("   [OK] Blueprint Prompt Triggered (Context check pending)")
            if "Active Channels" in prompt:
                print("   [OK] Metricool Context Detected in Prompt")
            else:
                print("   [FAIL] Metricool Context MISSING in Prompt")
            mock_response.text = json.dumps(blueprint_json)
        elif "JSON assets" in prompt:
            mock_response.text = json.dumps(assets_json)
        elif "Pedagogical Quality Assurance" in prompt:
            print("   [OK] QA Audit Triggered")
            mock_response.text = json.dumps(qa_json)
        elif "Constructivist Learning Theory" in prompt:
             mock_response.text = "This is a sufficient length educational narrative text that explains the concept of Digital Marketing using the Gardening metaphor. It needs to be longer than fifty characters to pass the validation check in the code."
        else: # Generic Fallback
             print(f"   [WARN] Unknown Prompt: {prompt[:50]}...")
             mock_response.text = "Generic fallback text that is long enough."
        return mock_response

    mock_model.generate_content.side_effect = side_effect

    # 2. Patch dependencies
    with patch('app.agents.tutorial_agent.get_model', return_value=mock_model), \
         patch('app.agents.tutorial_agent.VideoAgent', return_value=mock_video_agent), \
         patch('app.agents.tutorial_agent.ImageAgent', return_value=mock_image_agent), \
         patch('app.agents.tutorial_agent.AudioAgent', return_value=mock_audio_agent), \
         patch('app.agents.tutorial_agent.MetricoolClient') as MockMetricool:

        # Setup Metricool Mock
        mock_mc = MockMetricool.return_value
        mock_mc.get_account_info.return_value = {"connected": ["instagram", "linkedin"]}

        # Setup Agent Mocks (Simulate Success)
        mock_video_agent.generate_video.return_value = "http://video.mp4"
        mock_audio_agent.generate_audio.return_value = "http://audio.mp3"
        mock_image_agent.generate_image.return_value = "http://image.png"

        # IMPORT AGENT NOW
        from app.agents.tutorial_agent import generate_tutorial

        # 3. RUN TEST CASE 1: SUCCESS PATH
        print("[TEST 1]: Full Success...")
        result = generate_tutorial("user_123", "Digital Marketing")
        
        # VERIFY
        print(f"   Context Channels Fetched: {mock_mc.get_account_info.called}")
        if result['audit_report']['score'] == 85:
             print("   [OK] QA Audit Saved Correctly")
        else:
             print("   [FAIL] QA Audit Missing")
             
        # Verify Summary Audio (should be last section or appended block)
        has_summary = False
        for sec in result['sections']:
            if sec['title'] == "Course Summary":
                has_summary = True
        if has_summary:
            print("   [OK] Final Audio Summary Generated")
        else:
             print("   [FAIL] Final Audio Summary Missing")

        # 4. RUN TEST CASE 2: ROBUST FALLBACK (Video Fail -> Image Success)
        print("\n[TEST 2]: Asset Fallback (Video Fail)...")
        mock_video_agent.generate_video.return_value = None # Fail Video
        
        result_fallback = generate_tutorial("user_123", "Digital Marketing")
        
        found_fallback = False
        for sec in result_fallback['sections']:
             for block in sec.get('blocks', []):
                 if block['type'] == 'image' and block.get('fallback') is True:
                     found_fallback = True
        
        if found_fallback:
            print("   [OK] Video Failure -> Image Fallback Triggered")
        else:
            print("   [FAIL] Fallback Logic Failed")

        # 5. RUN TEST CASE 3: TOTAL FAILURE (Video & Image Fail -> Alert)
        print("\n[TEST 3]: Total Failure (Alerts)...")
        mock_video_agent.generate_video.return_value = None
        mock_image_agent.generate_image.return_value = None
        
        result_fail = generate_tutorial("user_123", "Digital Marketing")
        
        alerts = result_fail.get('generation_alerts', [])
        if len(alerts) > 0:
            print(f"   [OK] Generation Alerts Created: {len(alerts)}")
            # Verify Admin Task creation
            # We look at mock_db.collection('admin_tasks').add
            if mock_db.collection.return_value.document.return_value.collection.return_value.add.call_count > 0 \
               or mock_db.collection('admin_tasks').add.call_count > 0:
                 print("   [OK] Admin Task Mock Called")
        else:
            print("   [FAIL] Generation Alerts Missing")

if __name__ == "__main__":
    test_tutorial_logic()
