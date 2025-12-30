import requests
from bs4 import BeautifulSoup
import os
import json
import logging
from .base_agent import BaseAgent
from app.services.llm_factory import get_gemini_model

class BrandAgent(BaseAgent):
    def __init__(self):
        super().__init__("BrandAgent")
        # Using 1.5 Flash for rapid identity extraction
        self.model = get_gemini_model('gemini-1.5-flash')

    async def analyze_business(self, url: str = None, description: str = None, countries: list = []):
        """
        Stealth Hybrid Analysis: Crawls a website using real-browser headers 
        or falls back to a text-based discovery interview.
        """
        self.log_task(f"Starting discovery. Mode: {'URL' if url else 'Description'}")
        
        context_data = ""
        mode_label = "Extraction" if url else "Discovery"

        try:
            # --- 1. DATA GATHERING WITH STEALTH HEADERS ---
            if url:
                # 🛡️ STEALTH HEADERS: Mimicking a modern Chrome browser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code != 200:
                    self.log_task(f"Warning: Site returned status {response.status_code}. Using fallback logic.")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Strip noise
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()
                
                meta_desc = soup.find("meta", attrs={"name": "description"})
                meta_text = meta_desc["content"] if meta_desc else ""
                title = soup.title.string if soup.title else "Unknown"
                body_text = soup.get_text()[:6000] 
                
                context_data = f"Website Title: {title}\nMeta: {meta_text}\nContent: {body_text}"
            else:
                context_data = f"Business Description: {description}"

            # --- 2. AI BRAND SYNTHESIS ---
            prompt = f"""
            You are a Senior Brand Director. Perform a Brand DNA study for a business targeting {countries}.
            Source Type: {mode_label}
            INPUT DATA: {context_data}

            Return ONLY a valid JSON object:
            {{
                "brand_name": "string",
                "offerings": ["list"],
                "tone": "description",
                "visual_styles": [
                    {{"id": "minimalist", "label": "Minimalist", "desc": "Clean aesthetic"}},
                    {{"id": "bold", "label": "Bold", "desc": "High impact"}},
                    {{"id": "warm", "label": "Warm", "desc": "Community focused"}}
                ],
                "color_palette": {{
                    "primary": "#HEX",
                    "secondary": "#HEX",
                    "accent": "#HEX"
                }},
                "graphic_elements": {{
                    "shapes": "string",
                    "line_weight": "string",
                    "vibe": "string"
                }},
                "cultural_nuance": "Marketing advice for {countries}"
            }}
            """

            response = self.model.generate_content(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(clean_json)

        except Exception as e:
            self.log_task(f"CRITICAL AGENT ERROR: {str(e)}")
            # 🛡️ FALLBACK: Return structured data so the Frontend/CORS doesn't break
            return {
                "brand_name": "My Brand",
                "offerings": ["Premium Services"],
                "tone": "Professional",
                "visual_styles": [
                    {"id": "minimalist", "label": "Modern Professional", "desc": "A clean, standard professional look."}
                ],
                "color_palette": {"primary": "#3B82F6", "secondary": "#1E293B", "accent": "#6366F1"},
                "graphic_elements": {"shapes": "clean", "line_weight": "normal", "vibe": "modern"},
                "cultural_nuance": "Focus on quality and reliability."
            }