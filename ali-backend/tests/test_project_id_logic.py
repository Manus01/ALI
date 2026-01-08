import sys

# Precise path to ali-backend
sys.path.append(r"d:\github\repos\Manus01\ALI\ali-backend")

from unittest.mock import patch, MagicMock
from app.legacy.video_agent import VideoAgent

# Mock google.genai to avoid actual API calls and credential checks
sys.modules["google.genai"] = MagicMock()
from app.legacy.video_agent import genai

@patch("os.getenv")
def test_video_agent_accepts_string_id(mock_getenv):
    print("Testing VideoAgent with string Project ID...")
    # Setup - simulate a string project ID environment
    mock_getenv.side_effect = lambda k, d=None: "my-string-project-id" if k in ["GENAI_PROJECT_ID", "PROJECT_ID"] else d
    
    # Mock the client constructor to verify arguments
    mock_client_instance = MagicMock()
    genai.Client = MagicMock(return_value=mock_client_instance)
    
    # Execute
    agent = VideoAgent()
    
    # Verify
    if agent.client is not None:
        print("✅ Client initialized successfully.")
    else:
        print("❌ Client failed to initialize.")
        exit(1)
        
    # Check if Client was called with the string ID
    genai.Client.assert_called_with(vertexai=True, project="my-string-project-id", location="us-central1")
    print("✅ VideoAgent correctly used string project ID 'my-string-project-id'.")

if __name__ == "__main__":
    test_video_agent_accepts_string_id()
