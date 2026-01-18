"""
Alerts Parser Service
Parses Google Alerts and Talkwalker Alerts emails to extract mentions.
"""
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from email import message_from_string
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Simple HTML to text converter."""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_link = False
        self.current_href = None
        self.links = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.in_link = True
            for attr, value in attrs:
                if attr == 'href':
                    self.current_href = value
    
    def handle_endtag(self, tag):
        if tag == 'a':
            self.in_link = False
            self.current_href = None
    
    def handle_data(self, data):
        text = data.strip()
        if text:
            self.text_parts.append(text)
            if self.in_link and self.current_href:
                self.links.append({
                    "text": text,
                    "url": self.current_href
                })
    
    def get_text(self) -> str:
        return ' '.join(self.text_parts)
    
    def get_links(self) -> List[Dict[str, str]]:
        return self.links


class AlertsParser:
    """
    Parser for Google Alerts and similar alert email services.
    
    Google Alerts emails contain:
    - Subject: "Google Alert - {keyword}"
    - Body: HTML with links to matching articles
    
    Set up: Create alert at google.com/alerts, set delivery to email.
    """
    
    # Pattern to match Google Alert subjects
    GOOGLE_ALERT_PATTERN = re.compile(r'Google Alert[s]?\s*[-–]\s*(.+)', re.IGNORECASE)
    
    # Pattern to extract URLs from Google redirect links
    GOOGLE_URL_PATTERN = re.compile(r'url=([^&]+)')
    
    def parse_google_alert_email(
        self,
        email_content: str
    ) -> Dict[str, Any]:
        """
        Parse a Google Alert email and extract mentions.
        
        Args:
            email_content: Raw email content (headers + body)
            
        Returns:
            Dict with keyword and list of mentions
        """
        try:
            msg = message_from_string(email_content)
            
            # Extract keyword from subject
            subject = msg.get('Subject', '')
            keyword_match = self.GOOGLE_ALERT_PATTERN.search(subject)
            keyword = keyword_match.group(1).strip() if keyword_match else "Unknown"
            
            # Get email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/html':
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    elif part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Parse HTML body
            mentions = self._extract_mentions_from_html(body, keyword)
            
            logger.info(f"📧 Parsed Google Alert for '{keyword}': {len(mentions)} mentions")
            
            return {
                "keyword": keyword,
                "source": "google_alerts",
                "received_at": msg.get('Date', datetime.utcnow().isoformat()),
                "mentions": mentions
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to parse Google Alert: {e}")
            return {"keyword": "", "source": "google_alerts", "mentions": []}
    
    def _extract_mentions_from_html(
        self,
        html_body: str,
        keyword: str
    ) -> List[Dict[str, Any]]:
        """Extract mentions from Google Alert HTML body."""
        mentions = []
        
        # Parse HTML to get links
        parser = HTMLTextExtractor()
        parser.feed(html_body)
        links = parser.get_links()
        
        for link in links:
            url = link.get("url", "")
            text = link.get("text", "")
            
            # Skip Google's own links
            if "google.com" in url.lower() and "url=" not in url:
                continue
            
            # Extract real URL from Google redirect
            if "google.com/url" in url:
                match = self.GOOGLE_URL_PATTERN.search(url)
                if match:
                    from urllib.parse import unquote
                    url = unquote(match.group(1))
            
            # Skip if no valid URL
            if not url or not url.startswith('http'):
                continue
            
            mentions.append({
                "id": url,
                "title": text,
                "url": url,
                "source": "google_alerts",
                "source_type": "alert",
                "source_name": "Google Alerts",
                "source_icon": "🔔",
                "keyword": keyword,
                "content": text,
                "description": text,
                "published_at": datetime.utcnow().isoformat(),
                "is_alert": True
            })
        
        return mentions
    
    def parse_raw_alert_data(
        self,
        alerts_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Parse pre-extracted alert data (e.g., from webhook or API).
        
        Args:
            alerts_data: List of alert objects with url, title, source fields
            
        Returns:
            Normalized list of mentions
        """
        mentions = []
        
        for alert in alerts_data:
            mentions.append({
                "id": alert.get("url", ""),
                "title": alert.get("title", ""),
                "url": alert.get("url", ""),
                "source": "google_alerts",
                "source_type": "alert",
                "source_name": alert.get("source", "Google Alerts"),
                "source_icon": "🔔",
                "keyword": alert.get("keyword", ""),
                "content": alert.get("snippet", alert.get("title", "")),
                "description": alert.get("snippet", ""),
                "published_at": alert.get("published_at", datetime.utcnow().isoformat()),
                "is_alert": True
            })
        
        return mentions


# Singleton instance
_parser: Optional[AlertsParser] = None


def get_alerts_parser() -> AlertsParser:
    """Get or create singleton alerts parser."""
    global _parser
    if _parser is None:
        _parser = AlertsParser()
    return _parser
