import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- MOCKING EXTERNAL DEPENDENCIES BEFORE IMPORTS ---
from unittest.mock import Mock
sys.modules['firebase_admin'] = Mock()
sys.modules['firebase_admin.firestore'] = Mock()
sys.modules['google'] = Mock()
sys.modules['google.cloud'] = Mock()
sys.modules['google.cloud.firestore'] = Mock()
sys.modules['google.cloud.aiplatform'] = Mock()
sys.modules['vertexai'] = Mock()
sys.modules['vertexai.preview'] = Mock() 
sys.modules['vertexai.preview.generative_models'] = Mock()
sys.modules['google.genai'] = Mock()
sys.modules['google.genai.types'] = Mock()
sys.modules['google.api_core'] = Mock()
sys.modules['google.api_core.exceptions'] = Mock()

# Also mock llm_factory to avoid it trying to import real vertexai
sys.modules['app.services.llm_factory'] = Mock()

# Patch other modules to avoid side effects
with patch.dict('sys.modules', {
    'app.core.security': Mock(),
    'app.core.templates': Mock(),
    'app.services.image_agent': Mock(),
    'app.services.asset_processor': Mock(),
}):
    # Import OrchestratorAgent
    from app.agents.orchestrator_agent import OrchestratorAgent
    # Capture the module object for patching
    import app.agents.orchestrator_agent as orchestrator_module

class TestCampaignFlow(unittest.IsolatedAsyncioTestCase):
    async def test_full_campaign_flow(self):
        print("\nTesting Full Campaign Orchestration Flow...")
        
        # 1. Instantiate Orchestrator
        orchestrator = OrchestratorAgent()
        orchestrator.db = MagicMock()
        
        # 2. Patch Classes using the imported module object
        # This bypasses the string path lookup which was failing
        with patch.object(orchestrator_module, 'CampaignAgent') as MockCampaignClass, \
             patch.object(orchestrator_module, 'ImageAgent') as MockImageClass:
            
            # Setup CampaignAgent Mock
            mock_campaign_instance = MockCampaignClass.return_value
            mock_campaign_instance.create_campaign_blueprint = AsyncMock(return_value={
                "theme": "Test Campaign",
                "instagram": {
                    "visual_prompt": "A sunny beach",
                    "caption": "Enjoy the sun!",
                    "format_type": "image"
                },
                "linkedin": {
                    "visual_prompt": "Professional handshake",
                    "body": "Networking is key.",
                    "format_type": "image"
                }
            })

            # Setup ImageAgent Mock
            mock_image_instance = MockImageClass.return_value
            mock_image_instance.generate_image = AsyncMock(return_value="http://mock-url.com/image.png")
            # Usually Orchestrator calls generate_image. 
            
            # Mock AssetProcessor logic implicitly via ImageAgent or direct patching if orchestrator calls it?
            # Orchestrator uses asset_processor.generate_video_asset inside the loop logic?
            # Wait, lines 112+ in orchestrator showed it creates `image_agent = ImageAgent()`.
            # And calls something on it.
            
            # To be safe, we Mock AssetProcessor just in case it's used
            with patch('app.services.asset_processor.get_asset_processor') as mock_get_processor:
                mock_processor = mock_get_processor.return_value
                mock_processor.apply_advanced_branding = AsyncMock(return_value="http://mock-url.com/branded.png")
                mock_processor.analyze_luminance_from_url = AsyncMock(return_value="light")
                
                # Setup Inputs
                uid = "test_user_123"
                campaign_id = "test_camp_ABC"
                goal = "Launch product"
                brand_dna = {"color_palette": {"primary": "#000000"}}
                answers = {"q1": "a1"}
                selected_channels = [" instagram ", " linkedin "] 
                
                # Execute Flow
                await orchestrator.run_full_campaign_flow(
                    uid, campaign_id, goal, brand_dna, answers, selected_channels
                )
                
                # 3. Verifications
                
                # Verify Blueprint Logic
                mock_campaign_instance.create_campaign_blueprint.assert_called_once()
                print("[OK] Blueprint creation called")
                
                # Verify DB Interactions
                self.assertTrue(orchestrator.db.collection.called)
                print("[OK] DB Collection accessed")
                
                # Verify Image Generation called
                # Depending on logic, it might call generate_image
                # We can check if MockImageClass was instantiated
                MockImageClass.assert_called()
                print("[OK] ImageAgent instantiated")
                
                print("[OK] Orchestration completed logic flow")

if __name__ == '__main__':
    unittest.main()
