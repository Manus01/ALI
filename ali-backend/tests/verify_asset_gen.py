
import asyncio
import os
import shutil
import logging
from unittest.mock import MagicMock, patch
import tempfile

# Add app to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.asset_processor import AssetProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_asset_gen")

async def test_asset_generation():
    logger.info("🚀 Starting Asset Generation Verification")
    
    # Mock specific GCS upload to avoid network calls
    with patch.object(AssetProcessor, 'upload_to_gcs', return_value="https://storage.googleapis.com/test-bucket/video.mp4") as mock_upload:
        
        processor = AssetProcessor()
        
        # Test Data
        html_content = """
        <!DOCTYPE html>
        <html>
            <body style="background: blue; height: 100vh; display: flex; align-items: center; justify-content: center;">
                <h1 style="color: white; font-size: 3rem;">VERIFICATION TEST</h1>
            </body>
        </html>
        """
        user_id = "test_user_verify"
        asset_id = "test_asset_verify"
        
        # 1. Test Video Generation
        logger.info("🎥 Testing generate_video_asset...")
        url = await processor.generate_video_asset(
            html_content=html_content,
            user_id=user_id,
            asset_id=asset_id,
            width=720,
            height=1280,
            duration=2.0
        )
        
        if url:
             logger.info(f"✅ Video URL generated: {url}")
        else:
             logger.error("❌ Video generation returned None")

        # 2. Check Mock Calls
        if mock_upload.called:
            args, kwargs = mock_upload.call_args
            content_type = kwargs.get('content_type')
            logger.info(f"📤 Upload called with Content-Type: {content_type}")
            
            # Check if MP4 or WebM
            if content_type == "video/mp4" and shutil.which("ffmpeg"):
                 logger.info("✅ FFmpeg utilized: Uploaded as video/mp4")
            elif content_type == "video/webm":
                 logger.info("⚠️ No FFmpeg or conversion failed: Uploaded as video/webm")
        else:
            logger.error("❌ Upload was never called!")

        # 3. Verify Temp Directory Cleanup
        # We can't easily check this as the method checks it internally, 
        # but we can verify no crash occurred.

if __name__ == "__main__":
    asyncio.run(test_asset_generation())
