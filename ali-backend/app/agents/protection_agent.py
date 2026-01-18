"""
Protection Agent
Advanced brand protection: priority actions, deepfake detection, 
platform reporting guidance, and legal evidence reports.
"""
import json
import logging
import hashlib
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent
from app.services.llm_factory import get_model
from app.types.evidence_models import (
    EvidenceSource, EvidenceItem, EvidenceReport, EvidenceExportBundle,
    CollectionMethod, EvidenceType,
    compute_source_hash, compute_item_hash, compute_report_hash,
    verify_chain_integrity, redact_pii
)

logger = logging.getLogger(__name__)


# Platform-specific reporting URLs and instructions
PLATFORM_REPORTING_INFO = {
    "facebook": {
        "name": "Facebook",
        "report_url": "https://www.facebook.com/help/contact/274459462613911",
        "defamation_url": "https://www.facebook.com/help/contact/284186058387966",
        "impersonation_url": "https://www.facebook.com/help/contact/295309487309948",
        "steps": [
            "Navigate to the post or profile you want to report",
            "Click the three dots (⋮) menu in the top right of the post",
            "Select 'Report post' or 'Find support or report'",
            "Choose the reason that best describes the violation",
            "Follow the on-screen prompts to complete your report",
            "Save a screenshot of your report confirmation"
        ]
    },
    "instagram": {
        "name": "Instagram",
        "report_url": "https://help.instagram.com/192435014247952",
        "defamation_url": "https://help.instagram.com/contact/504521742987441",
        "impersonation_url": "https://help.instagram.com/contact/636276399721841",
        "steps": [
            "Go to the post, story, or profile to report",
            "Tap the three dots (⋮) menu",
            "Tap 'Report'",
            "Select the type of issue (spam, harassment, etc.)",
            "Follow additional prompts if needed",
            "Screenshot the confirmation for your records"
        ]
    },
    "twitter": {
        "name": "X (Twitter)",
        "report_url": "https://help.twitter.com/en/forms/safety-and-sensitive-content/abuse",
        "defamation_url": "https://help.twitter.com/en/forms/safety-and-sensitive-content/abuse",
        "impersonation_url": "https://help.twitter.com/en/forms/authenticity/impersonation",
        "steps": [
            "Click the three dots (⋮) on the tweet",
            "Select 'Report Tweet'",
            "Choose 'It's abusive or harmful'",
            "Select the specific reason",
            "Provide additional context if requested",
            "Submit and save your report reference number"
        ]
    },
    "linkedin": {
        "name": "LinkedIn",
        "report_url": "https://www.linkedin.com/help/linkedin/answer/37822",
        "defamation_url": "https://www.linkedin.com/help/linkedin/answer/146",
        "steps": [
            "Click the three dots on the post or profile",
            "Select 'Report this post' or 'Report / Block'",
            "Choose the category of violation",
            "Provide details about the issue",
            "Submit your report"
        ]
    },
    "tiktok": {
        "name": "TikTok",
        "report_url": "https://support.tiktok.com/en/safety-hc/report-a-problem",
        "steps": [
            "Long press on the video or tap the share button",
            "Tap 'Report'",
            "Select the reason for reporting",
            "Provide additional details if needed",
            "Submit and screenshot confirmation"
        ]
    },
    "youtube": {
        "name": "YouTube",
        "report_url": "https://support.google.com/youtube/answer/2802027",
        "defamation_url": "https://support.google.com/youtube/answer/6154230",
        "steps": [
            "Click the three dots under the video",
            "Select 'Report'",
            "Choose the reason (harassment, spam, etc.)",
            "Provide timestamp if needed",
            "Submit your report"
        ]
    }
}


class ProtectionAgent(BaseAgent):
    """
    Agent for advanced brand protection features:
    1. Priority action scoring and dashboard
    2. Deepfake/AI content detection flagging
    3. Platform-specific reporting guidance
    4. Legal evidence report generation
    """
    
    def __init__(self):
        super().__init__("ProtectionAgent")
        self.model = get_model(intent='creative')  # For detailed analysis
    
    async def get_priority_actions(
        self,
        mentions: List[Dict[str, Any]],
        max_items: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Score and rank mentions by urgency to create priority action list.
        
        Priority Score = (Severity × 3) + (Recency × 2) + (Reach × 1)
        
        Returns top N items requiring immediate attention.
        """
        self.log_task(f"Calculating priority scores for {len(mentions)} mentions")
        
        scored_mentions = []
        now = datetime.utcnow()
        
        for mention in mentions:
            # Skip positive mentions
            sentiment = mention.get('sentiment', 'neutral')
            if sentiment == 'positive':
                continue
            
            # Severity component (0-10)
            severity = mention.get('severity', 5 if sentiment == 'negative' else 2)
            
            # Recency component (0-10) - newer = higher
            published = mention.get('published_at')
            if published:
                if isinstance(published, str):
                    try:
                        published = datetime.fromisoformat(published.replace('Z', '+00:00'))
                    except:
                        published = now
                hours_ago = (now - published.replace(tzinfo=None)).total_seconds() / 3600
                recency = max(0, 10 - (hours_ago / 24))  # Decays over 10 days
            else:
                recency = 5  # Unknown age
            
            # Reach component (estimated 0-10)
            source = mention.get('source_type', 'unknown')
            reach_map = {
                'news': 8,
                'social': 6,
                'blog': 5,
                'forum': 4,
                'review': 7,
                'unknown': 3
            }
            reach = reach_map.get(source, 3)
            
            # Calculate priority score
            priority_score = (severity * 3) + (recency * 2) + reach
            
            # Determine action type
            if severity >= 8:
                action_type = "urgent_response"
                action_label = "🚨 Urgent Response Required"
            elif severity >= 6:
                action_type = "respond"
                action_label = "⚠️ Respond Soon"
            elif 'deepfake' in mention.get('title', '').lower() or 'fake' in mention.get('content_snippet', '').lower():
                action_type = "investigate_deepfake"
                action_label = "🔍 Investigate Potential Deepfake"
            else:
                action_type = "monitor"
                action_label = "👁️ Monitor Closely"
            
            scored_mentions.append({
                **mention,
                "priority_score": round(priority_score, 1),
                "priority_rank": 0,  # Will be set after sorting
                "action_type": action_type,
                "action_label": action_label,
                "components": {
                    "severity": severity,
                    "recency": round(recency, 1),
                    "reach": reach
                }
            })
        
        # Sort by priority score (highest first)
        scored_mentions.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Assign ranks
        for i, mention in enumerate(scored_mentions[:max_items]):
            mention['priority_rank'] = i + 1
        
        return scored_mentions[:max_items]
    
    async def detect_potential_deepfake(
        self,
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze content for potential deepfake/AI-generated indicators.
        
        Note: This is heuristic-based. For production, integrate with 
        dedicated APIs like Sensity, Microsoft Video Authenticator, or
        Google Cloud Video Intelligence.
        """
        self.log_task("Analyzing content for deepfake indicators")
        
        title = content.get('title', '').lower()
        description = content.get('content_snippet', '').lower()
        url = content.get('url', '').lower()
        source_type = content.get('source_type', '')
        
        # Heuristic indicators
        indicators = []
        risk_score = 0
        
        # Check for deepfake-related keywords
        deepfake_keywords = ['deepfake', 'ai generated', 'synthetic media', 'fake video', 
                            'manipulated', 'doctored', 'fabricated']
        for keyword in deepfake_keywords:
            if keyword in title or keyword in description:
                indicators.append(f"Contains keyword: '{keyword}'")
                risk_score += 3
        
        # Video content from unknown sources
        if source_type == 'social' and 'video' in (title + description):
            indicators.append("Video content from social media")
            risk_score += 1
        
        # Check for impersonation indicators
        impersonation_keywords = ['fake account', 'impersonator', 'pretending', 'parody']
        for keyword in impersonation_keywords:
            if keyword in title or keyword in description:
                indicators.append(f"Impersonation indicator: '{keyword}'")
                risk_score += 2
        
        # Determine risk level
        if risk_score >= 5:
            risk_level = "high"
            recommendation = "Urgent investigation recommended. Consider using specialized deepfake detection tools."
        elif risk_score >= 2:
            risk_level = "medium"
            recommendation = "Monitor closely and verify authenticity of any media content."
        else:
            risk_level = "low"
            recommendation = "No obvious deepfake indicators detected."
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "indicators": indicators,
            "recommendation": recommendation,
            "verification_tools": [
                {"name": "Google Reverse Image Search", "url": "https://images.google.com"},
                {"name": "TinEye", "url": "https://tineye.com"},
                {"name": "InVID Verification Plugin", "url": "https://www.invid-project.eu/tools-and-services/invid-verification-plugin/"},
                {"name": "FotoForensics", "url": "https://fotoforensics.com"}
            ]
        }
    
    def get_reporting_guidance(
        self,
        platform: str,
        violation_type: str = "defamation"
    ) -> Dict[str, Any]:
        """
        Get platform-specific reporting instructions.
        
        Args:
            platform: facebook, instagram, twitter, linkedin, tiktok, youtube
            violation_type: defamation, impersonation, harassment, spam
        """
        self.log_task(f"Getting reporting guidance for {platform}")
        
        platform_key = platform.lower().replace('x', 'twitter')
        
        if platform_key not in PLATFORM_REPORTING_INFO:
            return {
                "error": f"Platform '{platform}' not found",
                "available_platforms": list(PLATFORM_REPORTING_INFO.keys())
            }
        
        info = PLATFORM_REPORTING_INFO[platform_key]
        
        # Get appropriate URL based on violation type
        if violation_type == "defamation" and "defamation_url" in info:
            report_url = info["defamation_url"]
        elif violation_type == "impersonation" and "impersonation_url" in info:
            report_url = info["impersonation_url"]
        else:
            report_url = info["report_url"]
        
        return {
            "platform": info["name"],
            "violation_type": violation_type,
            "report_url": report_url,
            "steps": info["steps"],
            "additional_tips": [
                "Take screenshots before the content is removed",
                "Record the date and time you first saw the content",
                "Save the URL of the offending content",
                "Document any impacts on your reputation or business",
                "If serious, consult with a legal professional"
            ]
        }
    
    async def generate_evidence_report(
        self,
        mentions: List[Dict[str, Any]],
        brand_name: str,
        report_purpose: str = "legal",  # "legal", "police", "platform"
        user_id: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a formal evidence report with tamper-evident hash chain.
        
        This enhanced version provides:
        - Full source traceability for every claim
        - SHA-256 hash chain (source -> item -> report)
        - PII redaction for privacy compliance
        - Chain integrity verification
        
        Args:
            mentions: List of mention dictionaries to include as evidence
            brand_name: The brand/entity subject of the report
            report_purpose: "legal", "police", or "platform"
            user_id: The user generating the report (for audit trail)
        
        Returns:
            Complete EvidenceReport as dictionary with chain_valid status
        """
        self.log_task(f"Generating {report_purpose} evidence report for {len(mentions)} items with evidence chain")
        
        # Generate unique report ID
        report_id = f"RPT-{hashlib.sha256(f'{brand_name}-{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:10].upper()}"
        now = datetime.utcnow()
        
        # Build evidence items with sources
        evidence_items = []
        legacy_evidence_items = []  # For backward compatibility
        
        for i, mention in enumerate(mentions):
            item_id = str(uuid.uuid4())
            
            # Create source from the mention
            collected_at = now.isoformat()
            raw_snippet = mention.get('content_snippet', '') or mention.get('description', '') or ''
            url = mention.get('url', '')
            
            # Check for and fetch deepfake analysis if linked
            deepfake_analysis_id = mention.get('deepfake_analysis_id')
            deepfake_analysis = None
            
            if deepfake_analysis_id and user_id:
                try:
                    deepfake_analysis = await self._fetch_deepfake_summary(user_id, deepfake_analysis_id)
                except Exception as e:
                    logger.warning(f"Failed to fetch deepfake analysis {deepfake_analysis_id}: {e}")
            
            # Compute source hash (includes stable deepfake fields if present)
            source_hash = compute_source_hash(
                raw_snippet, url, collected_at,
                deepfake_summary=deepfake_analysis
            )
            
            # Create the evidence source
            source = {
                "id": str(uuid.uuid4()),
                "item_id": item_id,
                "platform": mention.get('source_platform', mention.get('source_type', 'web')),
                "url": url,
                "collected_at": collected_at,
                "raw_snippet": raw_snippet[:500] if raw_snippet else "",
                "redacted_snippet": redact_pii(raw_snippet[:500]) if raw_snippet else "",
                "media_refs": [],
                "screenshot_ref": None,
                "method": "automated_scan",
                "source_hash": source_hash,
                "deepfake_analysis_id": deepfake_analysis_id,
                "deepfake_analysis": deepfake_analysis
            }
            
            # Determine evidence type from mention characteristics
            sentiment = mention.get('sentiment', 'neutral')
            severity = mention.get('severity', 5)
            title_lower = mention.get('title', '').lower()
            
            if 'deepfake' in title_lower or 'fake video' in title_lower:
                evidence_type = "deepfake"
            elif 'impersona' in title_lower:
                evidence_type = "impersonation"
            elif severity >= 7 and sentiment == 'negative':
                evidence_type = "defamation"
            elif sentiment == 'negative':
                evidence_type = "violation"
            else:
                evidence_type = "mention"
            
            # Build claim text
            claim_text = mention.get('ai_summary', '') or mention.get('title', '') or f"Evidence item #{i+1}"
            
            # Compute item hash
            source_hashes = [source_hash]
            item_hash = compute_item_hash(claim_text, source_hashes)
            
            # Create evidence item
            evidence_item = {
                "id": item_id,
                "report_id": report_id,
                "type": evidence_type,
                "claim_text": claim_text,
                "severity": severity if isinstance(severity, int) else 5,
                "sources": [source],
                "item_hash": item_hash
            }
            evidence_items.append(evidence_item)
            
            # Legacy format for backward compatibility
            legacy_evidence_items.append({
                "exhibit_number": f"EX-{i+1:03d}",
                "title": mention.get('title', 'Untitled'),
                "url": url,
                "source": mention.get('source_type', 'Unknown'),
                "platform": mention.get('source_platform', 'Unknown'),
                "published_date": mention.get('published_at', 'Unknown'),
                "captured_date": collected_at,
                "sentiment": sentiment,
                "severity": severity,
                "content_excerpt": (raw_snippet[:300] + '...') if raw_snippet else 'N/A'
            })
        
        # Compute report hash from all item hashes
        item_hashes = [item['item_hash'] for item in evidence_items]
        report_hash = compute_report_hash(item_hashes)
        
        # Use AI to generate analysis
        prompt = f"""Generate a professional evidence report summary for potential legal/police filing.

SUBJECT: {brand_name}
EVIDENCE COUNT: {len(mentions)} documented incidents
PURPOSE: {report_purpose} filing

KEY INCIDENTS:
{json.dumps(legacy_evidence_items[:5], indent=2)}

Generate:
1. Executive summary (2-3 sentences)
2. Pattern analysis (what type of attacks/defamation)
3. Potential legal violations (general categories, not legal advice)
4. Recommended next steps

Return ONLY valid JSON:
{{
    "executive_summary": "...",
    "pattern_analysis": "...",
    "potential_violations": ["...", "..."],
    "recommended_actions": ["...", "..."]
}}
"""
        
        try:
            response = await self.model.generate_content_async(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            analysis = json.loads(clean_json)
        except Exception as e:
            logger.error(f"❌ Report analysis failed: {e}")
            analysis = {
                "executive_summary": f"Evidence report documenting {len(mentions)} incidents affecting {brand_name}.",
                "pattern_analysis": "Manual review required.",
                "potential_violations": ["Defamation", "Harassment"],
                "recommended_actions": ["Consult legal professional", "File platform reports"]
            }
        
        # Legal disclaimer
        legal_disclaimer = """IMPORTANT DISCLAIMER:
This report is generated for informational purposes only and does not constitute 
legal advice. The information contained herein should be verified independently. 
Before taking any legal action, please consult with a qualified attorney in your 
jurisdiction. The timestamps and URLs provided should be verified, and original 
copies of all evidence should be preserved through proper forensic methods.

CHAIN OF CUSTODY:
This report includes cryptographic hashes (SHA-256) that enable verification of 
data integrity. Any modification to the source data, claims, or report will 
invalidate the corresponding hashes, allowing detection of tampering."""

        # Build complete report structure
        report = {
            # Core identification
            "id": report_id,
            "report_id": report_id,  # Alias for backward compatibility
            "created_at": now.isoformat(),
            "brand_id": user_id,
            "time_range": {
                "start": (now.replace(day=1)).isoformat(),
                "end": now.isoformat()
            },
            "version": 1,
            "generated_by": "ali_protection_agent",
            "report_purpose": report_purpose,
            "report_type": report_purpose,  # Alias for backward compatibility
            
            # AI-generated summaries
            "executive_summary": analysis.get("executive_summary", ""),
            "pattern_analysis": analysis.get("pattern_analysis", ""),
            "potential_legal_violations": analysis.get("potential_violations", []),
            "recommended_next_steps": analysis.get("recommended_actions", []),
            
            # Subject and counts
            "subject": brand_name,
            "total_incidents": len(mentions),
            
            # Evidence chain (NEW)
            "items": evidence_items,
            
            # Integrity (NEW)
            "report_hash": report_hash,
            "hash_algorithm": "SHA-256",
            
            # Legacy format for backward compatibility
            "analysis": analysis,
            "evidence_items": legacy_evidence_items,
            
            # Legal
            "legal_disclaimer": legal_disclaimer,
            
            # Next steps by purpose
            "next_steps": {
                "for_police": [
                    "Print this report and bring to your local police station",
                    "Request to file a formal complaint",
                    "Provide original screenshots as additional evidence",
                    "Request a case number for your records"
                ],
                "for_legal": [
                    "Share this report with your attorney",
                    "Preserve all original evidence (screenshots, recordings)",
                    "Document any financial or reputational damages",
                    "Consider sending a cease and desist letter"
                ],
                "for_platform": [
                    "Use this report as reference when filing platform reports",
                    "Submit reports to each platform individually",
                    "Follow up if content is not removed within their stated timeframe"
                ]
            },
            
            # Export tracking
            "export_history": []
        }
        
        # Verify chain integrity before returning
        verification = verify_chain_integrity(report)
        report["chain_valid"] = verification["valid"]
        report["chain_verified_at"] = verification["verified_at"]
        
        if not verification["valid"]:
            logger.warning(f"⚠️ Chain integrity issues: {verification['errors']}")
        else:
            logger.info(f"✅ Evidence chain verified for report {report_id}")
        
        return report

    async def _fetch_deepfake_summary(self, user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch deepfake analysis and extract stable summary fields for embedding.
        
        Only returns data for completed analyses to ensure hash stability.
        
        Args:
            user_id: The user ID who owns the analysis
            job_id: The deepfake job ID (e.g., DFA-XXXXXX)
        
        Returns:
            Dict with stable fields if completed, None otherwise
        """
        try:
            from firebase_admin import firestore
            db = firestore.client()
            
            job_ref = db.collection('users').document(user_id).collection('deepfake_jobs').document(job_id)
            doc = job_ref.get()
            
            if not doc.exists:
                logger.debug(f"Deepfake job {job_id} not found for user {user_id}")
                return None
            
            job = doc.to_dict()
            
            # Only include completed analyses to ensure hash stability
            if job.get('status') != 'completed':
                logger.debug(f"Deepfake job {job_id} not completed (status: {job.get('status')})")
                return None
            
            # Extract top 2 signals for display (more can be viewed in full analysis)
            signals = job.get('signals', [])[:2]
            
            # Build stable summary
            completed_at = job.get('completed_at')
            if hasattr(completed_at, 'isoformat'):
                completed_at = completed_at.isoformat()
            
            return {
                "id": job_id,
                "verdict": job.get('verdict'),
                "verdict_label": job.get('verdict_label'),
                "confidence": job.get('confidence'),
                "completed_at": completed_at,
                "signals": signals,
                "user_explanation": job.get('user_explanation')
            }
            
        except Exception as e:
            logger.error(f"Error fetching deepfake summary {job_id}: {e}")
            return None

