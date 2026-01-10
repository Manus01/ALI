
import asyncio
import os
import sys
import logging
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reproduce_issue")

async def test_video_generation():
    logger.info("🚀 Starting Video Generation Test")
    
    # 1. Test Path Creation
    asset_id = "test_asset_001"
    temp_dir = f"/tmp/videos/{asset_id}"
    logger.info(f"📂 Attempting to create temp dir: {temp_dir}")
    
    try:
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"✅ Temp dir created: {os.path.abspath(temp_dir)}")
    except Exception as e:
        logger.error(f"❌ Failed to create temp dir: {e}")
        # Try finding a working temp dir
        import tempfile
        correct_temp = os.path.join(tempfile.gettempdir(), "videos", asset_id)
        logger.info(f"💡 Suggestion: Use {correct_temp}")
        return

    # 2. Test Playwright Recording
    logger.info("🎥 Attempting Playwright Recording...")
    try:
        async with async_playwright() as p:
            logger.info("Browser launching...")
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            logger.info("Browser launched.")
            
            # Create context with video recording
            context = await browser.new_context(
                viewport={"width": 1080, "height": 1920},
                record_video_dir=temp_dir,
                record_video_size={"width": 1080, "height": 1920}
            )
            
            page = await context.new_page()
            
            # Simple Content
            html_content = """
            <!DOCTYPE html>
            <html>
                <body style="background: linear-gradient(45deg, #ff0000, #00ff00); height: 100vh; margin: 0; display: flex; align-items: center; justify-content: center;">
                    <h1 style="color: white; font-size: 5rem; font-family: sans-serif;">TEST VIDEO</h1>
                </body>
            </html>
            """
            
            await page.set_content(html_content)
            
            # Wait a bit
            logger.info("Recording for 2 seconds...")
            await asyncio.sleep(2)
            
            await context.close()
            await browser.close()
            
            # Check for file
            files = os.listdir(temp_dir)
            logger.info(f"📂 Files in temp dir: {files}")
            
            if not files:
                logger.error("❌ No video file generated!")
            else:
                video_file = os.path.join(temp_dir, files[0])
                size = os.path.getsize(video_file)
                logger.info(f"✅ Video generated: {files[0]} ({size} bytes)")
                
                # Check magic bytes for WebM vs MP4
                with open(video_file, 'rb') as f:
                    header = f.read(4)
                    logger.info(f"🔍 File Header: {header.hex()}")
                    # WebM usually starts with 1A 45 DF A3 (EBML)
                    # MP4 usually has ftyp box
                    
    except Exception as e:
        logger.error(f"❌ Playwright failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_video_generation())
