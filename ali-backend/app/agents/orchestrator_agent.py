import asyncio
import logging
import base64
import json
import random
from app.agents.base_agent import BaseAgent
from app.agents.campaign_agent import CampaignAgent
from app.services.image_agent import ImageAgent
from app.core.security import db
from app.core.templates import get_motion_template, get_template_for_tone, get_random_template, get_optimized_template, MOTION_TEMPLATES, FONT_MAP, TEMPLATE_COMPLEXITY
from firebase_admin import firestore

logger = logging.getLogger("ali_platform.agents.orchestrator_agent")

# V4.0 Configuration
IMAGE_GENERATION_TIMEOUT = 120  # Seconds per image

# V5.1: Graceful shutdown support - set by main.py SIGTERM handler
_shutdown_requested = False

def request_shutdown():
    """Called by main.py when SIGTERM is received."""
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning("🛑 Orchestrator: Shutdown requested - will save progress and exit gracefully")

def is_shutdown_requested():
    """Check if shutdown has been requested."""
    return _shutdown_requested


async def auto_resume_interrupted_campaigns():
    """
    V6.1: Automatically resume all interrupted campaigns on startup.
    Called during application startup to transparently continue any 
    campaigns that were interrupted by instance shutdown, memory issues, etc.
    
    User never knows the interruption happened - it just continues silently.
    """
    try:
        if not db:
            logger.warning("⚠️ Database not available, skipping auto-resume")
            return
        
        # Find all checkpoints (interrupted campaigns)
        checkpoints = db.collection('generation_checkpoints').stream()
        
        resume_count = 0
        for checkpoint_doc in checkpoints:
            try:
                checkpoint = checkpoint_doc.to_dict()
                campaign_id = checkpoint_doc.id
                uid = checkpoint.get("userId")
                
                if not uid:
                    continue
                
                # Get campaign data
                campaign_doc = db.collection('users').document(uid).collection('campaigns').document(campaign_id).get()
                if not campaign_doc.exists:
                    # Campaign was deleted, clean up orphan checkpoint
                    checkpoint_doc.reference.delete()
                    continue
                
                campaign_data = campaign_doc.to_dict()
                
                # Skip if campaign is already completed
                if campaign_data.get("status") == "completed":
                    checkpoint_doc.reference.delete()
                    continue
                
                # Get brand DNA for this user
                brand_doc = db.collection('users').document(uid).collection('brand_profile').document('current').get()
                brand_dna = brand_doc.to_dict() if brand_doc.exists else {}
                
                # Calculate pending channels
                completed_channels = checkpoint.get("completedChannels", [])
                all_channels = campaign_data.get("selected_channels", [])
                
                pending_channels = []
                for ch in all_channels:
                    if not any(comp.startswith(ch) for comp in completed_channels):
                        pending_channels.append(ch)
                
                if not pending_channels:
                    # All done, clean up checkpoint
                    checkpoint_doc.reference.delete()
                    continue
                
                logger.info(f"🔄 Auto-resuming campaign {campaign_id} for user {uid} - {len(pending_channels)} channels pending")
                
                # Resume generation in background
                orchestrator = OrchestratorAgent()
                asyncio.create_task(
                    orchestrator.run_full_campaign_flow(
                        uid, campaign_id,
                        campaign_data.get("goal", ""),
                        brand_dna,
                        {},  # answers not needed for resume
                        pending_channels
                    )
                )
                
                resume_count += 1
                
            except Exception as resume_err:
                logger.error(f"❌ Failed to auto-resume campaign {checkpoint_doc.id}: {resume_err}")
                continue
        
        if resume_count > 0:
            logger.info(f"✅ Auto-resume: Restarted {resume_count} interrupted campaign(s)")
        else:
            logger.debug("🔍 Auto-resume: No interrupted campaigns found")
            
    except Exception as e:
        logger.error(f"❌ Auto-resume failed: {e}")


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

    # =========================================================================
    # V6.1: Generation Checkpointing - Resumable Campaign Generation
    # Saves state after each asset, allows resuming from interruption points
    # =========================================================================
    
    def _save_checkpoint(self, uid: str, campaign_id: str, checkpoint_data: dict):
        """
        Save generation checkpoint to Firestore.
        Called after blueprint generation and after each asset completion.
        """
        try:
            checkpoint_ref = self.db.collection('generation_checkpoints').document(campaign_id)
            checkpoint_data.update({
                "userId": uid,
                "campaignId": campaign_id,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
            checkpoint_ref.set(checkpoint_data, merge=True)
            logger.debug(f"💾 Checkpoint saved for campaign {campaign_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save checkpoint: {e}")
    
    def _load_checkpoint(self, campaign_id: str) -> dict:
        """
        Load existing checkpoint for resume capability.
        Returns empty dict if no checkpoint exists.
        """
        try:
            checkpoint_ref = self.db.collection('generation_checkpoints').document(campaign_id)
            doc = checkpoint_ref.get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.warning(f"⚠️ Failed to load checkpoint: {e}")
        return {}
    
    def _mark_channel_complete(self, campaign_id: str, channel: str, format_label: str = "primary"):
        """
        Mark a specific channel/format as completed in the checkpoint.
        Called immediately after each asset is successfully generated.
        """
        try:
            checkpoint_ref = self.db.collection('generation_checkpoints').document(campaign_id)
            checkpoint_ref.set({
                "completedChannels": firestore.ArrayUnion([f"{channel}_{format_label}"]),
                "updatedAt": firestore.SERVER_TIMESTAMP
            }, merge=True)
            logger.debug(f"✅ Marked {channel}_{format_label} as complete")
        except Exception as e:
            logger.warning(f"⚠️ Failed to mark channel complete: {e}")
    
    def _clear_checkpoint(self, campaign_id: str):
        """Remove checkpoint after successful completion."""
        try:
            self.db.collection('generation_checkpoints').document(campaign_id).delete()
            logger.info(f"🧹 Cleared checkpoint for completed campaign {campaign_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to clear checkpoint: {e}")
    
    def _get_pending_channels(self, all_channels: list, completed: list) -> list:
        """
        Filter out already-completed channels from the generation list.
        Used when resuming from a checkpoint.
        """
        return [ch for ch in all_channels if ch not in completed]

    def _save_draft_immediately(self, uid, campaign_id, goal, channel, asset_payload, meta, blueprint):
        """
        V5.1: Progressive draft saving - saves draft immediately after asset is processed.
        This ensures drafts are persisted even if the instance is terminated mid-generation.
        """
        try:
            clean_channel = channel.lower().replace(" ", "_")
            format_label = meta.get("format_label", "primary")
            suffix = f"_{format_label}" if format_label and format_label not in ["feed", "primary"] else ""
            draft_id = f"draft_{campaign_id}_{clean_channel}{suffix}"
            
            channel_blueprint = blueprint.get(channel, blueprint.get('instagram', {}))
            
            # Determine status and thumbnail
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
            
            # Build text copy
            text_copy = channel_blueprint.get("caption") or channel_blueprint.get("body")
            if not text_copy and channel_blueprint.get("headlines"):
                text_copy = channel_blueprint["headlines"][0]
            if not text_copy:
                text_copy = goal or "Brand Campaign Asset"
            
            draft_data = {
                "userId": uid,
                "campaignId": campaign_id,
                "campaignGoal": goal,
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
            logger.info(f"📦 Saved draft {draft_id} [{status}] immediately for {clean_channel}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save draft immediately for {channel}: {e}")
            return False


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
            target_channels = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in target_channels]
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
                    
                    # Select template - V6.0 Optimized Template Selection
                    tone = meta.get("tone", "professional")
                    
                    # Use new optimized selection with industry, complexity, and channel awareness
                    template_name = get_optimized_template(
                        brand_dna=brand_dna,
                        goal=goal,
                        tone=tone,
                        channel=channel,
                        prefer_low_complexity=(channel in ['tiktok', 'youtube_shorts'])
                    )
                    logger.info(f"🎨 V6.0 Template Selected: {template_name} (complexity: {TEMPLATE_COMPLEXITY.get(template_name, 'unknown')})")
                    
                    # Randomize Layout Variant
                    layout_variant = random.choice(['hero-center', 'editorial-left', 'editorial-right'])
                    
                    # Generate motion HTML from template library with luminance mode and layout variant
                    html_content = get_motion_template(template_name, final_url, logo_url, primary_color, copy_text, luminance_mode, layout_variant)
                    
                    # Store with format label for multi-format support
                    format_label = meta.get("format_label", "primary")
                    asset_key = f"{channel}_{format_label}" if format_label != 'primary' else channel
                    
                    # ============================================================
                    # V5.0 SMART FORMAT SELECTION
                    # Read format_type from AI blueprint, with TikTok override
                    # ============================================================
                    ai_format_type = channel_blueprint.get("format_type", "image")
                    
                    # OVERRIDE: TikTok MUST always be video regardless of AI output
                    if channel == "tiktok":
                        ai_format_type = "video"
                        logger.info(f"📹 TikTok override: forcing video format")
                    
                    # Determine final format considering format_label
                    is_video = (
                        ai_format_type == "video" or 
                        format_label == "story" or
                        channel in ['youtube_shorts', 'facebook_story']
                    )
                    
                    logger.info(f"📊 Smart Format for {channel}: format_type={ai_format_type}, is_video={is_video}")
                    
                    # Get dimensions
                    w, h = meta.get("size", (1080, 1920))
                    
                    if is_video:
                        # V5.0: Use generate_video_asset with automatic fallback
                        logger.info(f"🎥 Generating VIDEO asset for {channel} ({w}x{h})...")
                        asset_url = await asset_processor.generate_video_asset(
                            html_content=html_content,
                            user_id=uid,
                            asset_id=f"{campaign_id}_{asset_key}",
                            width=w,
                            height=h,
                            duration=6.0,
                            fallback_to_image=True  # Auto-fallback on failure
                        )
                        if asset_url:
                            assets[asset_key] = asset_url
                            # Determine if it's video or fallback image
                            if asset_url.endswith('.mp4') or asset_url.endswith('.webm') or 'video' in asset_url:
                                meta["format_type"] = "video"
                                # If webm, warn about potential compatibility
                                if asset_url.endswith('.webm'):
                                    meta["compatibility_warning"] = "WebM format - may not play on all mobile devices"
                            else:
                                meta["format_type"] = "image"  # Fallback occurred
                        else:
                            # Both video and fallback failed - use HTML as last resort
                            logger.warning(f"⚠️ All rendering failed for {channel}, using HTML fallback")
                            encoded = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
                            assets[asset_key] = f"data:text/html;charset=utf-8;base64,{encoded}"
                            meta["format_type"] = "html"
                    else:
                        # V5.0: Use generate_image_asset with GSAP snap-to-finish
                        logger.info(f"📸 Generating IMAGE asset for {channel} ({w}x{h})...")
                        asset_url = await asset_processor.generate_image_asset(
                            html_content=html_content,
                            user_id=uid,
                            asset_id=f"{campaign_id}_{asset_key}",
                            width=w,
                            height=h
                        )
                        if asset_url:
                            assets[asset_key] = asset_url
                            meta["format_type"] = "image"
                        else:
                            # Fallback to base64 HTML
                            logger.warning(f"⚠️ Image generation failed for {channel}, using HTML fallback")
                            encoded = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
                            assets[asset_key] = f"data:text/html;charset=utf-8;base64,{encoded}"
                            meta["format_type"] = "html"
                    
                    assets_metadata[channel] = meta
                    
                # STANDARD IMAGE (non-motion channels)
                else:
                    # Store with format label for multi-format support
                    format_label = meta.get("format_label", "primary")
                    asset_key = f"{channel}_{format_label}" if format_label != 'primary' else channel
                    assets[asset_key] = final_url
                    meta["format_type"] = "image"
                
                # Save metadata (overwrite is fine for carousel as base props are same)
                assets_metadata[channel] = meta
                
                # V5.1: Progressive draft saving - save immediately after processing
                # This ensures the draft is persisted even if SIGTERM interrupts the generation
                if meta.get("format_type") != "carousel":  # Carousel handled separately
                    asset_key = f"{channel}_{meta.get('format_label', 'primary')}" if meta.get('format_label') not in [None, 'primary', 'feed'] else channel
                    draft_saved = self._save_draft_immediately(
                        uid, campaign_id, goal, channel,
                        assets.get(asset_key) or assets.get(channel),
                        meta, blueprint
                    )
                    # V6.1: Mark channel as complete for resume capability
                    if draft_saved:
                        self._mark_channel_complete(campaign_id, channel, meta.get("format_label", "primary"))

                
                # V5.1: Check for graceful shutdown between assets
                if is_shutdown_requested():
                    logger.warning(f"⚠️ Shutdown requested after processing {channel} - saving progress...")
                    self._update_progress(uid, campaign_id, f"Generation paused - {len(assets)} assets saved", 90)
                    # Save campaign with partial results
                    partial_data = {
                        "status": "interrupted",
                        "blueprint": blueprint,
                        "assets": assets,
                        "assets_metadata": assets_metadata,
                        "selected_channels": target_channels,
                        "goal": goal,
                        "campaign_id": campaign_id
                    }
                    self.db.collection('users').document(uid).collection('campaigns').document(campaign_id).set(partial_data, merge=True)
                    logger.info(f"💾 Saved partial campaign progress before shutdown")
                    return  # Exit gracefully

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
            
            # 5. V5.1: Handle carousel draft finalization (progressive saving handles most drafts already)
            # Save carousel drafts that weren't handled in the loop
            for channel, slides in temp_carousel_storage.items():
                if slides:
                    try:
                        clean_channel = channel.lower().replace(" ", "_")
                        draft_id = f"draft_{campaign_id}_{clean_channel}"
                        channel_blueprint = blueprint.get(channel, blueprint.get('instagram', {}))
                        meta = assets_metadata.get(channel, {})
                        
                        sorted_slides = [slides[k] for k in sorted(slides.keys())]
                        
                        text_copy = channel_blueprint.get("caption") or channel_blueprint.get("body")
                        if not text_copy and channel_blueprint.get("headlines"):
                            text_copy = channel_blueprint["headlines"][0]
                        if not text_copy:
                            text_copy = goal or "Brand Campaign Asset"
                        
                        draft_data = {
                            "userId": uid,
                            "campaignId": campaign_id,
                            "campaignGoal": goal,
                            "channel": clean_channel,
                            "thumbnailUrl": sorted_slides[0] if sorted_slides else "https://placehold.co/600x400",
                            "assetPayload": sorted_slides,
                            "asset_url": sorted_slides,
                            "title": f"{goal[:50]}..." if len(goal) > 50 else goal,
                            "format": "carousel",
                            "size": f"{meta.get('size', (0,0))[0]}x{meta.get('size', (0,0))[1]}" if meta.get('size') else "N/A",
                            "tone": meta.get("tone", "professional"),
                            "status": "DRAFT",
                            "approvalStatus": "pending",
                            "createdAt": firestore.SERVER_TIMESTAMP,
                            "blueprint": channel_blueprint,
                            "textCopy": text_copy
                        }
                        self.db.collection('creative_drafts').document(draft_id).set(draft_data)
                        logger.info(f"📦 Saved carousel draft {draft_id} for {clean_channel}")
                    except Exception as carousel_err:
                        logger.error(f"❌ Failed to save carousel draft for {channel}: {carousel_err}")
            
            # V4.0: Enhanced completion notification with details
            success_count = len([k for k, v in assets.items() if v and not isinstance(v, dict) or (isinstance(v, dict) and 'error' not in v)])
            goal_short = f"{goal[:40]}..." if len(goal) > 40 else goal
            self._update_progress(uid, campaign_id, f"Campaign Ready! {success_count} assets for: {goal_short}", 100)
            
            # V6.1: Clear checkpoint on successful completion
            self._clear_checkpoint(campaign_id)

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
