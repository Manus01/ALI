import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import json
from .base_agent import BaseAgent

class BrandAgent(BaseAgent):
    def __init__(self):
        super().__init__("BrandAgent")
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def analyze_business(self, url: str, target_countries: list):
        self.log_task(f"Crawling {url} for audience: {target_countries}")
        try:
            # 1. Fetch Website Data
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract meta tags and body text
            meta_desc = soup.find("meta", attrs={"name": "description"})
            desc_text = meta_desc["content"] if meta_desc else ""
            body_text = soup.get_text()[:6000] # First 6k chars for Gemini

            # 2. Analyze with Cultural Nuance
            prompt = f"""
            You are a Senior Brand Strategist. Based on the website text below and the target countries {target_countries}, 
            define the Brand DNA.
            
            URL: {url}
            Description: {desc_text}
            Content: {body_text}

            Return ONLY a JSON object:
            {{
                "brand_name": "string",
                "offerings": ["product1", "product2"],
                "tone": "detailed description of brand voice",
                "visual_styles": [
                    {{"id": "minimalist", "label": "Precision & Logic", "desc": "Great for German markets"}},
                    {{"id": "warm", "label": "Community & Relation", "desc": "Great for Cypriot markets"}},
                    {{"id": "bold", "label": "High-Impact Energy", "desc": "Universal appeal"}}
                ],
                "cultural_advice": "How to adjust marketing for these countries",
                "extracted_colors": ["#hex1", "#hex2"]
            }}
            """

            response = self.model.generate_content(prompt)
            # Remove potential markdown formatting from Gemini
            cleaned_json = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(cleaned_json)
        except Exception as e:
            self.handle_error(e)