
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath("ali-backend"))

print("--- Testing Imports ---")

try:
    print("Importing app.core.security...")
    from app.core.security import db
    print(" OK: app.core.security imported")
except ImportError as e:
    print(f" FAIL: app.core.security FAILED: {e}")

try:
    print("Importing app.services.llm_factory...")
    from app.services.llm_factory import get_model
    print(" OK: app.services.llm_factory imported")
except ImportError as e:
    print(f" FAIL: app.services.llm_factory FAILED: {e}")

try:
    print("Importing app.services.ai_studio...")
    from app.services.ai_studio import CreativeService
    print(" OK: app.services.ai_studio imported")
except ImportError as e:
    print(f" FAIL: app.services.ai_studio FAILED: {e}")

try:
    print("Importing app.agents.tutorial_agent...")
    from app.agents.tutorial_agent import generate_tutorial
    print(" OK: app.agents.tutorial_agent imported")
except ImportError as e:
    print(f" FAIL: app.agents.tutorial_agent FAILED: {e}")

try:
    print("Importing app.services.job_runner...")
    from app.services.job_runner import process_tutorial_job
    print(" OK: app.services.job_runner imported")
except ImportError as e:
    print(f" FAIL: app.services.job_runner FAILED: {e}")

try:
    print("Importing app.routers.tutorials...")
    from app.routers import tutorials
    print(" OK: app.routers.tutorials imported")
except ImportError as e:
    print(f" FAIL: app.routers.tutorials FAILED: {e}")

print("--- Test Complete ---")
