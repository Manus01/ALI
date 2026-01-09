import asyncio
import logging
from app.agents.base_agent import BaseAgent
from app.agents.campaign_agent import CampaignAgent
from app.services.image_agent import ImageAgent
from app.core.security import db
from firebase_admin import firestore

logger = logging.getLogger("ali_platform.agents.orchestrator_agent")

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Orchestrator")
        self.db = db

    async def run_full_campaign_flow(self, uid, campaign_id, goal, brand_dna, answers, connected_platforms: list = None):
        try:
            # 1. Update Notification: Start
            self._update_progress(uid, campaign_id, "Analyzing Cultural Context...", 10)

            # 2. Generate Blueprint
            planner = CampaignAgent()
            blueprint = await planner.create_campaign_blueprint(goal, brand_dna, answers)
            self._update_progress(uid, campaign_id, "Creative Blueprint Ready.", 30)

            # 3. Parallel Execution: Visuals & Copy
            # Initialize robust services - VideoAgent deprecated, using ImageAgent only
            image_agent = ImageAgent()
            
            # Determine target platforms
            target_platforms = connected_platforms if connected_platforms else ["instagram", "google_ads"]
            logger.info(f"🎯 Orchestrating for platforms: {target_platforms}")

            tasks = []
            platform_map = {} # To map result back to platform name
            task_index = 0

            # A. Instagram/Social Image Generation
            if any(p in target_platforms for p in ['instagram', 'facebook', 'tiktok']):
                ig_data = blueprint.get('instagram', {})
                visual_prompt = ig_data.get('visual_prompt', 'Professional brand promotional image')
                
                dna_str = f"Style {brand_dna.get('visual_styles', [])}. Colors {brand_dna.get('color_palette', {})}"
                task = asyncio.to_thread(image_agent.generate_image, visual_prompt, brand_dna=dna_str, folder="campaigns")
                tasks.append(task)
                platform_map[task_index] = 'instagram'
                task_index += 1
            
            # B. Google Display Ads (Landscape Image)
            if any(p in target_platforms for p in ['google_ads', 'google']):
                ig_data = blueprint.get('instagram', {})
                visual_prompt = ig_data.get('visual_prompt', 'Professional product shot')
                
                # Wrap sync call
                dna_str = f"Style {brand_dna.get('visual_styles', [])}"
                task = asyncio.to_thread(image_agent.generate_image, visual_prompt, brand_dna=dna_str, folder="campaigns")
                tasks.append(task)
                platform_map[task_index] = 'google_ads'
                task_index += 1

            self._update_progress(uid, campaign_id, "Generating Visual Assets...", 60)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks)
            
            # Map results back to structured assets
            assets = {}
            for i, result in enumerate(results):
                key = platform_map.get(i)
                if key and result:
                    # Extract URL if dict (new format), else use result (legacy string)
                    if isinstance(result, dict):
                         assets[key] = result.get('url')
                    else:
                         assets[key] = result
            
            # 4. Finalize & Package
            final_data = {
                "status": "completed",
                "blueprint": blueprint,
                "assets": assets,
                "goal": goal,
                "campaign_id": campaign_id
            }
            
            # Use set with merge=True to handle new campaign documents correctly
            self.db.collection('users').document(uid).collection('campaigns').document(campaign_id).set(final_data, merge=True)
            
            # 5. Also save assets to creative_drafts for User Self-Approval (Stage 4)
            for platform_key, asset_url in assets.items():
                if asset_url:
                    draft_id = f"draft_{campaign_id}_{platform_key}"
                    draft_data = {
                        "userId": uid,
                        "campaignId": campaign_id,
                        "platform": platform_key,
                        "thumbnailUrl": asset_url,
                        "title": f"{goal[:50]}..." if len(goal) > 50 else goal,
                        "format": "Image",
                        "status": "DRAFT",
                        "createdAt": firestore.SERVER_TIMESTAMP,
                        "blueprint": blueprint.get(platform_key, blueprint.get('instagram', {}))
                    }
                    self.db.collection('creative_drafts').document(draft_id).set(draft_data)
                    logger.info(f"📦 Saved draft {draft_id} for user {uid}")
            
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