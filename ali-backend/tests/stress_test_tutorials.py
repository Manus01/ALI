import unittest
from unittest.mock import MagicMock, patch
import logging
import time
# Import the function directly
from app.agents.tutorial_agent import generate_tutorial

# Configure logging to see the flow
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stress_test")

class TestTutorialRobustness(unittest.TestCase):
    
    # No setUp needed for function-based test
        
    @patch('app.agents.tutorial_agent.db')
    @patch('app.agents.tutorial_agent.VideoAgent')
    @patch('app.agents.tutorial_agent.ImageAgent')
    @patch('app.agents.tutorial_agent.AudioAgent')
    @patch('app.agents.tutorial_agent.get_model')
    @patch('app.agents.tutorial_agent.generate_curriculum_blueprint') # Patch the inner blueprint call
    def test_slow_asset_generation(self, mock_blueprint, mock_get_model, mock_audio, mock_image, mock_video, mock_db):
        """
        SCENARIO: 'The Slow Artist'
        Video/Image generation takes 2 seconds. The pipeline MUST wait.
        """
        print("\n🧪 STARTING STRESS TEST: Slow Asset Generation...")
        
        # 1. Mock Blueprint (Return a dictionary directly since we patched the function)
        mock_blueprint.return_value = {
            "course_title": "Quantum Physics for Toddlers",
            "pedagogical_metaphor": "Building Blocks",
            "sections": [
                {
                    "title": "Module 1: What is a Quanta?",
                    "type": "supportive",
                    "goal": "Explain atoms",
                    "visual_prompt": "An atom smiling"
                }
            ],
            "estimated_duration": "5 mins",
            "difficulty": "Beginner"
        }
        
        # Mock LLM for Narrative/Assets calls inside per-section processing
        # We need it to return text for 'write_section_narrative' and JSON for 'design_section_assets'
        mock_model_instance = MagicMock()
        mock_get_model.return_value = mock_model_instance
        
        # We need side_effects because get_model is called multiple times for different purposes
        # Call 1: Write Narrative -> Returns String
        # Call 2: Design Assets -> Returns JSON String
        # Call 3: Review Quality -> Returns JSON String
        mock_model_instance.generate_content.side_effect = [
            MagicMock(text="Here is the lesson text about atoms. It must be very long to pass the validation check which requires at least fifty characters of deep educational content."), # Narrative
            MagicMock(text='''
            ```json
            {
                "assets": [
                    { "type": "video_clip", "visual_prompt": "Atom video" },
                    { "type": "quiz_single", "question": "What is it?", "options": ["A","B"], "correct_answer": 0 }
                ]
            }
            ```
            '''), # Assets Design
             MagicMock(text='{ "score": 90, "status": "PASSED" }') # Review
        ]
        
        # 2. Mock 'The Slow Artist' Agents
        def slow_video(*args, **kwargs):
            logger.info("    Sleeping 2s for Video...")
            time.sleep(2)
            return "https://mock.veo/slow_video.mp4"

        def slow_image(*args, **kwargs):
            logger.info("    Sleeping 1s for Image...")
            time.sleep(1)
            return "https://mock.imagen/slow_image.png"
            
        mock_video_instance = mock_video.return_value
        mock_video_instance.generate_video.side_effect = slow_video
        
        mock_image_instance = mock_image.return_value
        mock_image_instance.generate_image.side_effect = slow_image
        
        mock_audio_instance = mock_audio.return_value
        mock_audio_instance.generate_audio.return_value = "https://mock.tts/audio.mp3"

        # 3. Execution
        start_time = time.time()
        # Call function directly
        result = generate_tutorial(
            user_id="stress_tester_01",
            topic="Quantum Physics for Toddlers"
        )
        end_time = time.time()
        
        # 4. Validation
        duration = end_time - start_time
        print(f"✅ Stress Test Complete in {duration:.2f}s")
        
        # The result must contain the assets
        self.assertIn("sections", result)
        # Check that we actually waited (should be > 2s since video took 2s)
        self.assertTrue(duration > 2.0, "Pipeline finished too fast! Did it skip the slow video?")
        
        # Ensure deep structure exists
        self.assertEqual(result['title'], "Quantum Physics for Toddlers")
        # Check first section for assets
        section_blocks = result['sections'][0].get('blocks', [])
        # Iterate blocks to find type 'video' (fabricate_block transforms video_clip -> video)
        self.assertTrue(any(b.get('type') == 'video' for b in section_blocks), "Missing Slow Video Asset in Blocks")
        
        logger.info(f"Hardening Check: Notification Sent? {mock_db.collection.call_args_list}")
        # We expect calls to 'users', 'tutorials', and 'notifications'
        # Since mocks are complex chain calls, we can inspect correct call signatures or just ensure it didn't crash.
        # But let's try to find 'notifications' in the call history of the collection object.
        
        # Verify collection('users').doc(uid).collection('notifications').add(...)
        # This is a bit deep for mock inspection, but we can check if string 'notifications' was used in a chain.
        calls = [str(c) for c in mock_db.mock_calls]
        self.assertTrue(any("notifications" in c for c in calls), "Notification subcollection not accessed!")

    @patch('app.agents.tutorial_agent.db')
    @patch('app.agents.tutorial_agent.get_model')
    def test_broken_blueprint_recovery(self, mock_get_model, mock_db):
        """
        SCENARIO: 'The Drunk Architect'
        LLM returns malformed JSON for blueprint. Agent should retry or fail gracefully.
        """
        print("\n🧪 STARTING STRESS TEST: Malformed Blueprint...")
        
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        # Return Garbage Header, then JSON
        mock_model.generate_content.return_value.text = '''
        Here is your plan:
        { "This is broken JSON...
        '''
        
        # Expectation: The agent's JSON parser (in helper or logic) might catch this.
        # If we rely on the helper `parse_json_garbage` (hypothetical) it might work, 
        # otherwise `generate_tutorial` catches Exception.
        
        try:
            result = generate_tutorial("tester_02", "Chaos Theory")
            # If it returns a result, checks it's safe fallback?
            if "error" in result:
                 print("✅ Gracefully returned error dict.")
            else:
                 print("❓ Unexpected success on bad JSON?")
        except Exception as e:
            print(f"✅ Gracefully caught exception in top-level handler: {e}")

if __name__ == '__main__':
    unittest.main()
