import asyncio
import logging
from app.agents.base_agent import BaseAgent
from app.agents.campaign_agent import CampaignAgent
from app.services.video_agent import VideoAgent
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
            # Initialize robust services
            video_agent = VideoAgent()
            image_agent = ImageAgent()
            
            # Determine target platforms
            target_platforms = connected_platforms if connected_platforms else ["instagram", "tiktok"]
            logger.info(f"🎯 Orchestrating for platforms: {target_platforms}")

            tasks = []
            platform_map = {} # To map result back to platform name
            task_index = 0

            # A. Video Generation (TikTok/Reels)
            if any(p in target_platforms for p in ['tiktok', 'youtube_shorts']):
                tiktok_data = blueprint.get('tiktok', {})
                script = tiktok_data.get('video_script', 'Engaging brand content')
                style = tiktok_data.get('audio_style', 'Upbeat')
                
                # Construct a rich prompt for VEO
                prompt = f"Create a high-quality social media video. Script concept: {script}. Vibe: {style}. No text overlays."
                
                # Wrap synchronous agent call in thread for async compatibility
                task = asyncio.to_thread(
                    video_agent.generate_video, 
                    prompt=prompt, 
                    brand_dna=brand_dna, # Pass dict directly (Agent handles stringification if needed, or we stringify here? VideoAgent expects str usually but let's check. VideoAgent brand_dna is `Optional[str]`. We should stringify.)
                    # Let's fix brand_dna type mismatch inline:
                    # VideoAgent.generate_video signature: (prompt: str, reference_image_uri..., brand_dna: str)
                    # We pass formatted string.
                    folder="campaigns"
                )
                # Wait, VideoAgent expects brand_dna as string? Let's format it.
                dna_str = f"Style {brand_dna.get('visual_styles', [])}. Colors {brand_dna.get('color_palette', {})}"
                task = asyncio.to_thread(video_agent.generate_video, prompt, reference_image_uri=None, brand_dna=dna_str, folder="campaigns")
                
                tasks.append(task)
                platform_map[task_index] = 'tiktok'
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

            self._update_progress(uid, campaign_id, "Generating Cinematic Assets...", 60)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks)
            
            # Map results back to structured assets
            assets = {}
            for i, result in enumerate(results):
                key = platform_map.get(i)
                if key and result:
                    assets[key] = result
            
            # 4. Finalize & Package
            
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