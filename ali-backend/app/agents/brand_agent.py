import requests
from bs4 import BeautifulSoup
import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any

from .base_agent import BaseAgent
from app.services.llm_factory import get_model
from app.services.brand_analysis_service import (
    get_brand_analysis_service,
    BrandAnalysisService
)

logger = logging.getLogger(__name__)


class BrandAgent(BaseAgent):
    """
    Brand DNA Agent v2.0
    
    Orchestrates brand identity extraction and generation using the
    BrandAnalysisService. Supports:
    - Website URL crawling
    - Text-based description analysis  
    - PDF brand guidelines extraction
    - "Senior Designer" fallback logic
    """
    
    def __init__(self):
        super().__init__("BrandAgent")
        # Using 1.5 Flash for rapid identity extraction
        self.model = get_model(intent='fast')
        self.analysis_service: BrandAnalysisService = get_brand_analysis_service()
    
    async def analyze_business(
        self, 
        url: str = None, 
        description: str = None, 
        countries: list = None,
        pdf_bytes: bytes = None,
        brand_vibe: str = "minimalist",
        industry: str = None
    ) -> Dict[str, Any]:
        """
        Hybrid Brand Analysis with multiple input modes.
        
        Priority order:
        1. PDF brand guidelines (if provided)
        2. Website URL crawling
        3. Text description analysis
        4. Pure generative fallback (Senior Designer mode)
        
        Args:
            url: Website URL to crawl
            description: Text description of the business
            countries: Target markets for cultural nuance
            pdf_bytes: Uploaded PDF brand guidelines
            brand_vibe: Selected brand aesthetic 
            industry: Business industry for color psychology
            
        Returns:
            Complete BrandDNA dictionary (never has null fields)
        """
        countries = countries or []
        self.log_task(f"Starting discovery. Vibe: {brand_vibe}, Inputs: URL={bool(url)}, Desc={bool(description)}, PDF={bool(pdf_bytes)}")
        
        # --- MODE A: PDF Brand Guidelines ---
        if pdf_bytes:
            self.log_task("Mode A: Extracting from PDF brand guidelines")
            try:
                result = await self.analysis_service.analyze_pdf(pdf_bytes, brand_vibe)
                # Enrich with context
                result["cultural_nuance"] = self._generate_cultural_nuance(countries)
                return result
            except Exception as e:
                logger.warning(f"⚠️ PDF extraction failed, falling back: {e}")
        
        # --- MODE B: Website URL Crawling ---
        context_data = ""
        brand_name = None
        
        if url:
            self.log_task("Mode B: Crawling website for brand context")
            try:
                context_data, brand_name = await self._crawl_website(url)
            except Exception as e:
                logger.warning(f"⚠️ Website crawl failed: {e}")
                context_data = ""
        
        # --- MODE C: Text Description ---
        if not context_data and description:
            self.log_task("Mode C: Analyzing text description")
            context_data = f"Business Description: {description}"
        
        # --- AI Synthesis or Pure Fallback ---
        if context_data:
            try:
                return await self._synthesize_brand_dna(
                    context_data=context_data,
                    countries=countries,
                    brand_vibe=brand_vibe,
                    brand_name=brand_name,
                    mode="URL" if url else "Description"
                )
            except Exception as e:
                logger.warning(f"⚠️ AI synthesis failed, using generative fallback: {e}")
        
        # --- FALLBACK: Senior Designer Mode ---
        self.log_task("Fallback: Using Senior Designer generative mode")
        return await self.analysis_service.generate_from_context(
            brand_vibe=brand_vibe,
            industry=industry,
            description=description,
            brand_name=brand_name
        )
    
    async def _crawl_website(self, url: str) -> tuple:
        """
        Crawl website with stealth headers to extract brand context.
        
        Returns:
            Tuple of (context_data, brand_name)
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Run blocking I/O in thread pool
        response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            self.log_task(f"Warning: Site returned status {response.status_code}")
        
        soup = await asyncio.to_thread(BeautifulSoup, response.text, 'html.parser')
        
        # Strip noise
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        
        meta_desc = soup.find("meta", attrs={"name": "description"})
        meta_text = meta_desc["content"] if meta_desc else ""
        title = soup.title.string if soup.title else "Unknown"
        body_text = soup.get_text()[:6000]
        
        context_data = f"Website Title: {title}\nMeta: {meta_text}\nContent: {body_text}"
        
        # Try to extract brand name from title
        brand_name = title.split("|")[0].split("-")[0].strip() if title else None
        
        return context_data, brand_name
    
    async def _synthesize_brand_dna(
        self,
        context_data: str,
        countries: list,
        brand_vibe: str,
        brand_name: str = None,
        mode: str = "Extraction"
    ) -> Dict[str, Any]:
        """
        Use AI to synthesize brand DNA from context data.
        Results are passed through the Senior Constraint enforcer.
        """
        # Get vibe-aware defaults from service
        fonts = self.analysis_service._select_font_pairing(brand_vibe)
        colors = self.analysis_service._infer_colors(None, brand_vibe)
        
        prompt = f"""
        You are a Senior Brand Director. Perform a Brand DNA study for a business targeting {countries or 'Global'}.
        Source Type: {mode}
        Brand Vibe: {brand_vibe}
        INPUT DATA: {context_data}

        Return ONLY a valid JSON object:
        {{
            "brand_name": "string (extract from content or use 'My Brand')",
            "offerings": ["list of products/services"],
            "tone": "description of voice and messaging style",
            "visual_styles": [
                {{"id": "primary", "label": "Primary Style", "desc": "Main visual approach"}},
                {{"id": "secondary", "label": "Secondary Style", "desc": "Alternative approach"}},
                {{"id": "accent", "label": "Accent Style", "desc": "Supporting aesthetic"}}
            ],
            "color_palette": {{
                "primary": "#HEX (extract from site or suggest based on industry)",
                "secondary": "#HEX",
                "accent": "#HEX"
            }},
            "graphic_elements": {{
                "shapes": "description of preferred shapes",
                "line_weight": "thin/normal/bold",
                "vibe": "overall graphic mood"
            }},
            "cultural_nuance": "Marketing advice for {countries or 'Global Markets'}",
            "industry": "inferred industry category"
        }}
        
        Suggested fonts for {brand_vibe} vibe:
        - Header: {fonts.header}
        - Body: {fonts.body}
        
        Suggested colors if not extractable:
        - Primary: {colors.primary}
        - Secondary: {colors.secondary}
        - Accent: {colors.accent}
        """
        
        response = await self.model.generate_content_async(prompt)
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        parsed = json.loads(clean_json)
        
        # Ensure completeness through Senior Constraint enforcer
        return self.analysis_service._ensure_complete_dna(parsed, brand_vibe, source="hybrid")
    
    def _generate_cultural_nuance(self, countries: list) -> str:
        """Generate cultural nuance text for target markets"""
        if not countries:
            return "Focus on universal values: quality, reliability, and customer satisfaction."
        
        if len(countries) == 1:
            return f"Tailor messaging for {countries[0]} market preferences and cultural values."
        
        return f"Balance messaging across {', '.join(countries[:3])} markets while maintaining brand consistency."
    
    async def regenerate_dna(
        self,
        current_dna: Dict[str, Any],
        brand_vibe: str = None
    ) -> Dict[str, Any]:
        """
        Regenerate brand DNA with variations.
        Used by the "Regenerate" button in the frontend.
        
        Keeps core brand identity but regenerates:
        - Pattern (different template or parameters)
        - Visual styles (alternative options)
        - Slight color variations
        """
        vibe = brand_vibe or current_dna.get("brand_vibe", "minimalist")
        
        # Regenerate pattern with different template
        import random
        templates = ["grid", "wave", "dots", "circles", "blob"]
        current_template = current_dna.get("pattern", {}).get("template", "wave")
        available = [t for t in templates if t != current_template]
        new_template = random.choice(available) if available else "wave"
        
        primary_color = current_dna.get("color_palette", {}).get("primary", "#3B82F6")
        new_pattern = self.analysis_service.regenerate_pattern(new_template, primary_color)
        
        # Regenerate visual styles
        new_styles = self.analysis_service._generate_visual_styles(vibe)
        
        # Build updated DNA
        updated = {**current_dna}
        updated["pattern"] = new_pattern
        updated["visual_styles"] = new_styles
        updated["version"] = "2.0"
        
        return updated