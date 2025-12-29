import asyncio
from app.agents.base_agent import BaseAgent
from app.agents.campaign_agent import CampaignAgent
from app.agents.visual_agent import VisualAgent
from firebase_admin import firestore

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Orchestrator")
        self.db = firestore.client()

    async def run_full_campaign_flow(self, uid, campaign_id, goal, brand_dna, answers):
        try:
            # 1. Update Notification: Start
            self._update_progress(uid, campaign_id, "Analyzing Cultural Context...", 10)

            # 2. Generate Blueprint
            planner = CampaignAgent()
            blueprint = await planner.create_campaign_blueprint(goal, brand_dna, answers)
            self._update_progress(uid, campaign_id, "Creative Blueprint Ready.", 30)

            # 3. Parallel Execution: Visuals & Copy
            visualizer = VisualAgent()
            
            # Use asyncio.gather to run TikTok, Instagram, and Email generation at once
            tiktok_task = visualizer.generate_branded_video(blueprint['tiktok'], brand_dna)
            insta_task = visualizer.generate_branded_image(blueprint['instagram'], brand_dna)
            
            self._update_progress(uid, campaign_id, "Generating Cinematic Assets...", 60)
            
            results = await asyncio.gather(tiktok_task, insta_task)
            
            # 4. Finalize & Package
            final_data = {
                "status": "completed",
                "blueprint": blueprint,
                "assets": {
                    "tiktok": results[0],
                    "instagram": results[1]
                }
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