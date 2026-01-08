"""
Assets Router
Spec v2.2 §8: Centralized Asset Processing Pipeline

Provides POST /assets/process endpoint for unified image processing:
- Smart cropping (focal point detection)
- Background removal
- Image optimization
- Upload to Cloud Storage
"""
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException

from app.core.security import verify_token
from app.services.asset_processor import get_asset_processor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/process")
async def process_asset(
    file: UploadFile = File(...),
    remove_bg: bool = Form(default=True),
    smart_crop: bool = Form(default=False),
    crop_width: Optional[int] = Form(default=None),
    crop_height: Optional[int] = Form(default=None),
    optimize: bool = Form(default=True),
    create_thumbnail: bool = Form(default=True),
    user: dict = Depends(verify_token)
):
    """
    Process an uploaded image through the asset pipeline.
    
    All images are:
    - Smart-cropped (if dimensions provided)
    - Background-removed by default
    - Optimized for web delivery
    - Uploaded to Cloud Storage with persistent URLs
    
    Args:
        file: Image file (PNG, JPG, SVG)
        remove_bg: Remove background (default: True)
        smart_crop: Enable smart cropping (default: False, requires crop_width/height)
        crop_width: Target width for smart crop
        crop_height: Target height for smart crop
        optimize: Optimize for web (default: True)
        create_thumbnail: Create thumbnail version (default: True)
    
    Returns:
        ProcessedAsset with URLs and metadata
    """
    user_id = user.get("uid")
    
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file.content_type}. Allowed: {allowed_types}"
        )
    
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=413, detail="File too large. Max size: 10MB")
        
        # Get asset processor
        processor = get_asset_processor()
        
        # Generate unique asset ID from filename
        import uuid
        asset_id = f"{uuid.uuid4().hex[:8]}_{file.filename or 'asset'}"
        
        # Determine smart crop dimensions
        smart_crop_size = None
        if smart_crop and crop_width and crop_height:
            smart_crop_size = (crop_width, crop_height)
        
        # Process through pipeline
        result = await processor.process_image(
            image_bytes=file_bytes,
            user_id=user_id,
            asset_id=asset_id,
            remove_bg=remove_bg,
            smart_crop_size=smart_crop_size,
            optimize=optimize,
            create_thumb=create_thumbnail
        )
        
        logger.info(f"✅ Asset processed for user {user_id}: {asset_id}")
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Asset processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Asset processing failed: {str(e)}")


@router.post("/process-url")
async def process_asset_from_url(
    image_url: str = Form(...),
    remove_bg: bool = Form(default=True),
    smart_crop: bool = Form(default=False),
    crop_width: Optional[int] = Form(default=None),
    crop_height: Optional[int] = Form(default=None),
    optimize: bool = Form(default=True),
    user: dict = Depends(verify_token)
):
    """
    Process an image from URL through the asset pipeline.
    
    Useful for re-processing existing assets or external images.
    """
    import aiohttp
    
    user_id = user.get("uid")
    
    try:
        # Download image from URL
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url, timeout=30) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail=f"Failed to fetch image: HTTP {response.status}")
                
                file_bytes = await response.read()
        
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Image too large. Max size: 10MB")
        
        processor = get_asset_processor()
        
        import uuid
        asset_id = f"{uuid.uuid4().hex[:8]}_reprocessed"
        
        smart_crop_size = None
        if smart_crop and crop_width and crop_height:
            smart_crop_size = (crop_width, crop_height)
        
        result = await processor.process_image(
            image_bytes=file_bytes,
            user_id=user_id,
            asset_id=asset_id,
            remove_bg=remove_bg,
            smart_crop_size=smart_crop_size,
            optimize=optimize,
            create_thumb=True
        )
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ URL asset processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Asset processing failed: {str(e)}")
