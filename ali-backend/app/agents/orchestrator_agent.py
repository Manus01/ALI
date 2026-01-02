import asyncio
from app.agents.base_agent import BaseAgent
from app.agents.campaign_agent import CampaignAgent
from app.agents.visual_agent import VisualAgent
from app.core.security import db
from firebase_admin import firestore

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
            visualizer = VisualAgent()
            
            # Determine target platforms
            # If no integrations found, we might fallback to what the user answered or a default set
            target_platforms = connected_platforms if connected_platforms else ["instagram", "tiktok"]
            print(f"🎯 Orchestrating for platforms: {target_platforms}")

            tasks = []
            platform_map = {} # To map result back to platform name

            # A. Video Generation (TikTok/Reels)
            if any(p in target_platforms for p in ['tiktok', 'youtube_shorts']):
                task = visualizer.generate_branded_video(blueprint.get('tiktok', {}), brand_dna)
                tasks.append(task)
                platform_map[len(tasks)-1] = 'tiktok'
            
            # C. Google Display Ads (Landscape Image)
            if any(p in target_platforms for p in ['google_ads', 'google']):
                # Reuse the visual hook from Instagram but request landscape
                display_ad_blueprint = blueprint.get('instagram', {}).copy()
                display_ad_blueprint['aspect_ratio'] = "16:9" 
                task = visualizer.generate_branded_image(display_ad_blueprint, brand_dna)
                tasks.append(task)
                platform_map[len(tasks)-1] = 'google_ads'

            self._update_progress(uid, campaign_id, "Generating Cinematic Assets...", 60)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks)
            
            # Map results back to structured assets
            assets = {}
            for i, result in enumerate(results):
                key = platform_map.get(i)
                if key:
                    assets[key] = result
            
            # 4. Finalize & Package
            final_data = {
                "status": "completed",
                "blueprint": blueprint,
                "assets": assets
            }
            
            self.db.collection('users').document(uid).collection('campaigns').document(campaign_id).update(final_data)
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