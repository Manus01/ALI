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
        
    def fetch_recent_errors(self, hours: int = 24, limit: int = 10) -> List[Any]:
        """ Fetches 'ERROR' severity logs from the last X hours. """
        if not self.logging_client:
            return []
            
        logger.info(f"🔎 Fetching logs for last {hours}h...")
        try:
            time_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
            filter_str = f"severity>=ERROR AND timestamp>=\"{time_threshold.isoformat()}\""
            
            entries = self.logging_client.list_entries(
                filter_=filter_str,
                order_by=DESCENDING,
                page_size=limit
            )
            
            # Simple Deduplication by payload signature
            unique_errors = {}
            for entry in entries:
                # payload can be dict or str
                payload = entry.payload
                sig = str(payload)[:200] # Signature based on first 200 chars
                if sig not in unique_errors:
                    unique_errors[sig] = {
                        "timestamp": entry.timestamp,
                        "payload": payload,
                        "resource": entry.resource.labels if entry.resource else {},
                        "signature": sig
                    }
                    
            return list(unique_errors.values())
        except Exception as e:
            logger.error(f"❌ Log Fetch Failed: {e}")
            return []

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
        except:
             # Fallback to previously initialized tool or empty if unavailable
             search_tool = self.tools[0] if self.tools else None
        
        prompt = f"""
        You are a **Senior Google Cloud Site Reliability Engineer (SRE)**.
        Your expertise lies in distributed systems, Cloud Run, Firestore, Vertex AI, and Python web services.
        
        ### MISSION
        Analyze the following application log error with the depth of a Principal Engineer.
        You must determine if this is a Code, Configuration (IAM/Quota), or Infrastructure issue.

        ### ERROR CONTEXT
        - **Timestamp**: {timestamp}
        - **Raw Log**: {payload}

        ### ANALYSIS PROTOCOL
        1.  **Categorize**: Is this Transient (retryable) or Permanent?
        2.  **Google Cloud Diagnostics**:
            - Could this be an **IAM Permission** issue? (e.g., 403, permission denied)
            - Could this be a **Quota/Limit** issue? (e.g., 429, resource exhausted)
            - Could this be a **Cloud Run** lifecycle issue? (e.g., SIGTERM, memory limit, cold start timeout)
        3.  **Research (Mandatory)**: Use the attached Google Search tool to validate specific error codes or recent GCP outages.
        
        ### OUTPUT FORMAT (JSON)
        {{
            "root_cause": "Technical explanation of WHY it happened (e.g., 'Service Account missing roles/storage.objectCreator')",
            "sre_assessment": "Assessment of impact (e.g., 'Critical failure in asset pipeline').",
            "suggested_fix": "Exact gcloud command, IAM change, or code fix required.",
            "is_transient": true/false,
            "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
            "relevant_gcp_doc": "Link to official Google Cloud documentation."
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
            except:
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

    def run_troubleshooter(self):
        """ Main Orchestrator """
        errors = self.fetch_recent_errors()
        
        if not errors:
            logger.info("✅ No new errors found.")
            return {"status": "clean", "count": 0}

        tasks_created = 0
        for err in errors:
            # Check if we already have a pending task for this error signature
            # to avoid spamming the admin
            sig = err.get('signature')
            existing = db.collection('admin_tasks').where('type', '==', 'error_report').where('error_signature', '==', sig).where('status', '==', 'pending').limit(1).stream()
            if any(existing):
                logger.info(f"⏭️ Skipping duplicate error: {sig[:20]}")
                continue

            # Analyze
            analysis = self.analyze_error(err)
            
            # Report
            task_data = {
                "type": "error_report",
                "status": "pending",
                "title": f"Error: {analysis.get('root_cause', 'Unknown Error')[:50]}",
                "description": analysis.get('suggested_fix'),
                "severity": analysis.get('severity', 'MEDIUM'),
                "error_signature": sig,
                "full_log": str(err.get('payload')),
                "analysis_details": analysis,
                "created_at": firestore.SERVER_TIMESTAMP,
                "source": "TroubleshootingAgent"
            }
            
            try:
                db.collection('admin_tasks').add(task_data)
                tasks_created += 1
                logger.info(f"🚨 Admin Task Created: {task_data['title']}")
            except Exception as e:
                logger.error(f"❌ Failed to save admin task: {e}")

        return {"status": "success", "errors_found": len(errors), "reports_filed": tasks_created}
