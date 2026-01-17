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
from typing import Dict, Any, Optional, List, Tuple, Union
import subprocess
import shutil
import tempfile
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


# ============================================================================
# Phase 2: Google Fonts Mapping for Brand DNA Fonts
# Maps common system/brand fonts to closest Google Font equivalents
# ============================================================================
GOOGLE_FONT_MAPPING = {
    # Sans-serif defaults
    "arial": "Inter",
    "helvetica": "Inter",
    "helvetica neue": "Inter",
    "verdana": "Open Sans",
    "tahoma": "Open Sans",
    "segoe ui": "Inter",
    "roboto": "Roboto",
    # Serif defaults
    "times new roman": "Playfair Display",
    "times": "Playfair Display",
    "georgia": "DM Serif Display",
    "palatino": "Libre Baskerville",
    # Display fonts
    "impact": "Anton",
    "comic sans": "Patrick Hand",
    "comic sans ms": "Patrick Hand",
    # Monospace
    "courier": "Roboto Mono",
    "courier new": "Roboto Mono",
    "monaco": "Fira Code"
}


def map_font_to_google_font(font_name: str) -> str:
    """
    Map a DNA font to the closest Google Font equivalent.
    
    Args:
        font_name: Font name from brand DNA (e.g., "Arial", "Helvetica")
        
    Returns:
        Google Font name or original if already a Google Font
    """
    if not font_name:
        return "Inter"  # Default fallback
    normalized = font_name.lower().strip()
    return GOOGLE_FONT_MAPPING.get(normalized, font_name)


# ============================================================================
# V6.0: Browser Pool Pattern - Pre-warmed Chromium instances for faster rendering
# Eliminates cold-start overhead of ~1-2s per asset
# ============================================================================
class BrowserPool:
    """
    Singleton pool of pre-warmed Chromium browser instances.
    Reduces browser startup overhead from ~1-2s to near-zero.
    
    Usage:
        browser = await BrowserPool.acquire()
        try:
            page = await browser.new_page(...)
            # ... do work ...
        finally:
            await BrowserPool.release(browser)
    """
    _playwright = None
    _browsers: list = []
    _lock = None
    _max_browsers = 3
    _initialized = False
    
    @classmethod
    async def _ensure_initialized(cls):
        """Initialize the pool on first use."""
        if cls._initialized:
            return
        
        import asyncio
        cls._lock = asyncio.Lock()
        cls._initialized = True
        logger.info("🔧 BrowserPool initialized")
    
    @classmethod
    async def acquire(cls):
        """
        Acquire a browser from the pool.
        Creates new browser if pool is empty and under limit.
        """
        if not PLAYWRIGHT_AVAILABLE:
            return None
            
        await cls._ensure_initialized()
        
        async with cls._lock:
            # Return existing browser if available
            if cls._browsers:
                browser = cls._browsers.pop()
                if browser.is_connected():
                    logger.debug("♻️ Reusing browser from pool")
                    return browser
                else:
                    logger.debug("⚠️ Discarding disconnected browser")
            
            # Create new browser
            if cls._playwright is None:
                from playwright.async_api import async_playwright
                cls._playwright = await async_playwright().start()
            
            browser = await cls._playwright.chromium.launch(headless=True)
            logger.debug("🚀 Created new browser instance")
            return browser
    
    @classmethod
    async def release(cls, browser):
        """Return a browser to the pool for reuse."""
        if browser is None:
            return
            
        await cls._ensure_initialized()
        
        async with cls._lock:
            if len(cls._browsers) < cls._max_browsers and browser.is_connected():
                # Close all contexts to reset state
                for context in browser.contexts:
                    await context.close()
                cls._browsers.append(browser)
                logger.debug(f"♻️ Browser returned to pool (size: {len(cls._browsers)})")
            else:
                # Pool full or browser invalid, close it
                try:
                    await browser.close()
                except Exception:
                    pass
    
    @classmethod
    async def warmup(cls, count: int = 2):
        """Pre-warm the pool with ready browsers."""
        if not PLAYWRIGHT_AVAILABLE:
            return
            
        await cls._ensure_initialized()
        
        for _ in range(count):
            if len(cls._browsers) < cls._max_browsers:
                browser = await cls.acquire()
                if browser:
                    await cls.release(browser)
        
        logger.info(f"🔥 BrowserPool warmed up with {len(cls._browsers)} browsers")
    
    @classmethod
    async def shutdown(cls):
        """Cleanup all browsers on application shutdown."""
        async with cls._lock:
            for browser in cls._browsers:
                try:
                    await browser.close()
                except Exception:
                    pass
            cls._browsers.clear()
            
            if cls._playwright:
                await cls._playwright.stop()
                cls._playwright = None
            
            logger.info("🛑 BrowserPool shutdown complete")


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

    def _load_logo_image(self, logo_url: str, context: str) -> Optional["Image.Image"]:
        if not logo_url or not PIL_AVAILABLE:
            return None

        import requests
        import importlib.util

        try:
            logo_response = requests.get(logo_url, timeout=15)
            logo_response.raise_for_status()
        except Exception as err:
            logger.warning(f"⚠️ Logo download failed for {context}: {err}")
            return None

        content_type = (logo_response.headers.get("Content-Type") or "").lower()
        is_svg = "image/svg" in content_type
        if content_type and not content_type.startswith("image/"):
            logger.warning(
                "⚠️ Invalid logo file for %s: expected image content type, got %s",
                context,
                content_type
            )
            return None

        logo_bytes = logo_response.content
        if is_svg:
            if importlib.util.find_spec("cairosvg") is None:
                logger.warning(
                    "⚠️ SVG logo provided for %s but cairosvg is unavailable for conversion.",
                    context
                )
                return None
            from cairosvg import svg2png
            try:
                logo_bytes = svg2png(bytestring=logo_bytes)
            except Exception as err:
                logger.warning(f"⚠️ Failed to convert SVG logo for {context}: {err}")
                return None

        logo_stream = io.BytesIO(logo_bytes)
        logo_stream.seek(0)

        try:
            logo_img = Image.open(logo_stream)
            logo_img.verify()
            logo_stream.seek(0)
            return Image.open(logo_stream).convert("RGBA")
        except Exception as err:
            logger.warning(f"⚠️ Invalid logo file for {context}: {err}")
            return None
    
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
    
    def analyze_luminance(self, image_bytes: bytes) -> str:
        """
        Analyze image brightness to determine text/logo contrast needs.
        
        V3.0 Intelligent Contrast Detection:
        - Converts image to greyscale
        - Calculates average pixel brightness (0-255)
        - Returns mode for optimal text visibility
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            'dark' if brightness < 128 (needs white text)
            'light' if brightness >= 128 (needs black text)
        """
        if not PIL_AVAILABLE:
            logger.warning("⚠️ PIL not available for luminance analysis")
            return 'dark'  # Default to dark (white text)
        
        try:
            # Open and convert to greyscale
            img = Image.open(io.BytesIO(image_bytes)).convert("L")
            
            # Resize for faster calculation
            img = img.resize((100, 100))
            
            # Calculate average brightness
            pixels = list(img.getdata())
            avg_brightness = sum(pixels) / len(pixels)
            
            mode = 'dark' if avg_brightness < 128 else 'light'
            logger.info(f"🔍 Luminance analysis: avg={avg_brightness:.1f}, mode={mode}")
            
            return mode
            
        except Exception as e:
            logger.warning(f"⚠️ Luminance analysis failed: {e}")
            return 'dark'  # Default to dark (white text)
    
    def analyze_luminance_from_url(self, image_url: str) -> str:
        """
        Analyze luminance from an image URL.
        Downloads the image and delegates to analyze_luminance.
        
        Args:
            image_url: URL of the image to analyze
            
        Returns:
            'dark' or 'light' mode string
        """
        try:
            import requests
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            return self.analyze_luminance(response.content)
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch image for luminance analysis: {e}")
            return 'dark'  # Default
    
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
    
    def apply_brand_layer(self, base_img: "Image.Image", brand_dna: Dict[str, Any]) -> "Image.Image":
        """
        Apply programmatic brand overlay (Logo + Color Tint).

        Uses low-opacity RGBA fills for brand color and pastes the logo
        in the top-right corner with a transparency mask.
        """
        if not PIL_AVAILABLE:
            logger.warning("⚠️ PIL not available for brand overlay")
            return base_img

        primary_color = (
            brand_dna.get("primary_color")
            or brand_dna.get("color_palette", {}).get("primary")
            or "#000000"
        )

        hex_color = primary_color.lstrip("#")
        rgb = (0, 0, 0)
        if len(hex_color) == 6:
            try:
                rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            except ValueError:
                rgb = (0, 0, 0)

        overlay = Image.new("RGBA", base_img.size, (*rgb, 30))
        base_img = Image.alpha_composite(base_img.convert("RGBA"), overlay)

        logo_url = brand_dna.get("logo_url")
        if logo_url:
            try:
                import requests
                logo_response = requests.get(logo_url, timeout=10)
                logo_response.raise_for_status()  # Explicit 404/403 detection
                logo_img = Image.open(io.BytesIO(logo_response.content)).convert("RGBA")

                target_logo_width = int(base_img.width * 0.15)
                aspect_ratio = logo_img.height / logo_img.width
                target_logo_height = int(target_logo_width * aspect_ratio)
                logo_img = logo_img.resize((target_logo_width, target_logo_height), Image.Resampling.LANCZOS)

                padding = int(base_img.width * 0.05)
                x_pos = base_img.width - target_logo_width - padding
                y_pos = padding

                base_img.paste(logo_img, (x_pos, y_pos), mask=logo_img)
            except Exception as e:
                logger.warning(f"⚠️ Logo overlay skipped (URL may be 404/403): {e}")

        return base_img

    def analyze_image_context(self, keywords: list) -> str:
        """
        V3.0 Smart Selection: Returns best template based on content keywords.
        """
        keywords_str = " ".join([k.lower() for k in keywords])
        
        if any(w in keywords_str for w in ["food", "craft", "travel", "art", "nature", "handmade"]):
            return "scrapbook"
        elif any(w in keywords_str for w in ["sale", "event", "youth", "concert", "promo", "deal"]):
            return "pop"
        elif any(w in keywords_str for w in ["finance", "law", "b2b", "corporate", "office", "business"]):
            return "swiss"
        
        return None  # No specific match

    def apply_advanced_branding(
        self,
        base_image_url: str,
        brand_dna: Dict[str, Any]
    ) -> str:
        """
        V3.0 Advanced Branding with multiple layout styles.
        Randomly selects a layout: Border, Split, or Watermark.
        
        Args:
            base_image_url: URL of the base image
            brand_dna: Brand DNA containing logo_url, color_palette, etc.
        
        Returns:
            URL of the branded image
        """
        if not PIL_AVAILABLE or not self.storage_client:
            logger.warning("⚠️ PIL or GCS not available for advanced branding")
            return base_image_url
        
        import random
        import requests
        import time
        
        try:
            # 1. Download Base Image (with timeout protection)
            response = requests.get(base_image_url, timeout=30)
            response.raise_for_status()
            base_img = Image.open(io.BytesIO(response.content)).convert("RGBA")
            
            # Extract brand data
            logo_url = brand_dna.get('logo_url')
            color_palette = brand_dna.get('color_palette', {})
            primary_color = color_palette.get('primary', '#000000')
            
            # Parse hex color
            hex_color = primary_color.lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
            else:
                r, g, b = 0, 0, 0
            
            # 2. Select Random Layout Style
            layout = random.choice(['border', 'split', 'watermark'])
            logger.info(f"🎨 Applying '{layout}' branding layout")
            
            if layout == 'border':
                # BORDER: Fixed 20px professional border in brand color
                border_width = 20
                new_width = base_img.width + (border_width * 2)
                new_height = base_img.height + (border_width * 2)
                
                bordered = Image.new("RGBA", (new_width, new_height), (r, g, b, 255))
                bordered.paste(base_img, (border_width, border_width))
                base_img = bordered
                logo_position = 'top_right'
                
            elif layout == 'split':
                # SPLIT: Gradient fade at bottom for text readability
                gradient = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
                
                # Create bottom gradient (last 40% of image height)
                for y in range(int(base_img.height * 0.6), base_img.height):
                    progress = (y - int(base_img.height * 0.6)) / (base_img.height * 0.4)
                    alpha = int(180 * progress)  # Max ~70% opacity
                    for x in range(base_img.width):
                        gradient.putpixel((x, y), (r, g, b, alpha))
                
                base_img = Image.alpha_composite(base_img, gradient)
                logo_position = 'bottom_center'
                
            else:  # watermark
                # WATERMARK: Repeated logo tiles at 5% opacity
                if logo_url:
                    logo_img = self._load_logo_image(logo_url, "watermark")
                    if logo_img:
                        try:
                            # Make logo very transparent (5% opacity)
                            logo_small = logo_img.resize(
                                (int(base_img.width * 0.10), int(base_img.width * 0.10 * logo_img.height / logo_img.width)),
                                Image.Resampling.LANCZOS
                            )
                            
                            # Reduce opacity to 5%
                            alpha = logo_small.split()[3]
                            alpha = alpha.point(lambda p: int(p * 0.05))
                            logo_small.putalpha(alpha)
                            
                            # Tile the logo
                            watermark_layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
                            tile_spacing_x = max(1, int(base_img.width * 0.20))
                            tile_spacing_y = max(1, int(base_img.height * 0.20))
                            
                            for y in range(0, base_img.height, tile_spacing_y):
                                for x in range(0, base_img.width, tile_spacing_x):
                                    watermark_layer.paste(logo_small, (x, y), mask=logo_small)
                            
                            base_img = Image.alpha_composite(base_img, watermark_layer)
                        except Exception as e:
                            logger.warning(f"⚠️ Watermark logo failed: {e}")
                
                logo_position = 'top_right'
            
            # 3. Apply Main Logo (based on layout)
            if logo_url and layout != 'watermark':  # Watermark already has logos
                logo_img = self._load_logo_image(logo_url, "logo placement")
                if logo_img:
                    try:
                        # Resize logo to 18% of image width
                        target_logo_width = int(base_img.width * 0.18)
                        aspect_ratio = logo_img.height / logo_img.width
                        target_logo_height = int(target_logo_width * aspect_ratio)
                        logo_img = logo_img.resize((target_logo_width, target_logo_height), Image.Resampling.LANCZOS)
                        
                        # Position based on layout
                        padding = int(base_img.width * 0.05)
                        
                        if logo_position == 'top_right':
                            x_pos = base_img.width - target_logo_width - padding
                            y_pos = padding
                        else:  # bottom_center
                            x_pos = (base_img.width - target_logo_width) // 2
                            y_pos = base_img.height - target_logo_height - padding
                        
                        # Composite logo
                        logo_layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
                        logo_layer.paste(logo_img, (x_pos, y_pos), mask=logo_img)
                        base_img = Image.alpha_composite(base_img, logo_layer)
                    except Exception as e:
                        logger.warning(f"⚠️ Logo placement failed: {e}")
            
            # 4. Save and Upload
            output = io.BytesIO()
            base_img = base_img.convert("RGB")
            base_img.save(output, format="JPEG", quality=92)
            processed_bytes = output.getvalue()
            
            filename = f"advanced_branded_{layout}_{int(time.time())}.jpg"
            destination_path = f"assets/branded/{filename}"
            
            return self.upload_to_gcs(processed_bytes, destination_path, "image/jpeg") or base_image_url
            
        except Exception as e:
            logger.error(f"❌ Advanced branding failed: {e}")
            return base_image_url
    
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
        output_format: str = "png",
        animation_delay: float = 3.0,
        timeout: int = 30000
    ) -> bytes:
        """
        Render HTML creative to raster image.
        Used for HTML5 ad banners, landing page previews, and animated GSAP templates.
        
        V4.1 Animation Rendering Fix:
        - Added animation_delay for GSAP animation stabilization
        - Added configurable timeout (use 60000 for vertical 9:16 formats)
        - Checks for .animation-complete class if present
        
        Args:
            html_content: Complete HTML document or snippet
            width: Viewport width
            height: Viewport height
            output_format: 'png' or 'jpeg'
            animation_delay: Seconds to wait for animations to stabilize (default 3.0)
            timeout: Page load timeout in milliseconds (default 30000, use 60000 for heavy animations)
            
        Returns:
            Screenshot bytes
        """
        import asyncio
        
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
                
                # V4.1: Use configurable timeout for set_content
                await page.set_content(html_content, wait_until="networkidle", timeout=timeout)
                
                # V4.1 FIX: Wait for GSAP animations to stabilize
                # First, try to wait for .animation-complete class (if template adds it)
                try:
                    await page.wait_for_selector(".animation-complete", timeout=2000)
                    logger.debug("✓ Animation complete class detected")
                except Exception:
                    logger.debug("No .animation-complete class detected")
                    # Class not present - use fixed animation delay as fallback
                    pass
                
                # Always apply animation delay for GSAP stabilization
                await asyncio.sleep(animation_delay)
                logger.debug(f"⏱️ Animation delay complete ({animation_delay}s)")
                
                screenshot = await page.screenshot(
                    type=output_format,
                    full_page=False,
                    omit_background=output_format == "png"
                )
                
                await browser.close()
                logger.info(f"✅ Rendered HTML to {output_format.upper()} ({width}x{height}) [delay={animation_delay}s]")
                return screenshot
                

        except Exception as e:
            logger.error(f"❌ HTML render failed: {e}")
            return b""

    async def generate_image_asset(
        self,
        html_content: str,
        user_id: str,
        asset_id: str,
        width: int = 1080,
        height: int = 1920,
        output_format: str = "png"
    ) -> Optional[str]:
        """
        V6.0 Browser Pool Optimized: Generate static image from HTML with GSAP snap-to-finish.
        
        Uses BrowserPool for faster browser acquisition (eliminates ~1-2s cold-start).
        Uses gsap.globalTimeline.progress(1).pause() to instantly snap the animation
        to its final frame, then captures a screenshot.
        
        Args:
            html_content: HTML string with GSAP animations
            user_id: User ID for storage path
            asset_id: Asset ID for filename
            width: Image width
            height: Image height
            output_format: 'png' or 'jpeg'
            
        Returns:
            Public URL of the uploaded image or None if failed.
        """
        import asyncio
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("⚠️ Playwright not available for image generation")
            return None
        
        browser = None
        context = None
        try:
            # V6.0: Use BrowserPool for faster acquisition
            browser = await BrowserPool.acquire()
            if browser is None:
                logger.warning("⚠️ Could not acquire browser from pool")
                return None
            
            # Create a new context for isolation
            context = await browser.new_context(viewport={"width": width, "height": height})
            page = await context.new_page()
            
            # Normalize HTML
            if not html_content.strip().lower().startswith("<!doctype") and not html_content.strip().lower().startswith("<html"):
                html_content = f"<!DOCTYPE html><html><body>{html_content}</body></html>"
            
            # Load content
            await page.set_content(html_content, wait_until="networkidle", timeout=60000)
            
            # V5.0 SNAP-TO-FINISH: Skip animation to final frame instantly
            try:
                await page.evaluate("""
                    if (typeof gsap !== 'undefined' && gsap.globalTimeline) {
                        gsap.globalTimeline.progress(1).pause();
                    }
                """)
                logger.debug("⚡ GSAP snapped to final frame")
            except Exception:
                pass
            
            # Brief wait for render stabilization
            await asyncio.sleep(0.3)  # Reduced from 0.5s with warmed browser
            
            # Capture screenshot
            screenshot = await page.screenshot(
                type=output_format,
                full_page=False,
                omit_background=output_format == "png"
            )
            
            # Clean up context
            await context.close()
            context = None
            
            # Upload to GCS
            target_path = f"assets/{user_id}/{asset_id}/static.{output_format}"
            uploaded_url = self.upload_to_gcs(
                screenshot,
                target_path,
                content_type=f"image/{output_format}"
            )
            
            logger.info(f"📸 Image asset generated & uploaded: {uploaded_url}")
            return uploaded_url
            
        except Exception as e:
            logger.error(f"❌ Image asset generation failed: {e}")
            return None
        finally:
            # Clean up context if still open
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            # Return browser to pool
            if browser:
                await BrowserPool.release(browser)


    async def generate_video_asset(
        self,
        html_content: str,
        user_id: str,
        asset_id: str,
        width: int = 1080,
        height: int = 1920,
        duration: float = 6.0,
        fallback_to_image: bool = True
    ) -> Optional[str]:
        """
        V5.0 Smart Format Selection: Generate video asset with automatic fallback.
        
        Attempts to record HTML animation as video. If recording fails (e.g., browser crash,
        timeout, Playwright error), automatically falls back to static image capture
        so the user at least gets something.
        
        Args:
            html_content: HTML string with GSAP animations
            user_id: User ID for storage path
            asset_id: Asset ID for filename
            width: Video width
            height: Video height
            duration: Animation duration in seconds
            fallback_to_image: If True, capture static image on video failure
            
        Returns:
            Public URL of the video (or fallback image) or None if both fail.
        """
        try:
            # Attempt video recording
            video_url = await self.record_html_animation(
                html_content=html_content,
                user_id=user_id,
                asset_id=asset_id,
                width=width,
                height=height,
                duration=duration
            )
            
            if video_url:
                return video_url
            else:
                raise Exception("Video recording returned None")
                
        except Exception as e:
            logger.warning(f"⚠️ Video recording failed for {asset_id}: {e}")
            
            if fallback_to_image:
                logger.info(f"🔄 Falling back to static image for {asset_id}")
                try:
                    image_url = await self.generate_image_asset(
                        html_content=html_content,
                        user_id=user_id,
                        asset_id=f"{asset_id}_fallback",
                        width=width,
                        height=height
                    )
                    if image_url:
                        logger.info(f"✅ Fallback image generated: {image_url}")
                        return image_url
                except Exception as fallback_err:
                    logger.error(f"❌ Fallback image also failed: {fallback_err}")
            
            return None

    async def record_html_animation(
        self,
        html_content: str,
        user_id: str,
        asset_id: str,
        width: int = 1080,
        height: int = 1920,
        duration: float = 6.0,
        fps: int = 30
    ) -> Optional[str]:
        """
        Record HTML/GSAP animation to MP4 video.
        
        Args:
            html_content: HTML string with animations
            user_id: User ID for storage
            asset_id: Asset ID for filename
            width: Video width (default 1080 for vertical)
            height: Video height (default 1920 for vertical)
            duration: Animation duration in seconds (real time)
            fps: Frames per second
            
        Returns:
            Public URL of the uploaded video or None if failed.
        """
        import asyncio
        import os
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("⚠️ Playwright not available for video recording")
            return None
            
        video_path = None
        
        try:
            # Create local temp directory for video
            base_temp_dir = tempfile.gettempdir()
            temp_dir = os.path.join(base_temp_dir, "videos", asset_id)
            os.makedirs(temp_dir, exist_ok=True)
            
            async with async_playwright() as p:
                # Launch browser (headless)
                browser = await p.chromium.launch(headless=True)
                
                # Create context with video recording enabled
                context = await browser.new_context(
                    viewport={"width": width, "height": height},
                    record_video_dir=temp_dir,
                    record_video_size={"width": width, "height": height}
                )
                
                page = await context.new_page()
                
                # Normalize HTML
                if not html_content.strip().lower().startswith("<!doctype") and not html_content.strip().lower().startswith("<html"):
                    html_content = f"<!DOCTYPE html><html><body>{html_content}</body></html>"
                
                # Load content
                await page.set_content(html_content, wait_until="networkidle", timeout=60000)
                
                # SMART OPTIMIZATION: Speed up GSAP to 2x (if GSAP exists)
                # This cuts recording time in half effectively
                try:
                    await page.evaluate("if (typeof gsap !== 'undefined') { gsap.globalTimeline.timeScale(2); }")
                    logger.debug("⚡ accelerated GSAP timeline by 2x")
                except Exception:
                    pass
                
                # WAIT LOGIC FIX (V5.1):
                # If we speed up GSAP by 2x, the animation finishes in duration/2.
                # However, Playwright creates a video file that plays at normal speed.
                # If we record for 3s (real time) while GSAP is 2x, we capture the hole animation.
                # The output video will be 3s long and look "fast". this is desired for social.
                
                recording_time = duration / 2.0
                await asyncio.sleep(recording_time + 1.0) # Buffer to ensure capture
                
                # Close context to save video
                await context.close()
                await browser.close()
                
                # Find the video file
                video_files = [f for f in os.listdir(temp_dir) if f.endswith(".webm")]
                if not video_files:
                    logger.error("❌ No video file generated")
                    return None
                    
                local_video_path = os.path.join(temp_dir, video_files[0]) # This is .webm
                
                # V5.1 FIX: Verify if FFmpeg is available for conversion
                ffmpeg_available = shutil.which("ffmpeg") is not None
                final_video_path = local_video_path
                content_type = "video/webm"
                
                if ffmpeg_available:
                    try:
                        # Convert to MP4
                        mp4_path = os.path.join(temp_dir, "output.mp4")
                        command = [
                            "ffmpeg", "-y",
                            "-i", local_video_path,
                            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                            "-c:a", "aac", "-b:a", "128k",
                            mp4_path
                        ]
                        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        final_video_path = mp4_path
                        content_type = "video/mp4"
                        logger.info("✅ Converted WebM to MP4")
                    except Exception as conv_err:
                        logger.warning(f"⚠️ FFmpeg conversion failed, falling back to WebM: {conv_err}")
                else:
                    logger.warning("⚠️ FFmpeg not found, uploading as WebM (may affect platform compatibility)")

                # Upload to GCS
                with open(final_video_path, "rb") as f:
                    video_bytes = f.read()
                
                # Determine extension
                ext = "mp4" if content_type == "video/mp4" else "webm"
                target_path = f"assets/{user_id}/{asset_id}/video.{ext}"
                
                uploaded_url = self.upload_to_gcs(
                    video_bytes,
                    target_path,
                    content_type=content_type
                )
                
                # Cleanup
                try:
                    # Remove all files in temp dir
                    for f in os.listdir(temp_dir):
                        os.remove(os.path.join(temp_dir, f))
                    os.rmdir(temp_dir)
                except:
                    pass
                    
                logger.info(f"🎥 Video recorded & uploaded: {uploaded_url}")
                return uploaded_url

        except Exception as e:
            logger.error(f"❌ Video recording failed: {e}")
            return None
    
    async def generate_veo_video_asset(
        self,
        prompt: Union[str, Dict, List], 
        text_content: str,
        logo_url: str,
        user_id: str,
        asset_id: str,
        channel: str = "instagram",
        brand_dna: dict = None,
        width: int = 1080,
        height: int = 1920
    ) -> Optional[str]:
        """
        V7.0 Hybrid Video Pipeline: Veo AI background + HTML text overlay.
        
        Combines:
        1. Veo video generation (using raw bytes & manual polling)
        2. HTML/GSAP text overlay (perfect font rendering)
        3. Playwright recording (composite final video)
        
        Args:
            prompt: Description of the video background to generate (str, dict, or list)
            text_content: Headline/copy text to overlay
            logo_url: URL of the brand logo
            user_id: User ID for storage path
            asset_id: Asset ID for filename
            channel: Target channel (affects layout and aspect ratio)
            brand_dna: Brand DNA with colors, fonts, etc.
            width: Output width in pixels
            height: Output height in pixels
            
        Returns:
            URL of the final composite video or None if failed.
        """
        logger.info(f"🎬 Starting Veo hybrid video for channel: {channel}")
        
        # Imports for strict Veo protocol
        import vertexai
        from vertexai.preview.vision_models import ImageGenerationModel
        import time
        
        # ----------------------------------------------------------------
        # V7.2 FIX: AGGRESSIVE PROMPT SANITIZATION
        # ----------------------------------------------------------------
        clean_prompt = ""
        try:
            if isinstance(prompt, dict):
                clean_prompt = prompt.get('visual_prompt') or prompt.get('description') or prompt.get('prompt') or str(prompt)
            elif isinstance(prompt, list):
                clean_prompt = " ".join([str(p) for p in prompt])
            else:
                clean_prompt = str(prompt)
            
            if not isinstance(clean_prompt, str):
                clean_prompt = str(clean_prompt)
            
            logger.info(f"Veo Prompt Sanitized: {clean_prompt[:50]}...")
        except Exception as e:
            logger.error(f"Error sanitizing prompt: {e}")
            return None
        
        # ----------------------------------------------------------------
        # 1. Generate Veo Video (Strict Raw Bytes Protocol)
        # ----------------------------------------------------------------
        video_url = None
        try:
            # [REQUIREMENT] Use Integer GENAI_PROJECT_ID
            project_id_int = int(os.getenv("GENAI_PROJECT_ID")) 
            vertexai.init(project=project_id_int, location="us-central1")

            veo_model_name = os.getenv("VEO_VIDEO_MODEL_NAME", "veo-3.1-generate-001")
            model = ImageGenerationModel.from_pretrained(veo_model_name)

            # Generate video (returns an Operation)
            operation = model.generate_video(
                prompt=clean_prompt,
                number_of_videos=1,
                aspect_ratio=f"{width}x{height}" if width and height else "9:16",
                add_watermark=False
            )

            # [REQUIREMENT] Manual Polling Loop
            logger.info("Polling Veo operation...")
            while not operation.done():
                time.sleep(10)

            result = operation.result()
            
            # [REQUIREMENT] Handle Raw Bytes
            video_bytes = None
            if result.videos and result.videos[0].video_bytes:
                video_bytes = result.videos[0].video_bytes
            else:
                raise ValueError("Veo generation finished but no video_bytes were returned.")

            # Upload raw bytes to GCS
            timestamp = int(time.time())
            filename = f"veo_raw_{asset_id}_{timestamp}.mp4"
            destination_blob_name = f"assets/{user_id}/{asset_id}/{filename}"
            
            video_url = self.upload_to_gcs(video_bytes, destination_blob_name, "video/mp4")
            
            if not video_url:
                raise ValueError("Failed to upload raw Veo bytes to GCS")
                
            logger.info(f"✅ Veo video generated & uploaded: {video_url}")

        except Exception as e:
            logger.error(f"❌ Veo generation failed: {e}")
            # [REQUIREMENT] STRICTLY NO FALLBACK. Return None.
            return None
            
        # ----------------------------------------------------------------
        # 2. Build Hybrid Overlay
        # ----------------------------------------------------------------
        try:
            from app.core.templates import get_layout_for_channel
            
            # Analyze luminance (placeholder or future implementation)
            luminance_mode = "dark" 
            
            # Get channel layout
            layout_class = get_layout_for_channel(channel)
            
            # Build HTML
            brand_color = brand_dna.get("color_palette", {}).get("primary", "#ffffff") if brand_dna else "#ffffff"
            
            html_content = self._build_video_overlay_template(
                video_url=video_url,
                text=text_content,
                logo_url=logo_url,
                layout_class=layout_class,
                luminance_mode=luminance_mode,
                brand_color=brand_color,
                width=width,
                height=height
            )
            
            # ----------------------------------------------------------------
            # 3. Record Composite Video
            # ----------------------------------------------------------------
            final_url = await self.record_html_animation(
                html_content=html_content,
                user_id=user_id,
                asset_id=asset_id,
                width=width,
                height=height,
                duration=4.0  # Default Veo preview duration
            )
            
            logger.info(f"🎥 Hybrid video complete: {final_url}")
            return final_url
            
        except Exception as e:
            logger.error(f"❌ Hybrid composition failed: {e}")
            return None
    
    def _build_video_overlay_template(
        self,
        video_url: str,
        text: str,
        logo_url: str,
        layout_class: str,
        luminance_mode: str = "dark",
        brand_color: str = "#ffffff",
        width: int = 1080,
        height: int = 1920
    ) -> str:
        """
        Build HTML template with video background and text overlay.
        """
        # Text color based on luminance
        text_color = "#ffffff" if luminance_mode == "dark" else "#000000"
        shadow_color = "rgba(0,0,0,0.8)" if luminance_mode == "dark" else "rgba(255,255,255,0.8)"
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    width: {width}px; 
                    height: {height}px; 
                    font-family: 'Inter', sans-serif;
                    overflow: hidden;
                }}
                
                .video-bg {{
                    position: absolute;
                    top: 0; left: 0;
                    width: 100%; height: 100%;
                    object-fit: cover;
                    z-index: 1;
                }}
                
                .overlay {{
                    position: absolute;
                    top: 0; left: 0;
                    width: 100%; height: 100%;
                    z-index: 10;
                    display: flex;
                    flex-direction: column;
                    padding: 60px;
                }}
                
                .{layout_class} {{
                    /* Layout applied via class */
                }}
                
                .text-container {{
                    max-width: 90%;
                }}
                
                .headline {{
                    font-size: 4rem;
                    font-weight: 800;
                    color: {text_color};
                    text-shadow: 0 0 30px {shadow_color}, 0 0 60px {shadow_color};
                    line-height: 1.1;
                    opacity: 0;
                }}
                
                .logo {{
                    width: 120px;
                    height: auto;
                    opacity: 0;
                    filter: drop-shadow(0 0 20px {shadow_color});
                }}
                
                .accent-bar {{
                    width: 100px;
                    height: 6px;
                    background: {brand_color};
                    margin: 20px 0;
                    opacity: 0;
                }}
            </style>
        </head>
        <body>
            <video class="video-bg" autoplay muted loop playsinline>
                <source src="{video_url}" type="video/mp4">
            </video>
            
            <div class="overlay {layout_class}">
                <div class="text-container">
                    <img src="{logo_url}" class="logo" id="logo">
                    <div class="accent-bar" id="accent"></div>
                    <h1 class="headline" id="text">{text}</h1>
                </div>
            </div>
            
            <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
            <script>
                gsap.timeline()
                    .to("#logo", {{opacity: 1, y: 0, duration: 0.6, ease: "power2.out"}})
                    .to("#accent", {{opacity: 1, width: 150, duration: 0.4}}, "-=0.3")
                    .to("#text", {{opacity: 1, y: 0, duration: 0.8, ease: "power2.out"}}, "-=0.2");
            </script>
        </body>
        </html>
        '''

_asset_processor: Optional[AssetProcessor] = None


def get_asset_processor() -> AssetProcessor:
    """Get or create singleton AssetProcessor."""
    global _asset_processor
    if _asset_processor is None:
        _asset_processor = AssetProcessor()
    return _asset_processor
