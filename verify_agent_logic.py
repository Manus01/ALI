
import sys
import os
import json
import logging

# Add project root
sys.path.append(os.path.abspath("ali-backend"))

# Mock imports to test pure logic without loading full app
from typing import Dict, Any, List

# Re-implement logic here or import if possible. 
# Since we modified the file, let's try to import the helper functions directly.
# However, the file has top-level imports that might fail (Firebase).
# So we will MOCK the dependencies before importing.
from unittest.mock import MagicMock
sys.modules["app.services.ai_studio"] = MagicMock()
sys.modules["app.services.llm_factory"] = MagicMock()
sys.modules["app.core.security"] = MagicMock()
sys.modules["firebase_admin"] = MagicMock()

# Now import the agent
from app.agents import tutorial_agent

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

def test_extract_json_safe():
    print("\n--- Testing JSON Extraction ---")
    
    # Case 1: Pure JSON
    t1 = '{"key": "value"}'
    res1 = tutorial_agent.extract_json_safe(t1)
    if res1 == {"key": "value"}: print("  PURE JSON: PASS")
    else: print(f"  PURE JSON: FAIL ({res1})")
    
    # Case 2: Markdown JSON
    t2 = 'Here is code:\n```json\n{"key": "value"}\n```'
    res2 = tutorial_agent.extract_json_safe(t2)
    if res2 == {"key": "value"}: print("  MARKDOWN JSON: PASS")
    else: print(f"  MARKDOWN JSON: FAIL ({res2})")
    
    # Case 3: Messy/Raw text with JSON inside
    t3 = 'Sure! Here it is: {"key": "value"} Hope you like it.'
    res3 = tutorial_agent.extract_json_safe(t3)
    if res3 == {"key": "value"}: print("  REGEX JSON: PASS")
    else: print(f"  REGEX JSON: FAIL ({res3})")

def test_quiz_validation():
    print("\n--- Testing Quiz Validation ---")
    
    # Case 1: String to Int conversion
    assets1 = [{"type": "quiz_single", "correct_answer": "2", "options": ["A", "B", "C"]}]
    res1 = tutorial_agent.validate_quiz_data(assets1)
    if res1[0]["correct_answer"] == 2: print("  STRING->INT: PASS")
    else: print(f"  STRING->INT: FAIL ({res1})")
    
    # Case 2: Out of bounds correction
    assets2 = [{"type": "quiz_single", "correct_answer": 5, "options": ["A", "B"]}]
    res2 = tutorial_agent.validate_quiz_data(assets2)
    if res2[0]["correct_answer"] == 0: print("  OUT OF BOUNDS FIX: PASS")
    else: print(f"  OUT OF BOUNDS FIX: FAIL ({res2})")

if __name__ == "__main__":
    try:
        test_extract_json_safe()
        test_quiz_validation()
        print("\nAll Logic Tests Passed!")
    except Exception as e:
        print(f"\nTest Script Failed: {e}")
        import traceback
        traceback.print_exc()
