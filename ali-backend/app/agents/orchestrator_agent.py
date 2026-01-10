import asyncio
import logging
import base64
import json
import random
from app.agents.base_agent import BaseAgent
from app.agents.campaign_agent import CampaignAgent
from app.services.image_agent import ImageAgent
from app.core.security import db
from app.core.templates import get_motion_template, get_template_for_tone, get_random_template, MOTION_TEMPLATES, FONT_MAP
from firebase_admin import firestore

logger = logging.getLogger("ali_platform.agents.orchestrator_agent")

# V4.0 Configuration
IMAGE_GENERATION_TIMEOUT = 120  # Seconds per image

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
                
                # V3.0: Generate BOTH Story (9:16) AND Feed (1:1) for social channels
                formats_to_generate = []
                if channel in ['instagram', 'facebook', 'tiktok']:
                    # Find story format (9:16)
                    story_format = next((f for f in spec["formats"] if f.get("ratio") == "9:16"), None)
                    # Find feed format (1:1 or similar)
                    feed_format = next((f for f in spec["formats"] if f.get("ratio") in ["1:1", "4:5"]), None)
                    
                    if story_format:
                        formats_to_generate.append((story_format, 'story'))
                    if feed_format:
                        formats_to_generate.append((feed_format, 'feed'))
                    
                    # Fallback if no formats found
                    if not formats_to_generate:
                        formats_to_generate.append((spec["formats"][0], 'primary'))
                else:
                    formats_to_generate.append((spec["formats"][0], 'primary'))
                
                # Generate assets for each format
                for primary_format, format_label in formats_to_generate:
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
                            "format_label": format_label,
                            "motion_enabled": motion_supported,
                            "size": primary_format["size"],
                            "tone": tone
                        })
            
            self._update_progress(uid, campaign_id, f"Generating {len(tasks)} Channel Assets...", 40)
            
            # Execute all tasks concurrently with Semaphore (V4.0 Stability Fix)
            # Limit concurrent image generations to Avoid Quota Errors (Vertex AI limit ~60/min but burst limited)
            semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests

            async def semaphore_task(t, task_meta):
                """V4.0: Enhanced task wrapper with timeout and error isolation."""
                async with semaphore:
                    try:
                        result = await asyncio.wait_for(t, timeout=IMAGE_GENERATION_TIMEOUT)
                        return result
                    except asyncio.TimeoutError:
                        logger.error(f"⏰ Timeout generating asset for {task_meta.get('channel')}")
                        return {"error": "timeout", "channel": task_meta.get("channel")}
                    except Exception as e:
                        logger.error(f"❌ Generate task failed for {task_meta.get('channel')}: {e}")
                        return {"error": str(e), "channel": task_meta.get("channel")}

            # Wrap tasks with metadata for error context
            safe_tasks = [semaphore_task(t, task_metadata[i]) for i, t in enumerate(tasks)]
            
            # Process in batches to update progress more frequently
            results = []
            batch_size = 3
            for batch_start in range(0, len(safe_tasks), batch_size):
                batch_end = min(batch_start + batch_size, len(safe_tasks))
                batch = safe_tasks[batch_start:batch_end]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                results.extend(batch_results)
                
                # Update progress after each batch
                percent = 40 + int((len(results) / len(safe_tasks)) * 45)  # 40-85%
                self._update_progress(uid, campaign_id, f"Generated {len(results)}/{len(tasks)} assets...", percent)
            
            # Map results back to structured assets
            from app.services.asset_processor import get_asset_processor
            asset_processor = get_asset_processor()
            
            assets = {}
            temp_carousel_storage = {} # Store slides: {channel: {index: url}}
            assets_metadata = {}

            for i, result in enumerate(results):
                meta = task_metadata[i]
                channel = meta["channel"]
                
                # V4.0: Enhanced error detection
                if isinstance(result, Exception):
                    logger.error(f"❌ Exception generating asset for {channel}: {result}")
                    assets_metadata[channel] = {**meta, "error": str(result), "status": "FAILED"}
                    continue
                
                # Check for error dict from our enhanced ImageAgent
                if isinstance(result, dict) and "error" in result:
                    logger.warning(f"⚠️ Asset error for {channel}: {result.get('error')} - {result.get('message')}")
                    assets_metadata[channel] = {**meta, "error": result.get('message'), "status": "FAILED"}
                    continue
                    
                # Extract URL if dict (new format), else use result (legacy string)
                raw_url = result.get('url') if isinstance(result, dict) else result
                
                if not raw_url:
                    logger.warning(f"⚠️ No URL returned for {channel}")
                    assets_metadata[channel] = {**meta, "error": "No URL generated", "status": "FAILED"}
                    continue
                
                # FIX 1: Apply Advanced Branding
                # Use the new apply_advanced_branding with layout styles
                if channel not in ['blog', 'email']:
                    try:
                        # Apply advanced branding with layout styles
                        final_url = await asyncio.to_thread(
                            asset_processor.apply_advanced_branding,
                            raw_url,
                            brand_dna
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Advanced branding skipped for {channel}: {e}")
                        final_url = raw_url
                else:
                    final_url = raw_url

                # HANDLE CAROUSEL
                if meta.get("format_type") == "carousel":
                    if channel not in temp_carousel_storage:
                        temp_carousel_storage[channel] = {}
                    temp_carousel_storage[channel][meta["slide_index"]] = final_url
                    # We don't set assets[channel] yet, we wait until loop end
                    
                # HANDLE MOTION - Use Template Library
                elif meta.get("motion_enabled"):
                    # Get brand details for motion
                    logo_url = brand_dna.get('logo_url', '')
                    primary_color = brand_dna.get('color_palette', {}).get('primary', '#000000')
                    
                    # V3.0: Analyze luminance for intelligent contrast
                    try:
                        luminance_mode = asset_processor.analyze_luminance_from_url(final_url)
                        logger.info(f"🔍 Luminance mode for {channel}: {luminance_mode}")
                    except Exception as lum_err:
                        logger.warning(f"⚠️ Luminance analysis failed, defaulting to 'dark': {lum_err}")
                        luminance_mode = 'dark'
                    
                    # Generate HTML asset using template library
                    channel_blueprint = blueprint.get(channel, {})
                    copy_text = channel_blueprint.get("headlines", ["Brand Motion"])[0]
                    
                    # Select template - V3.0 Smart Priority System
                    tone = meta.get("tone", "professional")
                    template_name = None
                    
                    # 1. Smart Context Match (New Universal Templates)
                    try:
                        # Combine goal words and tone as keywords
                        context_keywords = goal.split() + [tone]
                        if brand_dna.get("industry"): 
                            context_keywords.append(brand_dna.get("industry"))
                            
                        smart_match = asset_processor.analyze_image_context(context_keywords)
                        if smart_match:
                            template_name = smart_match
                            logger.info(f"🧠 Smart Context Template Selected: {template_name}")
                    except Exception as e:
                        logger.warning(f"Smart selection failed: {e}")

                    # 2. Key Tone Match (Existing Logic)
                    if not template_name:
                        # 40% chance to force tone match if not smart matched
                        if random.random() < 0.4:
                            template_name = get_template_for_tone(tone)
                            logger.info(f"🎯 Using tone-matched template: {template_name}")
                        else:
                    # 3. Random Rotation (Variety)
                            template_name = get_random_template()
                            logger.info(f"🎲 Using random template: {template_name}")
                    
                    # Randomize Layout Variant
                    layout_variant = random.choice(['hero-center', 'editorial-left', 'editorial-right'])
                    
                    # Generate motion HTML from template library with luminance mode and layout variant
                    html_content = get_motion_template(template_name, final_url, logo_url, primary_color, copy_text, luminance_mode, layout_variant)
                    encoded = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
                    html_asset = f"data:text/html;charset=utf-8;base64,{encoded}"
                    
                    # Store with format label for multi-format support
                    format_label = meta.get("format_label", "primary")
                    asset_key = f"{channel}_{format_label}" if format_label != 'primary' else channel
                    assets[asset_key] = html_asset
                    
                # STANDARD IMAGE
                else:
                    # Store with format label for multi-format support
                    format_label = meta.get("format_label", "primary")
                    asset_key = f"{channel}_{format_label}" if format_label != 'primary' else channel
                    assets[asset_key] = final_url
                
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
            
            # 5. Save drafts per channel + format for User Self-Approval (Review Feed)
            for channel in target_channels:
                clean_channel = channel.lower().replace(" ", "_")
                try:
                    channel_assets = []
                    for asset_key, asset_payload in assets.items():
                        if asset_key == clean_channel:
                            channel_assets.append((None, asset_payload))
                        elif asset_key.startswith(f"{clean_channel}_"):
                            fmt = asset_key[len(clean_channel) + 1:]
                            channel_assets.append((fmt, asset_payload))

                    if not channel_assets:
                        channel_assets = [(None, None)]

                    for fmt, asset_payload in channel_assets:
                        suffix = f"_{fmt}" if fmt and fmt != "feed" else ""
                        draft_id = f"draft_{campaign_id}_{clean_channel}{suffix}"

                        meta = assets_metadata.get(channel, {})
                        channel_blueprint = blueprint.get(channel, blueprint.get('instagram', {}))

                        if asset_payload:
                            status = "DRAFT"
                            thumbnail_url = asset_payload
                            if isinstance(asset_payload, list):
                                thumbnail_url = asset_payload[0]
                            elif isinstance(asset_payload, str) and asset_payload.startswith("data:text/html"):
                                thumbnail_url = asset_payload
                        else:
                            status = "FAILED"
                            thumbnail_url = "https://placehold.co/600x400?text=Generation+Failed"
                            # Capture specific error if available in payload (which might be Exception object)
                            error_msg = str(asset_payload) if asset_payload and isinstance(asset_payload, (Exception, str)) else "Unknown Error"
                            asset_payload = None

                        text_copy = channel_blueprint.get("caption") or channel_blueprint.get("body")
                        if not text_copy and channel_blueprint.get("headlines"):
                            text_copy = channel_blueprint["headlines"][0]
                        if not text_copy:
                            text_copy = goal or "Brand Campaign Asset"

                        draft_data = {
                            "userId": uid,
                            "campaignId": campaign_id,
                            "campaignGoal": goal,  # V4.0: For frontend grouping by goal
                            "channel": clean_channel,
                            "thumbnailUrl": thumbnail_url,
                            "assetPayload": asset_payload,
                            "asset_url": asset_payload if asset_payload else None,
                            "title": f"{goal[:50]}..." if len(goal) > 50 else goal,
                            "format": meta.get("format_type", "Image"),
                            "size": f"{meta.get('size', (0,0))[0]}x{meta.get('size', (0,0))[1]}" if meta.get('size') else "N/A",
                            "tone": meta.get("tone", "professional"),
                            "status": status,
                            "approvalStatus": "pending",
                            "createdAt": firestore.SERVER_TIMESTAMP,
                            "blueprint": channel_blueprint,
                            "textCopy": text_copy
                        }

                        self.db.collection('creative_drafts').document(draft_id).set(draft_data)
                        logger.info(f"📦 Saved draft {draft_id} [{status}] for user {uid} (channel: {clean_channel})")
                except Exception as save_err:
                    logger.error(f"❌ Failed to save drafts for {clean_channel}: {save_err}")
                    failed_draft_id = f"draft_{campaign_id}_{clean_channel}"
                    failed_draft = {
                        "userId": uid,
                        "campaignId": campaign_id,
                        "campaignGoal": goal,  # V4.0: For frontend grouping by goal
                        "channel": clean_channel,
                        "thumbnailUrl": "https://placehold.co/600x400?text=Generation+Failed",
                        "assetPayload": None,
                        "asset_url": None,
                        "title": f"{goal[:50]}..." if len(goal) > 50 else goal,
                        "format": "Image",
                        "size": "N/A",
                        "tone": "professional",
                        "status": "FAILED",
                        "approvalStatus": "pending",
                        "createdAt": firestore.SERVER_TIMESTAMP,
                        "blueprint": blueprint.get(channel, blueprint.get('instagram', {})),
                        "textCopy": goal or "Brand Campaign Asset"
                    }
                    self.db.collection('creative_drafts').document(failed_draft_id).set(failed_draft)
            
            # V4.0: Enhanced completion notification with details
            success_count = len([k for k, v in assets.items() if v and not isinstance(v, dict) or (isinstance(v, dict) and 'error' not in v)])
            goal_short = f"{goal[:40]}..." if len(goal) > 40 else goal
            self._update_progress(uid, campaign_id, f"Campaign Ready! {success_count} assets for: {goal_short}", 100)

        except Exception as e:
            self.handle_error(e)
            self._update_progress(uid, campaign_id, "Error in generation.", 0, failed=True)

    def _update_progress(self, uid, campaign_id, message, percent, failed=False):
        """V4.0: Enhanced notifications with title, link, and proper timestamps."""
        # Determine status and title
        status = "error" if failed else ("completed" if percent == 100 else "processing")
        
        if failed:
            title = "❌ Campaign Failed"
        elif percent == 100:
            title = "🎉 Campaign Ready"
        else:
            title = "⚙️ Generating Campaign"
        
        notif_ref = self.db.collection('users').document(uid).collection('notifications').document(campaign_id)
        notif_ref.set({
            "title": title,
            "message": message,
            "progress": percent,
            "type": "campaign_progress",
            "campaign_id": campaign_id,
            "status": status,
            "link": "/creative-studio?view=library" if percent == 100 else None,  # Navigate to asset library when complete
            "created_at": firestore.SERVER_TIMESTAMP,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

    def _get_motion_template(self, style_name: str) -> dict:
        """
        V3.0 Animation Library: Returns CSS and GSAP code for the given style.
        
        Styles:
        - cinematic: Luxury feel (coffee/fashion) - blur text, slow scale
        - hype: Modern energy (sneakers/tech) - skew text, yoyo overlay
        - float: Soft calm (services/wellness) - floating text, rotating logo
        """
        templates = {
            "cinematic": {
                "css_extra": """
                    #card {
                        position: absolute; bottom: 0; left: 0; right: 0;
                        padding: 30px 20px; z-index: 50;
                        background: rgba(255,255,255,0.15);
                        backdrop-filter: blur(12px);
                        -webkit-backdrop-filter: blur(12px);
                        border-top: 1px solid rgba(255,255,255,0.2);
                    }
                """,
                "gsap": """
                    gsap.from("#text", {filter:"blur(20px)", opacity:0, duration:2});
                    gsap.to("#bg", {scale:1.15, duration:10, ease:"none"});
                    gsap.from("#logo", {opacity:0, y:-20, duration:1.5, delay:0.5});
                """,
                "text_wrapper": "card"
            },
            "hype": {
                "css_extra": """
                    #overlay {
                        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                        background: linear-gradient(135deg, rgba(0,0,0,0.7) 0%, transparent 50%);
                        z-index: 10;
                    }
                    #text {
                        font-size: 32px; text-transform: uppercase; letter-spacing: 2px;
                    }
                """,
                "gsap": """
                    gsap.from("#text", {y:100, skewY:10, opacity:0, duration:0.8, ease:"back.out(1.7)"});
                    gsap.to("#overlay", {opacity:0.3, duration:1, yoyo:true, repeat:-1, ease:"power1.inOut"});
                    gsap.from("#logo", {scale:0.5, opacity:0, duration:0.6, delay:0.3, ease:"back.out"});
                """,
                "text_wrapper": None,
                "has_overlay": True
            },
            "float": {
                "css_extra": """
                    #text {
                        font-size: 22px; font-weight: 400; letter-spacing: 1px;
                    }
                    #logo {
                        width: 60px;
                    }
                """,
                "gsap": """
                    gsap.to("#text", {y:-10, duration:2, yoyo:true, repeat:-1, ease:"sine.inOut"});
                    gsap.from("#logo", {rotation:-10, opacity:0, duration:1, ease:"power2.out"});
                    gsap.to("#bg", {scale:1.05, duration:8, ease:"none"});
                """,
                "text_wrapper": None
            }
        }
        return templates.get(style_name, templates["cinematic"])

    def _generate_html_motion_asset(self, image_url, logo_url, color, text):
        """
        V3.0: Generates HTML5 motion asset with dynamic style selection.
        Randomly selects from 3 animation styles: cinematic, hype, float.
        """
        # Select style randomly
        style = random.choice(['cinematic', 'hype', 'float'])
        template = self._get_motion_template(style)
        
        # Select layout variant randomly - NEW V3.1
        layout_variant = random.choice(['hero-center', 'editorial-left', 'editorial-right'])
        
        css_extra = template.get("css_extra", "")
        gsap_code = template.get("gsap", "")
        has_overlay = template.get("has_overlay", False)
        text_wrapper = template.get("text_wrapper")
        
        # Build overlay element if needed
        overlay_html = '<div id="overlay"></div>' if has_overlay else ''
        
        # Build text element (wrapped in card for cinematic style)
        if text_wrapper == "card":
            text_html = f'<div id="card" class="variant-{layout_variant}"><div id="text">{text}</div></div>'
        else:
            text_html = f'<div id="text" class="variant-{layout_variant}">{text}</div>'
        
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
                    color: white; font-family: 'Segoe UI', Arial, sans-serif; font-size: 24px; font-weight: bold;
                    text-shadow: 0 2px 8px rgba(0,0,0,0.8);
                    z-index: 60;
                }}
                {css_extra}
            </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
        </head>
        <body>
            <div id="bg"></div>
            {overlay_html}
            <img id="logo" src="{logo_url}" onerror="this.style.display='none'">
            {text_html}
            <script>
                {gsap_code}
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
