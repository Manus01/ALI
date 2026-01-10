import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock GCS and Vision to isolate AssetProcessor logic
from unittest.mock import MagicMock, patch
sys.modules['google.cloud'] = MagicMock()
sys.modules['google.cloud.storage'] = MagicMock()
sys.modules['google.cloud.vision'] = MagicMock()

from app.services.asset_processor import AssetProcessor

async def test_asset_generation():
    print("\nTesting Asset Generation Logic...")
    
    # 1. Instantiate Processor
    processor = AssetProcessor()
    # Mock upload to avoid GCS errors
    processor.upload_to_gcs = MagicMock(return_value="https://storage.googleapis.com/mock-bucket/assets/test.png")
    
    # 2. Test Smart Image Generation (Mocking Playwright to verify logic flow)
    print("\n[Test 1] Generating Image Asset...")
    html_content = """
    <div id="bg" style="background:red;width:100%;height:100%;">
        <h1 style="color:white;">Hello World</h1>
    </div>
    """
    
    # We will try to run it. If playwright is missing, we catch it.
    # But for verification of *logic*, checking if it calls playwright correct is enough if we can't run it.
    # The user asked to "Test we can generate material".
    
    try:
        url = await processor.generate_image_asset(
            html_content=html_content,
            user_id="test_user",
            asset_id="test_asset_001",
            width=1080,
            height=1080
        )
        if url:
            print(f"[OK] Image Generation Success: {url}")
        else:
            print("[FAIL] Image Generation Returned None (Check logs for Playwright/Browser issues)")
            
    except Exception as e:
        print(f"[FAIL] Image Generation Failed with Exception: {e}")

    # 3. Test Video Generation Logic
    print("\n[Test 2] Generating Video Asset...")
    try:
        # Mocking record_html_animation to avoid needing ffmpeg/heavy interaction in this simple check
        # But we want to test the flow
        with patch.object(processor, 'record_html_animation', new_callable=MagicMock) as mock_record:
            mock_record.return_value = "https://mock-url.com/video.mp4"
            
            url = await processor.generate_video_asset(
                html_content=html_content,
                user_id="test_user",
                asset_id="test_video_001",
                fallback_to_image=True
            )
            
            if url:
                print(f"[OK] Video Generation Flow Success: {url}")
            else:
                print("[FAIL] Video Generation Failed")
                
    except Exception as e:
        print(f"[FAIL] Video Generation Failed with Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_asset_generation())
