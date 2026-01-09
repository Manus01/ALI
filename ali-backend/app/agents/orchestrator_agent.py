import asyncio
import logging
import base64
import json
from app.agents.base_agent import BaseAgent
from app.agents.campaign_agent import CampaignAgent
from app.services.image_agent import ImageAgent
from app.core.security import db
from firebase_admin import firestore

logger = logging.getLogger("ali_platform.agents.orchestrator_agent")

# ============================================================================
# 2025/2026 MASTER CHANNEL SPECIFICATIONS
# Enforces dimension-accurate, platform-compliant asset generation
# ============================================================================
CHANNEL_SPECS = {
    "linkedin": {
        "formats": [
            {"type": "feed", "size": (1200, 627), "ratio": "1.91:1", "tone": "professional"},
            {"type": "square", "size": (1080, 1080), "ratio": "1:1", "tone": "professional"},
            {"type": "carousel", "size": (1080, 1080), "ratio": "1:1", "tone": "professional_educational"}
        ],
        "text_limit": 3000,
        "tone": "professional",
        "carousel_support": True
    },
    "instagram": {
        "formats": [
            {"type": "story", "size": (1080, 1920), "ratio": "9:16", "safe_zone_bottom": 250},
            {"type": "feed_portrait", "size": (1080, 1350), "ratio": "4:5"}
        ],
        "tone": "visual_heavy_hashtags",
        "motion_support": True,
        "carousel_support": True
    },
    "facebook": {
        "formats": [
            {"type": "feed", "size": (1080, 1080), "ratio": "1:1"},
            {"type": "link", "size": (1200, 628), "ratio": "1.91:1"}
        ],
        "tone": "conversational"
    },
    "tiktok": {
        "formats": [
            {"type": "feed_video_placeholder", "size": (1080, 1920), "ratio": "9:16", "safe_zone_bottom": 420, "safe_zone_right": 120}
        ],
        "tone": "trendy_short",
        "motion_support": True
    },
    "google_display": {
        "formats": [
            {"type": "medium_rect", "size": (300, 250)},
            {"type": "leaderboard", "size": (728, 90)},
            {"type": "mobile_leaderboard", "size": (320, 50)}
        ],
        "tone": "direct_response"
    },
    "pinterest": {
        "formats": [
            {"type": "pin", "size": (1000, 1500), "ratio": "2:3"}
        ],
        "tone": "aspirational_visual"
    },
    "threads": {
        "formats": [
            {"type": "feed", "size": (1080, 1080), "ratio": "1:1"}
        ],
        "tone": "minimal_conversational"
    },
    "email": {
        "formats": [{"type": "header", "size": (600, 200)}],
        "tone": "persuasive"
    },
    "blog": {
        "formats": [{"type": "hero", "size": (1200, 630)}],
        "tone": "informative"
    }
}

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Orchestrator")
        self.db = db

    async def run_full_campaign_flow(self, uid, campaign_id, goal, brand_dna, answers, selected_channels: list = None):
        """
        Channel-Aware Campaign Orchestrator v3.0
        Generates dimension-accurate, platform-compliant assets for each selected channel.
        """
        try:
            # 1. Update Notification: Start
            self._update_progress(uid, campaign_id, "Analyzing Cultural Context...", 10)

            # Resolve channels - use selected_channels if provided, fallback to connected_platforms detection
            target_channels = selected_channels if selected_channels else ["instagram", "linkedin"]
            # Normalize channel names (lowercase, underscores)
            target_channels = [c.lower().replace(" ", "_").replace("-", "_") for c in target_channels]
            logger.info(f"🎯 Channel-Aware Orchestration for: {target_channels}")

            # 2. Generate Blueprint with channel context
            planner = CampaignAgent()
            blueprint = await planner.create_campaign_blueprint(goal, brand_dna, answers, selected_channels=target_channels)
            self._update_progress(uid, campaign_id, "Creative Blueprint Ready.", 30)

            # 3. Channel-Aware Asset Generation Loop
            image_agent = ImageAgent()
            
            tasks = []
            task_metadata = []  # Track (channel, format_type, specs) for each task
            
            for channel in target_channels:
                spec = CHANNEL_SPECS.get(channel)
                if not spec:
                    logger.warning(f"⚠️ Unknown channel '{channel}', skipping...")
                    continue
                
                # Use first format as primary for this channel
                primary_format = spec["formats"][0]
                width, height = primary_format["size"]
                tone = spec.get("tone", primary_format.get("tone", "professional"))
                
                # Build safe zone instruction for vertical formats
                safe_zone_instruction = ""
                if primary_format.get("safe_zone_bottom"):
                    safe_zone_instruction = f" CRITICAL: Leave bottom {primary_format['safe_zone_bottom']}px clear of text/logos (UI overlay zone)."
                if primary_format.get("safe_zone_right"):
                    safe_zone_instruction += f" Leave right {primary_format['safe_zone_right']}px clear."
                
                # Get channel-specific visual prompt from blueprint, fallback to instagram
                channel_data = blueprint.get(channel, blueprint.get('instagram', {}))
                visual_prompt = channel_data.get('visual_prompt', 'Professional brand promotional image')
                
                # Enhance prompt with dimension awareness and safe zones
                enhanced_prompt = (
                    f"{visual_prompt}. "
                    f"DIMENSIONS: {width}x{height}px ({primary_format.get('ratio', 'custom')}). "
                    f"TONE: {tone}.{safe_zone_instruction}"
                )
                
                dna_str = f"Style {brand_dna.get('visual_styles', [])}. Colors {brand_dna.get('color_palette', {})}"
                
                # ---------------------------------------------------------
                # NEW: Carousel & Motion Logic
                # ---------------------------------------------------------
                is_carousel = primary_format.get("type") == "carousel"
                motion_supported = spec.get("motion_support", False)
                
                if is_carousel:
                    # Carousel: Generate 3 sequential images
                    # We create a sub-loop of tasks
                    for i in range(1, 4):
                        slide_prompt = f"{enhanced_prompt}. Slide {i} of 3. Ensure visual continuity."
                        task = asyncio.to_thread(
                            image_agent.generate_image, 
                            slide_prompt, 
                            brand_dna=dna_str, 
                            folder=f"campaigns/{channel}/slide_{i}"
                        )
                        tasks.append(task)
                        task_metadata.append({
                            "channel": channel,
                            "format_type": "carousel",  # Mark as carousel
                            "slide_index": i,
                            "size": primary_format["size"],
                            "tone": tone
                        })

                else:
                    # Standard Single Image (may be upgraded to Motion later)
                    task = asyncio.to_thread(
                        image_agent.generate_image, 
                        enhanced_prompt, 
                        brand_dna=dna_str, 
                        folder=f"campaigns/{channel}"
                    )
                    tasks.append(task)
                    task_metadata.append({
                        "channel": channel,
                        "format_type": "motion" if motion_supported else primary_format["type"],
                        "motion_enabled": motion_supported,
                        "size": primary_format["size"],
                        "tone": tone
                    })
            
            self._update_progress(uid, campaign_id, f"Generating {len(tasks)} Channel Assets...", 60)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Map results back to structured assets
            from app.services.asset_processor import get_asset_processor
            asset_processor = get_asset_processor()
            
            assets = {}
            temp_carousel_storage = {} # Store slides: {channel: {index: url}}
            assets_metadata = {}

            for i, result in enumerate(results):
                meta = task_metadata[i]
                channel = meta["channel"]
                
                if isinstance(result, Exception):
                    logger.error(f"❌ Failed to generate asset for {channel}: {result}")
                    continue
                    
                # Extract URL if dict (new format), else use result (legacy string)
                raw_url = result.get('url') if isinstance(result, dict) else result
                
                # FIX 1: Apply Programmatic Brand Overlay
                # Enforce branding on all channels except text-heavy ones
                if channel not in ['blog', 'email']:
                    try:
                        # Get brand details
                        logo_url = brand_dna.get('logo_url')
                        primary_color = brand_dna.get('color_palette', {}).get('primary', '#000000')
                        
                        # Apply overlay (skip for motion base images if we are wrapping them later, but good for fallback)
                        final_url = await asyncio.to_thread(
                            asset_processor.apply_brand_layer,
                            raw_url,
                            logo_url,
                            primary_color
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Brand overlay skipped for {channel}: {e}")
                        final_url = raw_url
                else:
                    final_url = raw_url

                # HANDLE CAROUSEL
                if meta.get("format_type") == "carousel":
                    if channel not in temp_carousel_storage:
                        temp_carousel_storage[channel] = {}
                    temp_carousel_storage[channel][meta["slide_index"]] = final_url
                    # We don't set assets[channel] yet, we wait until loop end
                    
                # HANDLE MOTION
                elif meta.get("motion_enabled"):
                    # Generate HTML asset using the final_url as background
                    channel_blueprint = blueprint.get(channel, {})
                    copy_text = channel_blueprint.get("headlines", ["Brand Motion"])[0] 
                    
                    html_asset = self._generate_html_motion_asset(final_url, logo_url, primary_color, copy_text)
                    assets[channel] = html_asset
                    
                # STANDARD IMAGE
                else:
                    assets[channel] = final_url
                
                # Save metadata (overwrite is fine for carousel as base props are same)
                assets_metadata[channel] = meta

            # Finalize Carousels: Convert dict to sorted list
            for channel, slides in temp_carousel_storage.items():
                sorted_slides = [slides[k] for k in sorted(slides.keys())]
                assets[channel] = sorted_slides
            
            # 4. Finalize & Package
            final_data = {
                "status": "completed",
                "blueprint": blueprint,
                "assets": assets,
                "assets_metadata": assets_metadata,
                "selected_channels": target_channels,
                "goal": goal,
                "campaign_id": campaign_id
            }
            
            # Use set with merge=True to handle new campaign documents correctly
            self.db.collection('users').document(uid).collection('campaigns').document(campaign_id).set(final_data, merge=True)
            
            # 5. Save drafts per channel for User Self-Approval (Review Feed)
            for channel in target_channels:
                # FIX: Ensure every channel gets a draft doc, even if generation failed
                # Standardize ID: strictly lowercase, no spaces (matches frontend)
                clean_channel = channel.lower().replace(" ", "_")
                draft_id = f"draft_{campaign_id}_{clean_channel}"
                
                asset_payload = assets.get(channel)
                meta = assets_metadata.get(channel, {})
                channel_blueprint = blueprint.get(channel, blueprint.get('instagram', {}))

                # Determine Status & URLs
                if asset_payload:
                    status = "DRAFT"
                    # Determine Thumbnail
                    thumbnail_url = asset_payload 
                    if isinstance(asset_payload, list):
                        thumbnail_url = asset_payload[0]
                    elif isinstance(asset_payload, str) and asset_payload.startswith("data:text/html"):
                        thumbnail_url = asset_payload # FE will render iframe
                else:
                    # Handle Failed Generation
                    status = "FAILED"
                    thumbnail_url = "https://placehold.co/600x400?text=Generation+Failed"
                    asset_payload = None # Explicit null

                # WRAP IN TRY/EXCEPT FOR ROBUSTNESS
                try:
                    draft_data = {
                        "userId": uid,
                        "campaignId": campaign_id,
                        "channel": clean_channel,
                        "thumbnailUrl": thumbnail_url,
                        "assetPayload": asset_payload,
                        "title": f"{goal[:50]}..." if len(goal) > 50 else goal,
                        "format": meta.get("format_type", "Image"),
                        "size": f"{meta.get('size', (0,0))[0]}x{meta.get('size', (0,0))[1]}" if meta.get('size') else "N/A",
                        "tone": meta.get("tone", "professional"),
                        "status": status,
                        "approvalStatus": "pending",
                        "createdAt": firestore.SERVER_TIMESTAMP,
                        "blueprint": channel_blueprint,
                        "textCopy": channel_blueprint.get("caption") or channel_blueprint.get("body") or (channel_blueprint.get("headlines", [""])[0] if channel_blueprint.get("headlines") else "")
                    }
                    
                    self.db.collection('creative_drafts').document(draft_id).set(draft_data)
                    logger.info(f"📦 Saved draft {draft_id} [{status}] for user {uid} (channel: {clean_channel})")
                except Exception as save_err:
                    logger.error(f"❌ Failed to save draft {draft_id}: {save_err}")
                    # Continue loop to ensure other drafts are saved
            
            self._update_progress(uid, campaign_id, "Campaign Ready!", 100)

        except Exception as e:
            self.handle_error(e)
            self._update_progress(uid, campaign_id, "Error in generation.", 0, failed=True)

    def _update_progress(self, uid, campaign_id, message, percent, failed=False):
        # This matches the 'Notifications' system used in your Tutorials page
        notif_ref = self.db.collection('users').document(uid).collection('notifications').document(campaign_id)
        notif_ref.set({
            "message": message,
            "progress": percent,
            "type": "campaign_progress",
            "campaign_id": campaign_id,
            "status": "error" if failed else ("completed" if percent == 100 else "processing"),
            "timestamp": firestore.SERVER_TIMESTAMP
        })

    def _generate_html_motion_asset(self, image_url, logo_url, color, text):
        """
        Generates a lightweight HTML5 motion asset encoded as a Data URI.
        """
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }}
                #bg {{
                    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                    background-image: url('{image_url}');
                    background-size: cover;
                    background-position: center;
                }}
                #logo {{
                    position: absolute; top: 20px; right: 20px; width: 80px; z-index: 100;
                }}
                #text {{
                    position: absolute; bottom: 40px; left: 20px; right: 20px;
                    color: white; font-family: sans-serif; font-size: 24px; font-weight: bold;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.7);
                }}
            </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
        </head>
        <body>
            <div id="bg"></div>
            <img id="logo" src="{logo_url}">
            <div id="text">{text}</div>
            <script>
                gsap.from("#text", {{x: -100, opacity: 0, duration: 1}});
                gsap.to("#bg", {{scale: 1.1, duration: 5}});
            </script>
        </body>
        </html>
        """
        encoded = base64.b64encode(html_template.encode('utf-8')).decode('utf-8')
        return f"data:text/html;charset=utf-8;base64,{encoded}"

    def _generate_carousel_slides(self, image_url, logo_url, color, text):
        """
        Simulates a carousel by returning a list of the image repeated.
        """
        return [image_url, image_url, image_url]