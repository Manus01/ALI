"""
Asset Processor Service
Spec v2.2 Advertising §8: Asset Processing Pipeline

Provides:
1. Background removal (rembg or Cloud Vision)
2. Smart cropping (focal point detection)
3. Color palette extraction
4. Image optimization for web
"""
import os
import io
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None

try:
    from google.cloud import vision
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    vision = None

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None

logger = logging.getLogger(__name__)


class AssetType(str, Enum):
    """Supported asset types."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


@dataclass
class ProcessedAsset:
    """Result of asset processing."""
    original_url: str
    processed_url: Optional[str]
    thumbnail_url: Optional[str]
    
    # Extracted metadata
    width: int = 0
    height: int = 0
    format: str = ""
    size_bytes: int = 0
    
    # Color analysis
    dominant_colors: List[str] = None  # HEX values
    
    # Processing status
    background_removed: bool = False
    smart_cropped: bool = False
    optimized: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "originalUrl": self.original_url,
            "processedUrl": self.processed_url,
            "thumbnailUrl": self.thumbnail_url,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "sizeBytes": self.size_bytes,
            "dominantColors": self.dominant_colors or [],
            "backgroundRemoved": self.background_removed,
            "smartCropped": self.smart_cropped,
            "optimized": self.optimized,
        }


class AssetProcessor:
    """
    Asset processing service for advertising materials.
    Spec v2.2 §8: Background removal, smart cropping, color extraction.
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or os.getenv(
            "GCS_BUCKET_NAME", 
            "ali-platform-prod-73019.firebasestorage.app"
        )
        
        self.storage_client = None
        self.vision_client = None
        
        if GCS_AVAILABLE:
            try:
                self.storage_client = storage.Client()
            except Exception as e:
                logger.warning(f"⚠️ GCS client init failed: {e}")
        
        if VISION_AVAILABLE:
            try:
                self.vision_client = vision.ImageAnnotatorClient()
            except Exception as e:
                logger.warning(f"⚠️ Vision client init failed: {e}")
    
    def extract_dominant_colors(self, image_bytes: bytes, num_colors: int = 5) -> List[str]:
        """
        Extract dominant colors from image.
        Uses Cloud Vision API if available, falls back to PIL.
        """
        if self.vision_client:
            try:
                image = vision.Image(content=image_bytes)
                response = self.vision_client.image_properties(image=image)
                colors = response.image_properties_annotation.dominant_colors.colors
                
                hex_colors = []
                for color in colors[:num_colors]:
                    r = int(color.color.red)
                    g = int(color.color.green)
                    b = int(color.color.blue)
                    hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")
                
                return hex_colors
            except Exception as e:
                logger.warning(f"⚠️ Vision API color extraction failed: {e}")
        
        # Fallback: PIL-based color extraction
        if PIL_AVAILABLE:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                img = img.convert("RGB")
                img = img.resize((100, 100))  # Reduce for speed
                
                pixels = list(img.getdata())
                from collections import Counter
                color_counts = Counter(pixels)
                
                hex_colors = []
                for (r, g, b), count in color_counts.most_common(num_colors):
                    hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")
                
                return hex_colors
            except Exception as e:
                logger.warning(f"⚠️ PIL color extraction failed: {e}")
        
        return []
    
    def detect_focal_point(self, image_bytes: bytes) -> Tuple[float, float]:
        """
        Detect focal point of image using Cloud Vision.
        Returns (x_ratio, y_ratio) from 0-1 representing the focal point.
        """
        if not self.vision_client:
            return (0.5, 0.5)  # Default to center
        
        try:
            image = vision.Image(content=image_bytes)
            response = self.vision_client.face_detection(image=image)
            
            # If faces detected, use first face as focal point
            if response.face_annotations:
                face = response.face_annotations[0]
                vertices = face.bounding_poly.vertices
                
                # Get center of face bounding box
                x_coords = [v.x for v in vertices]
                y_coords = [v.y for v in vertices]
                
                # We need image dimensions
                props = self.vision_client.image_properties(image=image)
                # Note: Vision API doesn't return dimensions, assume from crop hints
                
                center_x = sum(x_coords) / len(x_coords)
                center_y = sum(y_coords) / len(y_coords)
                
                # Normalize to 0-1 (assuming 1000px for now, improve with actual dims)
                return (center_x / 1000, center_y / 1000)
            
            # Fall back to object detection
            response = self.vision_client.object_localization(image=image)
            if response.localized_object_annotations:
                obj = response.localized_object_annotations[0]
                vertices = obj.bounding_poly.normalized_vertices
                
                center_x = sum(v.x for v in vertices) / len(vertices)
                center_y = sum(v.y for v in vertices) / len(vertices)
                
                return (center_x, center_y)
            
        except Exception as e:
            logger.warning(f"⚠️ Focal point detection failed: {e}")
        
        return (0.5, 0.5)
    
    def smart_crop(
        self, 
        image_bytes: bytes, 
        target_width: int, 
        target_height: int
    ) -> bytes:
        """
        Smart crop image around focal point.
        """
        if not PIL_AVAILABLE:
            logger.warning("⚠️ PIL not available for smart crop")
            return image_bytes
        
        try:
            focal_x, focal_y = self.detect_focal_point(image_bytes)
            
            img = Image.open(io.BytesIO(image_bytes))
            orig_width, orig_height = img.size
            
            # Calculate crop box centered on focal point
            target_ratio = target_width / target_height
            orig_ratio = orig_width / orig_height
            
            if orig_ratio > target_ratio:
                # Image is wider, crop sides
                new_width = int(orig_height * target_ratio)
                new_height = orig_height
                
                focal_x_px = int(focal_x * orig_width)
                left = max(0, focal_x_px - new_width // 2)
                left = min(left, orig_width - new_width)
                
                crop_box = (left, 0, left + new_width, new_height)
            else:
                # Image is taller, crop top/bottom
                new_width = orig_width
                new_height = int(orig_width / target_ratio)
                
                focal_y_px = int(focal_y * orig_height)
                top = max(0, focal_y_px - new_height // 2)
                top = min(top, orig_height - new_height)
                
                crop_box = (0, top, new_width, top + new_height)
            
            cropped = img.crop(crop_box)
            cropped = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            cropped.save(output, format="PNG", optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"❌ Smart crop failed: {e}")
            return image_bytes
    
    def remove_background(self, image_bytes: bytes) -> bytes:
        """
        Remove background from image.
        Uses rembg if available, otherwise returns original.
        """
        try:
            from rembg import remove
            return remove(image_bytes)
        except ImportError:
            logger.warning("⚠️ rembg not installed, skipping background removal")
            return image_bytes
        except Exception as e:
            logger.error(f"❌ Background removal failed: {e}")
            return image_bytes
    
    def optimize_image(
        self, 
        image_bytes: bytes, 
        max_width: int = 1920, 
        quality: int = 85
    ) -> bytes:
        """
        Optimize image for web (resize and compress).
        """
        if not PIL_AVAILABLE:
            return image_bytes
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Resize if too large
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Save as optimized JPEG
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"❌ Image optimization failed: {e}")
            return image_bytes
    
    def create_thumbnail(
        self, 
        image_bytes: bytes, 
        width: int = 300, 
        height: int = 300
    ) -> bytes:
        """Create thumbnail from image."""
        if not PIL_AVAILABLE:
            return image_bytes
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=80)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"❌ Thumbnail creation failed: {e}")
            return image_bytes
    
    def upload_to_gcs(
        self, 
        data: bytes, 
        destination_path: str, 
        content_type: str = "image/png"
    ) -> Optional[str]:
        """Upload processed asset to Cloud Storage."""
        if not self.storage_client:
            logger.warning("⚠️ GCS client not available")
            return None
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(destination_path)
            blob.upload_from_string(data, content_type=content_type)
            blob.make_public()
            
            return blob.public_url
        except Exception as e:
            logger.error(f"❌ GCS upload failed: {e}")
            return None
    
    def process_image(
        self,
        image_bytes: bytes,
        user_id: str,
        asset_id: str,
        remove_bg: bool = False,
        smart_crop_size: Optional[Tuple[int, int]] = None,
        optimize: bool = True,
        create_thumb: bool = True
    ) -> ProcessedAsset:
        """
        Full image processing pipeline.
        
        Args:
            image_bytes: Raw image data
            user_id: User ID for storage path
            asset_id: Unique asset identifier
            remove_bg: Whether to remove background
            smart_crop_size: Target (width, height) for smart crop
            optimize: Whether to optimize for web
            create_thumb: Whether to create thumbnail
        """
        processed_bytes = image_bytes
        result = ProcessedAsset(
            original_url="",  # Will be set after upload
            processed_url=None,
            thumbnail_url=None,
            dominant_colors=[]
        )
        
        # 1. Extract colors (before any processing)
        result.dominant_colors = self.extract_dominant_colors(image_bytes)
        
        # 2. Background removal
        if remove_bg:
            processed_bytes = self.remove_background(processed_bytes)
            result.background_removed = True
        
        # 3. Smart crop
        if smart_crop_size:
            processed_bytes = self.smart_crop(
                processed_bytes, 
                smart_crop_size[0], 
                smart_crop_size[1]
            )
            result.smart_cropped = True
        
        # 4. Optimize
        if optimize:
            processed_bytes = self.optimize_image(processed_bytes)
            result.optimized = True
        
        # 5. Get dimensions
        if PIL_AVAILABLE:
            try:
                img = Image.open(io.BytesIO(processed_bytes))
                result.width = img.width
                result.height = img.height
                result.format = img.format or "JPEG"
            except:
                pass
        
        result.size_bytes = len(processed_bytes)
        
        # 6. Upload processed image
        processed_path = f"assets/{user_id}/{asset_id}/processed.jpg"
        result.processed_url = self.upload_to_gcs(
            processed_bytes, 
            processed_path, 
            "image/jpeg"
        )
        
        # 7. Create and upload thumbnail
        if create_thumb:
            thumb_bytes = self.create_thumbnail(processed_bytes)
            thumb_path = f"assets/{user_id}/{asset_id}/thumb.jpg"
            result.thumbnail_url = self.upload_to_gcs(
                thumb_bytes, 
                thumb_path, 
                "image/jpeg"
            )
        
        logger.info(f"✅ Processed asset {asset_id}: {result.width}x{result.height}")
        return result
    
    # --- HEADLESS RENDERING (v2.2 §7.2: SVG/Mermaid → Raster Export) ---
    
    async def render_svg_to_raster(
        self,
        svg_content: str,
        output_format: str = "png",
        width: int = 1200,
        height: int = 630
    ) -> bytes:
        """
        Convert SVG content to raster image (PNG/JPG) using headless Chromium.
        Spec v2.2 §7.2: Export SVG/HTML to PNG/JPG on download.
        
        Args:
            svg_content: Raw SVG markup string
            output_format: 'png' or 'jpeg'
            width: Viewport width
            height: Viewport height (auto-adjusted if 0)
            
        Returns:
            Image bytes in requested format
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("⚠️ Playwright not available for SVG rendering")
            return b""
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": width, "height": height or 800})
                
                # Wrap SVG in minimal HTML for proper rendering
                html = f"""
                <!DOCTYPE html>
                <html>
                <head><style>body {{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:transparent;}}</style></head>
                <body>{svg_content}</body>
                </html>
                """
                await page.set_content(html, wait_until="networkidle")
                
                screenshot = await page.screenshot(
                    type=output_format if output_format in ["png", "jpeg"] else "png",
                    full_page=True if height == 0 else False,
                    omit_background=True if output_format == "png" else False
                )
                
                await browser.close()
                logger.info(f"✅ Rendered SVG to {output_format.upper()} ({width}x{height})")
                return screenshot
                
        except Exception as e:
            logger.error(f"❌ SVG render failed: {e}")
            return b""
    
    async def render_mermaid_to_image(
        self,
        mermaid_code: str,
        theme: str = "default",
        width: int = 1200,
        output_format: str = "png"
    ) -> bytes:
        """
        Render Mermaid diagram to raster image.
        Uses Mermaid.js CDN for client-side rendering.
        
        Args:
            mermaid_code: Mermaid diagram syntax (without ```mermaid fences)
            theme: Mermaid theme ('default', 'dark', 'forest', 'neutral')
            width: Viewport width
            output_format: 'png' or 'jpeg'
            
        Returns:
            Image bytes of rendered diagram
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("⚠️ Playwright not available for Mermaid rendering")
            return b""
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": width, "height": 800})
                
                # HTML page with Mermaid.js CDN
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
                    <style>
                        body {{margin:20px;background:#fff;}}
                        .mermaid {{display:flex;justify-content:center;}}
                    </style>
                </head>
                <body>
                    <div class="mermaid">
                    {mermaid_code}
                    </div>
                    <script>mermaid.initialize({{startOnLoad:true,theme:'{theme}'}});</script>
                </body>
                </html>
                """
                
                await page.set_content(html, wait_until="networkidle")
                # Wait for Mermaid to render
                await page.wait_for_selector(".mermaid svg", timeout=10000)
                
                # Get the actual SVG element bounds
                mermaid_div = await page.query_selector(".mermaid")
                box = await mermaid_div.bounding_box() if mermaid_div else None
                
                screenshot = await page.screenshot(
                    type=output_format,
                    clip=box if box else None,
                    omit_background=output_format == "png"
                )
                
                await browser.close()
                logger.info(f"✅ Rendered Mermaid diagram ({theme} theme) to {output_format.upper()}")
                return screenshot
                
        except Exception as e:
            logger.error(f"❌ Mermaid render failed: {e}")
            return b""
    
    async def render_html_to_image(
        self,
        html_content: str,
        width: int = 1200,
        height: int = 630,
        output_format: str = "png"
    ) -> bytes:
        """
        Render HTML creative to raster image.
        Used for HTML5 ad banners and landing page previews.
        
        Args:
            html_content: Complete HTML document or snippet
            width: Viewport width
            height: Viewport height
            output_format: 'png' or 'jpeg'
            
        Returns:
            Screenshot bytes
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("⚠️ Playwright not available for HTML rendering")
            return b""
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": width, "height": height})
                
                # Check if it's a full HTML document or just a snippet
                if not html_content.strip().lower().startswith("<!doctype") and not html_content.strip().lower().startswith("<html"):
                    html_content = f"<!DOCTYPE html><html><body>{html_content}</body></html>"
                
                await page.set_content(html_content, wait_until="networkidle")
                
                screenshot = await page.screenshot(
                    type=output_format,
                    full_page=False,
                    omit_background=output_format == "png"
                )
                
                await browser.close()
                logger.info(f"✅ Rendered HTML to {output_format.upper()} ({width}x{height})")
                return screenshot
                
        except Exception as e:
            logger.error(f"❌ HTML render failed: {e}")
            return b""

_asset_processor: Optional[AssetProcessor] = None

def get_asset_processor() -> AssetProcessor:
    """Get or create singleton AssetProcessor."""
    global _asset_processor
    if _asset_processor is None:
        _asset_processor = AssetProcessor()
    return _asset_processor
