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
        # Using 1.5 Flash for rapid identity extraction
        self.model = genai.GenerativeModel('gemini-1.5-flash')

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
                # 🛡️ STEALTH HEADERS: Mimicking a modern Chrome browser on Windows
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                
                # Check for blocking errors (403, 401)
                if response.status_code != 200:
                    self.log_task(f"Warning: Site returned status {response.status_code}. AI will rely on metadata if available.")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract meta description and body
                meta_desc = soup.find("meta", attrs={"name": "description"})
                meta_text = meta_desc["content"] if meta_desc else ""
                title = soup.title.string if soup.title else "Unknown"
                
                # Strip excess tags to keep context window focused on content
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()
                
                body_text = soup.get_text()[:6000] # First 6k chars is plenty for DNA
                context_data = f"Website Title: {title}\nMeta: {meta_text}\nContent: {body_text}"
            else:
                context_data = f"Business Description Provided by User: {description}"

            # --- 2. AI BRAND SYNTHESIS ---
            prompt = f"""
            You are a Senior Brand Director. Perform a Brand DNA study for a business targeting {countries}.
            Source Type: {mode_label}
            
            INPUT DATA:
            {context_data}

            IDENTITY REQUIREMENTS:
            1. Define a cohesive 'Brand Identity JSON'.
            2. Suggest 3 distinct visual styles (id, label, desc).
            3. Extract or suggest a palette (primary, secondary, accent) in HEX.
            4. Suggest graphic elements (shapes, line weights, vibe).

            Return ONLY valid JSON:
            {{
                "brand_name": "string",
                "offerings": ["list"],
                "tone": "description",
                "visual_styles": [
                    {{"id": "minimalist", "label": "Minimalist", "desc": "description"}},
                    {{"id": "bold", "label": "Bold", "desc": "description"}},
                    {{"id": "warm", "label": "Warm", "desc": "description"}}
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
                "cultural_nuance": "Advice for {countries}"
            }}
            """

            response = self.model.generate_content(prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(clean_json)

        except Exception as e:
            self.handle_error(e)
            return {"error": "Failed to analyze brand. Please provide a business description instead."}