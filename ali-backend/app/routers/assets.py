"""
Assets upload router.
"""
import logging
import asyncio

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.asset_processor import AssetProcessor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload")
async def upload_asset(file: UploadFile = File(...)) -> dict:
    """Upload and process an asset through the AssetProcessor."""
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        processor = AssetProcessor()
        asset_id = file.filename or "asset"
        
        # Run sync method in thread pool to avoid blocking
        result = await asyncio.to_thread(
            processor.process_image,
            image_bytes=file_bytes,
            user_id="anonymous",
            asset_id=asset_id,
            remove_bg=True,
            smart_crop_size=None,
            optimize=True,
            create_thumb=True,
        )
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        return {}

