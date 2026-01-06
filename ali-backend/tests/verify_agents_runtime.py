
import sys
import os
import logging

# Setup Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runtime_verifier")

def verify_agents():
    print("------- STARTING AGENT VERIFICATION -------")
    errors = []

    # 1. Verify Imports and Types presence
    try:
        from google.genai import types
        print("[OK] [Import] google.genai.types imported successfully.")
        
        # Check for specific types used in code
        required_types = [
            "Part", 
            "GenerateImagesConfig", 
            "GenerateVideosConfig", 
            "GenerateContentConfig"
        ]
        
        for rt in required_types:
            if hasattr(types, rt):
                print(f"  [OK] [Type] Found: {rt}")
            else:
                print(f"  [FAIL] [Type] MISSING: {rt}")
                errors.append(f"Missing Type: {rt}")

    except ImportError as e:
        print(f"[FAIL] [Import] Failed to import google.genai: {e}")
        errors.append("Import Error: google.genai")
        return

    # 2. Verify Image Agent Init
    try:
        print("\n--- Testing ImageAgent ---")
        from app.services.image_agent import ImageAgent
        agent = ImageAgent()
        if agent.client:
            print("[OK] ImageAgent initialized with Vertex Client.")
        else:
            print("[WARN] ImageAgent initialized but Client is None (Auth/Env issue?).")
    except Exception as e:
        print(f"[FAIL] ImageAgent Crash: {e}")
        errors.append(f"ImageAgent: {e}")

    # 3. Verify Video Agent Init
    try:
        print("\n--- Testing VideoAgent ---")
        from app.services.video_agent import VideoAgent
        agent = VideoAgent()
        if agent.client:
            print("[OK] VideoAgent initialized with Vertex Client.")
        else:
            print("[WARN] VideoAgent initialized but Client is None.")
    except Exception as e:
        print(f"[FAIL] VideoAgent Crash: {e}")
        errors.append(f"VideoAgent: {e}")

    # 4. Verify Audio Agent Init
    try:
        print("\n--- Testing AudioAgent ---")
        from app.services.audio_agent import AudioAgent
        agent = AudioAgent()
        if agent.client:
            print("[OK] AudioAgent initialized with Vertex Client.")
        else:
            print("[WARN] AudioAgent initialized but Client is None.")
    except Exception as e:
        print(f"[FAIL] AudioAgent Crash: {e}")
        errors.append(f"AudioAgent: {e}")

    print("\n-------------------------------------------")
    if errors:
        print(f"[FAIL] Verification FAILED with {len(errors)} errors.")
        sys.exit(1)
    else:
        print("[OK] ALL AGENTS PASSED INIT CHECKS.")
        sys.exit(0)

if __name__ == "__main__":
    verify_agents()
