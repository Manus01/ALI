import asyncio
import logging
import base64
import json
import random
from typing import Any, Dict, List, Optional
from app.agents.base_agent import BaseAgent
from app.agents.campaign_agent import CampaignAgent
from app.services.image_agent import ImageAgent
from app.services.claims_verifier import verify_claims
from app.services.qc_rubric import evaluate_copy
from app.core.security import db
from app.core.templates import get_motion_template, get_template_for_tone, get_random_template, get_optimized_template, MOTION_TEMPLATES, FONT_MAP, TEMPLATE_COMPLEXITY
from app.services.governance import run_qc_rubric, verify_claims_for_blueprint
from firebase_admin import firestore

logger = logging.getLogger("ali_platform.agents.orchestrator_agent")

# V4.0 Configuration
IMAGE_GENERATION_TIMEOUT = 120  # Seconds per image

# V7.0: Enable Veo Video Pipeline
# When True, uses Google Veo for AI-generated video backgrounds
# with HTML text overlays. Falls back to HTML animations if Veo fails.
ENABLE_VEO_VIDEO = True

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
    },
    "twitter": {
        "formats": [
            {"type": "feed", "size": (1200, 675), "ratio": "16:9"},
            {"type": "square", "size": (1080, 1080), "ratio": "1:1"},
            {"type": "video", "size": (1080, 1920), "ratio": "9:16"}
        ],
        "tone": "concise_conversational",
        "motion_support": True
    },
    "youtube_shorts": {
        "formats": [
            {"type": "video", "size": (1080, 1920), "ratio": "9:16", "safe_zone_bottom": 350}
        ],
        "tone": "engaging_hook_driven",
        "motion_support": True
    }
}

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Orchestrator")
        self.db = db

    def _get_latest_competitor_snapshot(self, uid: str) -> Optional[Dict[str, Any]]:
        try:
            snapshot_ref = (
                self.db.collection("competitiveInsights")
                .document(uid)
                .collection("snapshots")
                .order_by("createdAt", direction=firestore.Query.DESCENDING)
                .limit(1)
            )
            docs = list(snapshot_ref.stream())
            if not docs:
                return None
            snapshot = docs[0].to_dict()
            snapshot["snapshot_id"] = docs[0].id
            return snapshot
        except Exception as e:
            logger.warning(f"⚠️ Failed to load competitor snapshot: {e}")
            return None

    def _get_recent_creative_memory(self, uid: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            memory_ref = (
                self.db.collection("users")
                .document(uid)
                .collection("creative_memory")
                .order_by("createdAt", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            return [doc.to_dict() for doc in memory_ref.stream()]
        except Exception as e:
            logger.warning(f"⚠️ Failed to load creative memory: {e}")
            return []

    def _save_creative_memory(
        self,
        uid: str,
        campaign_id: str,
        goal: str,
        blueprint: Dict[str, Any],
        creative_intent: Optional[Dict[str, Any]],
    ) -> None:
        try:
            hooks = []
            for channel, payload in blueprint.items():
                if channel == "theme" or not isinstance(payload, dict):
                    continue
                hook = (
                    payload.get("headline")
                    or (payload.get("headlines") or [None])[0]
                    or payload.get("caption")
                    or payload.get("body")
                )
                if hook:
                    hooks.append({"channel": channel, "hook": hook[:160]})

            memory_payload = {
                "campaignId": campaign_id,
                "goal": goal,
                "theme": blueprint.get("theme"),
                "hooks": hooks,
                "intent": creative_intent or {},
                "createdAt": firestore.SERVER_TIMESTAMP,
            }

            self.db.collection("users").document(uid).collection("creative_memory").add(memory_payload)
            logger.info(f"🧠 Saved creative memory for campaign {campaign_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save creative memory: {e}")

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

    # =========================================================================
    # V6.2: Granular AI Image Caching - Skip expensive AI calls on resume
    # Saves the AI-generated image URL before rendering, so on resume we only
    # need to redo the fast render step (0.5s image or 4s video) instead of
    # the expensive AI generation (15s per image)
    # =========================================================================
    
    def _save_ai_image_cache(self, campaign_id: str, channel: str, format_label: str, image_url: str):
        """
        Cache the AI-generated image URL before rendering.
        On resume, this allows skipping the expensive AI call.
        """
        try:
            cache_key = f"{channel}_{format_label}"
            checkpoint_ref = self.db.collection('generation_checkpoints').document(campaign_id)
            checkpoint_ref.set({
                f"aiImageCache.{cache_key}": image_url,
                "updatedAt": firestore.SERVER_TIMESTAMP
            }, merge=True)
            logger.debug(f"💾 Cached AI image for {cache_key}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache AI image: {e}")
    
    def _get_cached_ai_image(self, campaign_id: str, channel: str, format_label: str) -> str:
        """
        Retrieve cached AI image URL if available.
        Returns None if no cache exists.
        """
        try:
            checkpoint_doc = self.db.collection('generation_checkpoints').document(campaign_id).get()
            if checkpoint_doc.exists:
                data = checkpoint_doc.to_dict()
                cache_key = f"{channel}_{format_label}"
                cached_url = data.get("aiImageCache", {}).get(cache_key)
                if cached_url:
                    logger.info(f"♻️ Using cached AI image for {cache_key} (skipping 15s AI call)")
                    return cached_url
        except Exception as e:
            logger.warning(f"⚠️ Failed to load cached AI image: {e}")
        return None
    
    def _clear_ai_image_cache(self, campaign_id: str, channel: str, format_label: str):
        """Remove cached AI image after successful completion of this asset."""
        try:
            cache_key = f"{channel}_{format_label}"
            checkpoint_ref = self.db.collection('generation_checkpoints').document(campaign_id)
            checkpoint_ref.update({
                f"aiImageCache.{cache_key}": firestore.DELETE_FIELD
            })
        except Exception:
            pass  # Non-critical


    def _save_draft_immediately(
        self,
        uid,
        campaign_id,
        goal,
        channel,
        asset_payload,
        meta,
        blueprint,
        creative_intent: Optional[Dict[str, Any]] = None,
        claims_report: Optional[Dict[str, Any]] = None,
        qc_report: Optional[Dict[str, Any]] = None,
    ):
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
            original_asset_payload = asset_payload
            if asset_payload:
                status = "DRAFT"
                thumbnail_url = asset_payload
                if isinstance(asset_payload, list):
                    thumbnail_url = asset_payload[0]
                elif isinstance(asset_payload, str) and asset_payload.startswith("data:text/html"):
                    thumbnail_url = asset_payload
                if isinstance(asset_payload, str) and asset_payload.startswith("data:text/html"):
                    asset_payload = None
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
                "asset_url": original_asset_payload if original_asset_payload else None,
                "title": f"{goal[:50]}..." if len(goal) > 50 else goal,
                "format": meta.get("format_type", "Image"),
                "size": f"{meta.get('size', (0,0))[0]}x{meta.get('size', (0,0))[1]}" if meta.get('size') else "N/A",
                "tone": meta.get("tone", "professional"),
                "status": status,
                "approvalStatus": "pending",
                "createdAt": firestore.SERVER_TIMESTAMP,
                "blueprint": channel_blueprint,
                "textCopy": text_copy,
                "intent": meta.get("intent"),
                "claimsReport": meta.get("claims_report"),
                "qcReport": meta.get("qc_report")
            }
            
            self.db.collection('creative_drafts').document(draft_id).set(draft_data)
            logger.info(f"📦 Saved draft {draft_id} [{status}] immediately for {clean_channel}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save draft immediately for {channel}: {e}")
            return False

    def _save_creative_memory(self, uid: str, campaign_id: str, intent: dict, blueprint: dict):
        """Persist reusable creative hooks and intent per tenant."""
        try:
            hooks = []
            for channel, data in blueprint.items():
                if not isinstance(data, dict):
                    continue
                if data.get("headlines"):
                    hooks.extend(data["headlines"])
                if data.get("caption"):
                    hooks.append(data["caption"])
                if data.get("body"):
                    hooks.append(data["body"])

            memory_ref = self.db.collection('users').document(uid).collection('creative_memory')
            memory_ref.add({
                "campaignId": campaign_id,
                "intent": intent,
                "hooks": hooks[:10],
                "createdAt": firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            logger.warning(f"⚠️ Failed to save creative memory: {e}")

    def _load_creative_memory(self, uid: str) -> list:
        """Fetch recent reusable hooks for a tenant."""
        try:
            docs = self.db.collection('users').document(uid).collection('creative_memory').order_by("createdAt", direction=firestore.Query.DESCENDING).limit(5).stream()
            hooks = []
            for doc in docs:
                data = doc.to_dict()
                hooks.extend(data.get("hooks", []))
            return hooks[:10]
        except Exception as e:
            logger.warning(f"⚠️ Failed to load creative memory: {e}")
            return []

    def _load_competitor_insights(self, uid: str) -> dict:
        """Fetch latest competitor insights snapshot for context."""
        try:
            docs = self.db.collection('competitiveInsights').document(uid).collection('snapshots').order_by("createdAt", direction=firestore.Query.DESCENDING).limit(1).stream()
            latest = next(docs, None)
            return latest.to_dict() if latest else {}
        except Exception as e:
            logger.warning(f"⚠️ Failed to load competitor insights: {e}")
            return {}

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

            # 1.5 Generate Creative Intent Object
            planner = CampaignAgent()
            memory_hooks = self._load_creative_memory(uid)
            competitor_insights = self._load_competitor_insights(uid)
            intent_object = await planner.generate_creative_intent(
                goal,
                brand_dna,
                answers,
                selected_channels=target_channels,
                memory_hooks=memory_hooks,
                competitor_insights=competitor_insights
            )
            premium_media_allowed = brand_dna.get("premium_media_enabled", True)

            # 2. Generate Blueprint with channel context
            blueprint = await planner.create_campaign_blueprint(
                goal,
                brand_dna,
                answers,
                selected_channels=target_channels,
                memory_hooks=memory_hooks,
                competitor_insights=competitor_insights
            )
            self._update_progress(uid, campaign_id, "Creative Blueprint Ready.", 30)

            # 2.5 Claims Verification + QC Rubric (copy governance)
            claims_reports = {}
            qc_reports = {}
            claims_policy = brand_dna.get("claims_policy", {})

            def extract_primary_copy(channel_data: dict) -> str:
                if channel_data.get("caption"):
                    return channel_data["caption"]
                if channel_data.get("body"):
                    return channel_data["body"]
                headlines = channel_data.get("headlines") or []
                if headlines:
                    return headlines[0]
                if channel_data.get("headline"):
                    return channel_data["headline"]
                return ""

            for channel in target_channels:
                channel_data = blueprint.get(channel, {})
                channel_claims_reports = []

                for field in ["caption", "body", "headline"]:
                    if isinstance(channel_data.get(field), str):
                        cleaned, report = verify_claims(channel_data[field], claims_policy)
                        channel_data[field] = cleaned
                        channel_claims_reports.append({"field": field, **report})

                if isinstance(channel_data.get("headlines"), list):
                    cleaned_headlines = []
                    for idx, headline in enumerate(channel_data["headlines"]):
                        cleaned, report = verify_claims(headline, claims_policy)
                        cleaned_headlines.append(cleaned)
                        channel_claims_reports.append({"field": f"headlines[{idx}]", **report})
                    channel_data["headlines"] = cleaned_headlines

                blueprint[channel] = channel_data
                claims_reports[channel] = channel_claims_reports

                spec = CHANNEL_SPECS.get(channel, {})
                qc_reports[channel] = evaluate_copy(channel, extract_primary_copy(channel_data), brand_dna, spec)

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
                
                # V3.1: Google Display Ads - Generate ALL formats (Leaderboard, Med Rect, Mobile)
                if channel == 'google_display':
                    for fmt in spec["formats"]:
                        formats_to_generate.append((fmt, fmt['type']))
                        
                elif channel in ['instagram', 'facebook', 'tiktok']:
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
                        
                        # V6.2: Check for cached AI image (from interrupted generation)
                        cached_url = self._get_cached_ai_image(campaign_id, channel, format_label)
                        if cached_url:
                            # Use cached image - skip expensive AI call!
                            async def return_cached(url):
                                return {"url": url}
                            task = return_cached(cached_url)
                        else:
                            # No cache - generate new image
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
                
                # V6.2: CACHE AI IMAGE URL before rendering
                # This is the expensive step (15s) - cache it so resume can skip AI
                format_label = meta.get("format_label", "primary")
                self._save_ai_image_cache(campaign_id, channel, format_label, raw_url)
                
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
                    
                    # V7.0: Use channel-aware layout selection (includes new layouts)
                    from app.core.templates import get_layout_for_channel, LAYOUT_VARIANTS
                    layout_class = get_layout_for_channel(channel)
                    # Extract variant name from CSS class (e.g., 'variant-hero-center' -> 'hero-center')
                    layout_variant = layout_class.replace('variant-', '') if layout_class.startswith('variant-') else 'hero-center'

                    
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
                    
                    # ------------------------------------------------------------------------
                    # V7.1: STRICT VEO PIPELINE - NO FALLBACK VIDEO
                    # ------------------------------------------------------------------------
                    use_veo = ENABLE_VEO_VIDEO and premium_media_allowed and channel in ['tiktok', 'instagram', 'facebook_story']
                    
                    if is_video:
                        asset_url = None
                        
                        if use_veo:
                            # 1. Attempt VEO (Strict Mode)
                            try:
                                logger.info(f"🎬 Generating VEO hybrid video for {channel} ({w}x{h})...")
                                visual_prompt = channel_blueprint.get('visual_prompt', 'Professional brand video')
                                headline = channel_blueprint.get('headline', '')
                                
                                asset_url = await asset_processor.generate_veo_video_asset(
                                    prompt=visual_prompt,
                                    text_content=headline,
                                    logo_url=brand_dna.get('logo_url', ''),
                                    user_id=uid,
                                    asset_id=f"{campaign_id}_{asset_key}",
                                    channel=channel,
                                    brand_dna=brand_dna,
                                    width=w,
                                    height=h
                                )
                                if not asset_url:
                                    logger.warning(f"⚠️ Veo generation returned None. Strict mode: SKIPPING HTML VIDEO FALLBACK.")
                            except Exception as veo_err:
                                logger.warning(f"⚠️ Veo failed: {veo_err}. Strict mode: SKIPPING HTML VIDEO FALLBACK.")
                                asset_url = None
                        
                        else:
                            # 2. Standard HTML Video (Only if Veo wasn't requested)
                            logger.info(f"🎥 Generating HTML video asset for {channel} ({w}x{h})...")
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
                                if asset_url.endswith('.webm'):
                                    meta["compatibility_warning"] = "WebM format - may not play on all mobile devices"
                            else:
                                meta["format_type"] = "image"  # Fallback occurred
                        else:
                            # Both video and fallback failed (or Veo failed strict mode)
                            # Return base64 HTML as a last-resort crash protection
                            logger.warning(f"⚠️ All video rendering options failed for {channel}, using HTML fallback")
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
                    meta["intent"] = intent_object
                    meta["claims_report"] = claims_reports.get(channel)
                    meta["qc_report"] = qc_reports.get(channel)
                    draft_saved = self._save_draft_immediately(
                        uid, campaign_id, goal, channel,
                        assets.get(asset_key) or assets.get(channel),
                        meta, blueprint, creative_intent, claims_report, qc_report
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
                        "creative_intent": creative_intent,
                        "claims_report": claims_report,
                        "qc_report": qc_report,
                        "assets": assets,
                        "assets_metadata": assets_metadata,
                        "selected_channels": target_channels,
                        "goal": goal,
                        "campaign_id": campaign_id,
                        "intent": intent_object,
                        "claims_reports": claims_reports,
                        "qc_reports": qc_reports
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
                "creative_intent": creative_intent,
                "claims_report": claims_report,
                "qc_report": qc_report,
                "assets": assets,
                "assets_metadata": assets_metadata,
                "selected_channels": target_channels,
                "goal": goal,
                "campaign_id": campaign_id,
                "intent": intent_object,
                "claims_reports": claims_reports,
                "qc_reports": qc_reports
            }
            
            # Use set with merge=True to handle new campaign documents correctly
            self.db.collection('users').document(uid).collection('campaigns').document(campaign_id).set(final_data, merge=True)

            self._save_creative_memory(uid, campaign_id, goal, blueprint, creative_intent)
            
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
                            "textCopy": text_copy,
                            "intent": intent_object,
                            "claimsReport": claims_reports.get(channel),
                            "qcReport": qc_reports.get(channel)
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

            # V7.2: Save creative memory for reuse
            self._save_creative_memory(uid, campaign_id, intent_object, blueprint)

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
            "link": f"/campaign-center/{campaign_id}" if percent == 100 else None,  # Navigate to campaign results when complete
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
