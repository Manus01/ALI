import os
import datetime
import logging
from typing import List, Dict, Any
try:
    from google.cloud import logging as cloud_logging
    from google.cloud.logging import DESCENDING
except ImportError:
    import logging
    cloud_logging = None # Graceful fallback for non-GCP envs
    DESCENDING = "DESCENDING" # Mock constant
from vertexai.generative_models import Tool
from app.services.llm_factory import get_model
from app.core.security import db
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Configure Logger
logger = logging.getLogger("ali_platform.agents.troubleshooting_agent")

class TroubleshootingAgent:
    """
    Autonomous agent that monitors backend logs, researches errors using AI + Web Search,
    and files actionable reports for Admins.
    """
    
    def __init__(self):
        # Initialize Cloud Logging Client
        try:
            self.logging_client = cloud_logging.Client()
            logger.info("✅ Cloud Logging Client Initialized")
        except Exception as e:
            logger.warning(f"⚠️ Cloud Logging Init Failed: {e}. Agent will run in mock mode if tested locally.")
            self.logging_client = None

        # Tools: Google Search Grounding
        try:
            from vertexai.generative_models import GoogleSearchRetrieval
            # Ensure we are not passing unexpected args if SDK differs, but typically it takes no required args or 'disable_attribution'
            gsr = GoogleSearchRetrieval(disable_attribution=False)
            self.tools = [Tool.from_google_search_retrieval(gsr)]
            logger.info("✅ Google Search Grounding Configured")
        except ImportError:
            # Fallback for older SDKs or Preview
            try:
                from vertexai.preview.generative_models import GoogleSearchRetrieval
                gsr = GoogleSearchRetrieval(disable_attribution=False)
                self.tools = [Tool.from_google_search_retrieval(gsr)]
            except:
                logger.warning("⚠️ Google Search Retrieval tool could not be initialized. Web research disabled.")
                self.tools = []
        
    def fetch_combined_telemetry(self, hours: int = 1, limit: int = 20) -> List[Any]:
        """ 
        The Watchdog Eye: Fetches Backend Logs, Frontend Logs, and Admin Alerts.
        Defaults to last 1 hour for high-frequency monitoring.
        """
        combined = []
        # Use timezone-aware UTC
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
        
        # 1. Frontend Logs (client_logs)
        try:
            logs_ref = db.collection("client_logs")\
                         .where(filter=FieldFilter("timestamp", ">=", cutoff.isoformat()))\
                         .where(filter=FieldFilter("level", "==", "error"))\
                         .limit(limit).stream()
            for doc in logs_ref:
                d = doc.to_dict()
                combined.append({
                    "timestamp": d.get("timestamp"),
                    "payload": f"📱 [FRONTEND] {d.get('message')} @ {d.get('component')}\nStack: {d.get('stack_trace')[:200]}",
                    "source": "frontend",
                    "signature": f"client_{doc.id}"
                })
        except Exception as e:
            logger.warning(f"⚠️ Watchdog: Frontend log fetch failed: {e}")

        # 2. Admin Alerts - DEPRECATED / REMOVED
        # Integration errors are now logged to standard backend logs and picked up there.

        # 3. Admin Tasks (Tutorial Generation Failures)
        # These are created by tutorial_agent.py when failures occur
        try:
            failure_types = ['system_failure', 'generation_blocked', 'content_alert']
            for failure_type in failure_types:
                tasks_ref = db.collection("admin_tasks")\
                              .where(filter=FieldFilter("type", "==", failure_type))\
                              .where(filter=FieldFilter("status", "==", "pending"))\
                              .limit(limit).stream()
                for doc in tasks_ref:
                    d = doc.to_dict()
                    # Build informative payload based on type
                    if failure_type == 'system_failure':
                        payload = f"💥 [SYSTEM_FAILURE] Tutorial '{d.get('context', {}).get('topic', 'Unknown')}' failed: {d.get('error', 'Unknown error')}"
                    elif failure_type == 'generation_blocked':
                        failed_blocks = d.get('failed_blocks', [])
                        block_summary = ', '.join([fb.get('original_type', 'unknown') for fb in failed_blocks[:3]])
                        payload = f"🚫 [GENERATION_BLOCKED] Tutorial '{d.get('tutorial_topic', 'Unknown')}' blocked. Failed assets: {block_summary}"
                    else:  # content_alert
                        alerts_count = len(d.get('alerts', []))
                        payload = f"⚠️ [CONTENT_ALERT] Tutorial '{d.get('tutorial_title', 'Unknown')}' has {alerts_count} generation warnings"
                    
                    combined.append({
                        "timestamp": d.get("created_at"),
                        "payload": payload,
                        "source": "admin_task",
                        "signature": f"task_{doc.id}",
                        "task_id": doc.id,
                        "severity": d.get("severity", "MEDIUM")
                    })
        except Exception as e:
            logger.warning(f"⚠️ Watchdog: Admin tasks fetch failed: {e}")

        # 4. Cloud Logging (Backend)
        if self.logging_client:
            try:
                time_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
                # Filter for ERRORs
                filter_str = f"severity>=ERROR AND timestamp>=\"{time_threshold.isoformat()}\""
                entries = self.logging_client.list_entries(filter_=filter_str, order_by=DESCENDING, page_size=limit)
                
                unique_back = set()
                for entry in entries:
                     sig = str(entry.payload)[:200]
                     if sig not in unique_back:
                         combined.append({
                             "timestamp": entry.timestamp,
                             "payload": f"⚙️ [BACKEND] {entry.payload}",
                             "source": "backend_infra",
                             "signature": sig
                         })
                         unique_back.add(sig)
            except Exception as e:
                logger.error(f"⚠️ Watchdog: Backend log fetch failed: {e}")

        return combined

    def monitor_system_health(self):
        """ The Watchdog Loop: Runs continuously (via scheduler) to analyze health. """
        events = self.fetch_combined_telemetry(hours=1)
        
        if not events:
            # Silence is golden, but maybe log a heartbeat?
            return {"status": "healthy", "scanned_events": 0}

        tasks_created = 0
        logger.info(f"🐕 Watchdog: Analyzing {len(events)} anomalous events...")
        
        for event in events:
            # Check for existing pending task to dedupe
            sig = event.get('signature')
            exists = db.collection('admin_tasks').where(filter=FieldFilter('type', '==', 'error_report')).where(filter=FieldFilter('error_signature', '==', sig)).where(filter=FieldFilter('status', '==', 'pending')).limit(1).get()
            if len(exists) > 0: continue

            # Analyze
            analysis = self.analyze_error(event)
            
            # File Report
            db.collection("admin_tasks").add({
                 "type": "error_report",
                 "status": "pending",
                 "title": f"Watchdog: {analysis.get('root_cause', 'Unknown Issue')[:60]}",
                 "description": analysis.get("suggested_fix"),
                 "severity": analysis.get("severity", "MEDIUM"),
                 "error_signature": sig,
                 "raw_log": event.get("payload"),
                 "sre_analysis": analysis,
                 "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            tasks_created += 1
            
        return {"status": "anomalies_detected", "new_reports": tasks_created}

    def analyze_error(self, error_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Uses Gemini (with Search Grounding) to research the error.
        """
        payload = error_entry.get('payload')
        timestamp = error_entry.get('timestamp')
        
        logger.info(f"🧠 Analyzing Error: {str(payload)[:50]}...")
        
        model = get_model(intent='complex')
        
        # We create the tool for this specific call to ensure clean state
        try:
            from vertexai.generative_models import GoogleSearchRetrieval
            gsr = GoogleSearchRetrieval(disable_attribution=False)
            search_tool = Tool.from_google_search_retrieval(gsr)
        except Exception as e:
             logger.warning(f"Google Search Tool Init Failed: {e}")
             # Fallback to previously initialized tool or empty if unavailable
             search_tool = self.tools[0] if self.tools else None
        
        prompt = f"""
        You are a **Principal Debugging Engineer** at a tech company, specializing in both Google Cloud infrastructure (Cloud Run, Firestore, Vertex AI) and React/Python full-stack development.
        
        Your sole purpose is to analyze application errors and provide the simplest, most actionable fix.
        You prioritize **copy-pasteable code snippets** and **shell commands** over lengthy explanations.
        Keep your analysis concise. If you can fix it in one line, do so.
        
        Use the attached Google Search tool to validate error codes, library issues, or GCP outages.

        ### ERROR CONTEXT
        - **Timestamp**: {timestamp}
        - **Raw Log**: {payload}

        ### YOUR TASK
        1.  Identify WHAT failed.
        2.  Determine if it is **Transient** (retry will fix) or **Permanent** (code/config change needed).
        3.  Provide the **exact fix**. This is the most important part.

        ### OUTPUT FORMAT (JSON)
        {{
            "root_cause": "One-sentence explanation of the failure.",
            "impact": "Who/what is blocked by this error?",
            "suggested_fix": "THE MOST IMPORTANT FIELD. Provide the exact code change or shell command. Example: 'In AdminPage.jsx line 45, change `data.id` to `data?.id`'.",
            "is_transient": true/false,
            "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
        }}
        """
        
        try:
            # Generate with Search Grounding
            response = model.generate_content(
                prompt,
                tools=[search_tool]
            )
            
            # Parsing logic (using our standard helper if available, or local logic)
            text = response.text
            import json
            import re
            
            try:
                clean_text = text.replace("```json", "").replace("```", "").strip()
                analysis = json.loads(clean_text)
            except Exception as e:
                logger.warning(f"JSON Parsing failed: {e}")
                match = re.search(r'(\{.*\})', text, re.DOTALL)
                if match:
                    analysis = json.loads(match.group(1))
                else:
                    analysis = {"root_cause": "AI Analysis Failed", "suggested_fix": text}
            
            return analysis
            
        except Exception as e:
            logger.warning(f"⚠️ Analysis Failed: {e}")
            return {
                "root_cause": "Analysis Engine Failure",
                "suggested_fix": "Check AI quotas.",
                "technical_details": str(e)
            }

    # DEPRECATED: Old Manual Trigger (Refactored to monitor_system_health)
    def run_troubleshooter(self):
        return self.monitor_system_health()
