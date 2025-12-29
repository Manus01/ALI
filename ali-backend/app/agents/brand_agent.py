import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import json
import logging
from .base_agent import BaseAgent

class BrandAgent(BaseAgent):
    def __init__(self):
        super().__init__("BrandAgent")
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        # Using 1.5 Flash for speed and cost-efficiency during onboarding
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def analyze_business(self, url: str = None, description: str = None, countries: list = []):
        """
        Hybrid Analysis: Crawls a website if a URL is provided, 
        otherwise performs a 'Discovery Interview' based on the description.
        """
        self.log_task(f"Initializing Brand Discovery. URL: {url}, Desc Provided: {bool(description)}")
        
        context_data = ""
        mode = "Discovery"

        try:
            # --- 1. DATA GATHERING ---
            if url:
                mode = "Extraction"
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                response = requests.get(url, headers=headers, timeout=15)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract meta description and top-level text
                meta_desc = soup.find("meta", attrs={"name": "description"})
                meta_text = meta_desc["content"] if meta_desc else ""
                body_text = soup.get_text()[:6000] # Limit to 6k chars
                context_data = f"Website Title: {soup.title.string if soup.title else 'N/A'}\nMeta: {meta_text}\nContent: {body_text}"
            else:
                context_data = f"User Business Description: {description}"

            # --- 2. AI BRAND SYNTHESIS ---
            prompt = f"""
            You are a Senior Brand Director. Perform a Brand DNA study based on the following {mode} data.
            Target Markets: {countries}
            
            {context_data}

            Your goal is to define a cohesive identity that feels 'carefully branded' and culturally relevant.
            Return ONLY a valid JSON object:
            {{
                "brand_name": "string",
                "core_offerings": ["list", "of", "services"],
                "tone_of_voice": "detailed description (e.g., Sophisticated but accessible)",
                "visual_styles": [
                    {{"id": "minimalist", "label": "Minimalist Logic", "desc": "Clean, precise, white-space focused."}},
                    {{"id": "vibrant", "label": "Vibrant Energy", "desc": "High contrast, bold colors, active."}},
                    {{"id": "heritage", "label": "Heritage & Warmth", "desc": "Classic, community-focused, relational."}}
                ],
                "color_palette": {{
                    "primary": "#hex",
                    "secondary": "#hex",
                    "accent": "#hex"
                }},
                "graphic_elements": {{
                    "shapes": "e.g., sharp geometric or soft organic",
                    "line_weight": "e.g., bold or hair-line",
                    "vibe": "e.g., grainy textures, glassmorphism, or flat design"
                }},
                "cultural_nuance": "Specific advice for marketing in {countries}"
            }}
            """

            response = self.model.generate_content(prompt)
            # Standard cleanup for Gemini's markdown wrapper
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(clean_json)

        except Exception as e:
            self.handle_error(e)