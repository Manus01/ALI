import os
import sys
from unittest.mock import MagicMock

# --- 1. PRE-IMPORT PATCHING ---
# We must mock these BEFORE any app modules are imported by pytest collection.
# This prevents side effects like vertexai.init() or firebase_admin.initialize_app() running.

# Mock Vertex AI
mock_vertexai = MagicMock()
sys.modules["vertexai"] = mock_vertexai
sys.modules["vertexai.generative_models"] = MagicMock()
sys.modules["vertexai.preview"] = MagicMock()
sys.modules["vertexai.preview.generative_models"] = MagicMock()

# Mock Firebase Admin
mock_firebase = MagicMock()
mock_firebase._apps = {} 
sys.modules["firebase_admin"] = mock_firebase
sys.modules["firebase_admin.firestore"] = MagicMock()
sys.modules["firebase_admin.auth"] = MagicMock()
sys.modules["firebase_admin.credentials"] = MagicMock()

# Set Environment Variables
os.environ["GENAI_PROJECT_ID"] = "test-project"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
os.environ["FIREBASE_CREDENTIALS_PATH"] = "dummy/path/service-account.json"
os.environ["VERTEX_LOCATION"] = "us-central1"

import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_global_mocks():
    """
    Ensure mocks stay valid throughout the session.
    """
    # Double check standard library imports didn't override sys.modules
    # (Unlikely but good practice)
    pass
