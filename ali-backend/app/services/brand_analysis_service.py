"""
Brand Analysis Service v1.0
Phase 0: The Brand DNA Engine

Provides intelligent brand identity extraction and generation with two modes:
- Mode A: PDF Extraction - Parse uploaded brand guidelines
- Mode B: Generation - "Senior Designer" logic for users without brand books

Features:
- Parametric SVG Pattern Engine (5 base templates)
- Industry-aware color psychology
- Brand Vibe to Font Pairing mapping
- "Senior Constraint" enforcer - never returns null fields
"""

import logging
import json
import base64
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)


# =============================================================================
# DATA TYPES
# =============================================================================

class BrandVibe(str, Enum):
    PREMIUM_CORPORATE = "premium_corporate"
    RETAIL_PLAYFUL = "retail_playful"
    MINIMALIST = "minimalist"
    LUXURY = "luxury"
    TECH_MODERN = "tech_modern"


@dataclass
class ColorPalette:
    primary: str = "#3B82F6"
    secondary: str = "#1E293B"
    accent: str = "#6366F1"
    
    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class FontPairing:
    header: str = "Inter"
    body: str = "Roboto"
    link: str = "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Roboto:wght@400;500&display=swap"
    fallback_header: str = "Arial, sans-serif"
    fallback_body: str = "Arial, sans-serif"
    
    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class PatternConfig:
    template: str = "wave"
    svg_data: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BrandDNA:
    """Complete Brand DNA object - never has null fields"""
    brand_name: str = "My Brand"
    offerings: List[str] = field(default_factory=lambda: ["Premium Services"])
    tone: str = "Professional"
    visual_styles: List[Dict[str, str]] = field(default_factory=lambda: [
        {"id": "minimalist", "label": "Modern Professional", "desc": "A clean, standard professional look."}
    ])
    color_palette: Dict[str, str] = field(default_factory=lambda: ColorPalette().to_dict())
    graphic_elements: Dict[str, str] = field(default_factory=lambda: {
        "shapes": "clean",
        "line_weight": "normal",
        "vibe": "modern"
    })
    cultural_nuance: str = "Focus on quality and reliability."
    fonts: Dict[str, str] = field(default_factory=lambda: FontPairing().to_dict())
    pattern: Dict[str, Any] = field(default_factory=dict)
    # Phase 1: Voice and Constraints for Strategist & Editor
    voice: Dict[str, Any] = field(default_factory=lambda: {
        "personality": "Professional and approachable",
        "do": ["Be clear and concise", "Use active voice", "Focus on benefits"],
        "dont": ["Use jargon without explanation", "Make unsubstantiated claims", "Use ALL CAPS"]
    })
    constraints: Dict[str, Any] = field(default_factory=lambda: {
        "banned_phrases": [],
        "required_disclosures": [],
        "tone_guardrails": []
    })
    source: str = "generated"
    brand_vibe: str = "minimalist"
    version: str = "2.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# BRAND VIBE MAPPINGS
# =============================================================================

VIBE_FONT_MAP: Dict[str, FontPairing] = {
    "premium_corporate": FontPairing(
        header="Playfair Display",
        body="Lato",
        link="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=Lato:wght@300;400&display=swap",
        fallback_header="Georgia, serif",
        fallback_body="Arial, sans-serif"
    ),
    "retail_playful": FontPairing(
        header="Anton",
        body="Roboto",
        link="https://fonts.googleapis.com/css2?family=Anton&family=Roboto:wght@400;500;700&display=swap",
        fallback_header="Impact, sans-serif",
        fallback_body="Arial, sans-serif"
    ),
    "minimalist": FontPairing(
        header="Inter",
        body="Roboto Flex",
        link="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=Roboto+Flex:opsz,wght@8..144,100..1000&display=swap",
        fallback_header="sans-serif",
        fallback_body="sans-serif"
    ),
    "luxury": FontPairing(
        header="DM Serif Display",
        body="Cormorant Garamond",
        link="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&display=swap",
        fallback_header="Georgia, serif",
        fallback_body="Georgia, serif"
    ),
    "tech_modern": FontPairing(
        header="Orbitron",
        body="Rajdhani",
        link="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600&display=swap",
        fallback_header="Courier New, monospace",
        fallback_body="Arial, sans-serif"
    )
}


# Industry color psychology mapping
INDUSTRY_COLORS: Dict[str, ColorPalette] = {
    "finance": ColorPalette("#1E40AF", "#0F172A", "#3B82F6"),
    "banking": ColorPalette("#1E3A8A", "#1E293B", "#2563EB"),
    "healthcare": ColorPalette("#047857", "#134E4A", "#10B981"),
    "medical": ColorPalette("#0D9488", "#0F766E", "#14B8A6"),
    "technology": ColorPalette("#7C3AED", "#4C1D95", "#A78BFA"),
    "tech": ColorPalette("#6366F1", "#312E81", "#818CF8"),
    "startup": ColorPalette("#8B5CF6", "#5B21B6", "#A78BFA"),
    "retail": ColorPalette("#DC2626", "#991B1B", "#F87171"),
    "ecommerce": ColorPalette("#EA580C", "#C2410C", "#FB923C"),
    "food": ColorPalette("#D97706", "#92400E", "#FBBF24"),
    "restaurant": ColorPalette("#B91C1C", "#7F1D1D", "#EF4444"),
    "luxury": ColorPalette("#78350F", "#451A03", "#D4A574"),
    "fashion": ColorPalette("#831843", "#500724", "#EC4899"),
    "beauty": ColorPalette("#BE185D", "#9D174D", "#F472B6"),
    "education": ColorPalette("#1D4ED8", "#1E3A8A", "#60A5FA"),
    "nonprofit": ColorPalette("#059669", "#047857", "#34D399"),
    "real_estate": ColorPalette("#0369A1", "#075985", "#38BDF8"),
    "legal": ColorPalette("#1F2937", "#111827", "#6B7280"),
    "consulting": ColorPalette("#334155", "#1E293B", "#64748B"),
    "creative": ColorPalette("#C026D3", "#86198F", "#E879F9"),
    "entertainment": ColorPalette("#DB2777", "#9D174D", "#F472B6"),
    "sports": ColorPalette("#EA580C", "#9A3412", "#FB923C"),
    "fitness": ColorPalette("#16A34A", "#15803D", "#4ADE80"),
}


# Vibe color psychology mapping (fallback when industry unknown)
VIBE_COLORS: Dict[str, ColorPalette] = {
    "premium_corporate": ColorPalette("#1E40AF", "#0F172A", "#3B82F6"),
    "retail_playful": ColorPalette("#F59E0B", "#EA580C", "#FCD34D"),
    "minimalist": ColorPalette("#18181B", "#27272A", "#71717A"),
    "luxury": ColorPalette("#78350F", "#451A03", "#D4A574"),
    "tech_modern": ColorPalette("#7C3AED", "#4C1D95", "#A78BFA"),
}


# =============================================================================
# PARAMETRIC SVG PATTERN TEMPLATES
# =============================================================================

def _generate_grid_pattern(color: str, spacing: int = 40, stroke: float = 1) -> str:
    """Generate geometric grid pattern SVG"""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <defs>
    <pattern id="grid" width="{spacing}" height="{spacing}" patternUnits="userSpaceOnUse">
      <path d="M {spacing} 0 L 0 0 0 {spacing}" fill="none" stroke="{color}" stroke-width="{stroke}" opacity="0.3"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid)"/>
</svg>'''


def _generate_wave_pattern(color: str, amplitude: int = 20, frequency: int = 4) -> str:
    """Generate flowing wave lines pattern SVG"""
    wave_points = []
    for i in range(0, 101, 5):
        import math
        y = 50 + amplitude * math.sin((i / 100) * frequency * math.pi)
        wave_points.append(f"{i},{y:.1f}")
    path_d = "M " + " L ".join(wave_points)
    
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <defs>
    <pattern id="waves" width="100" height="100" patternUnits="userSpaceOnUse">
      <path d="{path_d}" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.25"/>
      <path d="{path_d}" fill="none" stroke="{color}" stroke-width="1" opacity="0.15" transform="translate(0, 10)"/>
      <path d="{path_d}" fill="none" stroke="{color}" stroke-width="0.5" opacity="0.1" transform="translate(0, 20)"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#waves)"/>
</svg>'''


def _generate_dots_pattern(color: str, size: float = 3, spacing: int = 20) -> str:
    """Generate polka dot pattern SVG"""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <defs>
    <pattern id="dots" width="{spacing}" height="{spacing}" patternUnits="userSpaceOnUse">
      <circle cx="{spacing/2}" cy="{spacing/2}" r="{size}" fill="{color}" opacity="0.2"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#dots)"/>
</svg>'''


def _generate_circles_pattern(color: str, count: int = 5, opacity: float = 0.15) -> str:
    """Generate concentric circles pattern SVG"""
    circles = ""
    for i in range(1, count + 1):
        r = i * 18
        o = opacity * (1 - (i / (count + 1)))
        circles += f'<circle cx="50" cy="50" r="{r}" fill="none" stroke="{color}" stroke-width="1" opacity="{o:.2f}"/>\n'
    
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  {circles}
</svg>'''


def _generate_blob_pattern(color1: str, color2: str, complexity: int = 3) -> str:
    """Generate abstract organic blob shape pattern SVG"""
    # Predefined blob paths for different complexity levels
    blob_paths = {
        1: "M50,10 Q90,25 80,60 Q70,95 40,85 Q10,75 20,40 Q30,10 50,10",
        2: "M50,5 Q85,15 90,50 Q95,85 60,90 Q25,95 10,60 Q0,25 35,10 Q50,5 50,5",
        3: "M50,2 Q88,8 95,45 Q98,82 65,95 Q32,98 8,68 Q2,38 28,12 Q54,2 50,2",
    }
    path = blob_paths.get(complexity, blob_paths[2])
    
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <defs>
    <linearGradient id="blob-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{color1};stop-opacity:0.15"/>
      <stop offset="100%" style="stop-color:{color2};stop-opacity:0.08"/>
    </linearGradient>
  </defs>
  <path d="{path}" fill="url(#blob-gradient)" stroke="{color1}" stroke-width="0.5" opacity="0.2"/>
</svg>'''


# Pattern template registry
PATTERN_TEMPLATES = {
    "grid": {
        "generator": _generate_grid_pattern,
        "description": "Geometric grid pattern - professional, structured",
        "default_params": {"spacing": 40, "stroke": 1},
        "best_for": ["premium_corporate", "minimalist", "tech_modern"]
    },
    "wave": {
        "generator": _generate_wave_pattern,
        "description": "Flowing wave lines - dynamic, elegant",
        "default_params": {"amplitude": 20, "frequency": 4},
        "best_for": ["luxury", "retail_playful", "premium_corporate"]
    },
    "dots": {
        "generator": _generate_dots_pattern,
        "description": "Polka dot pattern - playful, approachable",
        "default_params": {"size": 3, "spacing": 20},
        "best_for": ["retail_playful", "minimalist"]
    },
    "circles": {
        "generator": _generate_circles_pattern,
        "description": "Concentric circles - focused, premium",
        "default_params": {"count": 5, "opacity": 0.15},
        "best_for": ["luxury", "tech_modern"]
    },
    "blob": {
        "generator": _generate_blob_pattern,
        "description": "Abstract organic shape - creative, modern",
        "default_params": {"complexity": 2},
        "best_for": ["retail_playful", "tech_modern", "luxury"]
    }
}


# =============================================================================
# BRAND ANALYSIS SERVICE
# =============================================================================

class BrandAnalysisService:
    """
    Intelligent Brand DNA extraction and generation service.
    
    Operates in two modes:
    - Mode A: PDF Extraction - Parse uploaded brand guidelines
    - Mode B: Generation - "Senior Designer" logic for users without brand books
    
    Implements the "Senior Constraint" - never returns incomplete data.
    """
    
    def __init__(self):
        self.genai_client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the Gemini client"""
        try:
            self.genai_client = genai.Client()
            logger.info("✅ BrandAnalysisService: Gemini client initialized")
        except Exception as e:
            logger.warning(f"⚠️ BrandAnalysisService: Gemini client init failed: {e}")
    
    # -------------------------------------------------------------------------
    # MODE A: PDF EXTRACTION
    # -------------------------------------------------------------------------
    
    async def analyze_pdf(self, pdf_bytes: bytes, brand_vibe: str = "minimalist") -> Dict[str, Any]:
        """
        Extract brand DNA from uploaded PDF brand guidelines.
        
        Uses Gemini Pro's multimodal capabilities to parse PDF content
        and extract colors, fonts, rules, and graphic motifs.
        
        Args:
            pdf_bytes: Raw PDF file bytes
            brand_vibe: Selected brand vibe for fallback styling
            
        Returns:
            Complete BrandDNA dictionary (never has null fields)
        """
        logger.info("🔍 BrandAnalysisService: Analyzing PDF brand guidelines...")
        
        if not self.genai_client or not pdf_bytes:
            logger.warning("⚠️ No PDF bytes or client, falling back to generation mode")
            return await self.generate_from_context(brand_vibe=brand_vibe)
        
        try:
            # Encode PDF as base64 for Gemini
            pdf_b64 = base64.standard_b64encode(pdf_bytes).decode('utf-8')
            
            extraction_prompt = """
            You are a Senior Brand Director analyzing brand guidelines.
            Extract the following information from this PDF brand book:
            
            1. Brand Name
            2. Color Palette (primary, secondary, accent colors as hex codes)
            3. Typography (header font, body font)
            4. Visual Rules (shapes, line weights, graphic style)
            5. Tone of Voice
            6. Voice Guidelines (personality, do's and don'ts for communication)
            7. Constraints (banned phrases, required disclosures)
            
            Return ONLY a valid JSON object:
            {
                "brand_name": "string",
                "color_palette": {
                    "primary": "#HEX",
                    "secondary": "#HEX", 
                    "accent": "#HEX"
                },
                "fonts": {
                    "header": "Font Name",
                    "body": "Font Name"
                },
                "graphic_elements": {
                    "shapes": "description",
                    "line_weight": "thin/normal/bold",
                    "vibe": "description"
                },
                "tone": "description",
                "voice": {
                    "personality": "description of brand personality",
                    "do": ["list of communication guidelines to follow"],
                    "dont": ["list of things to avoid in communication"]
                },
                "constraints": {
                    "banned_phrases": ["phrases that should never be used"],
                    "required_disclosures": ["any required legal or brand disclosures"],
                    "tone_guardrails": ["specific tone requirements"]
                },
                "visual_rules": ["list of rules"],
                "offerings": ["inferred products/services"]
            }
            
            If any field cannot be determined, use "infer" as the value.
            """
            
            # Create multimodal content with PDF
            pdf_part = genai_types.Part(
                inline_data=genai_types.Blob(
                    mime_type="application/pdf",
                    data=pdf_b64
                )
            )
            
            response = await self.genai_client.aio.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[pdf_part, extraction_prompt]
            )
            
            # Parse response
            clean_json = response.text.strip()
            clean_json = re.sub(r'^```json\s*', '', clean_json)
            clean_json = re.sub(r'\s*```$', '', clean_json)
            
            extracted = json.loads(clean_json)
            logger.info(f"✅ PDF extraction successful: {extracted.get('brand_name', 'Unknown')}")
            
            # Merge with defaults and ensure completeness
            return self._ensure_complete_dna(extracted, brand_vibe, source="pdf")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ PDF extraction JSON parse error: {e}")
            return await self.generate_from_context(brand_vibe=brand_vibe)
        except Exception as e:
            logger.error(f"❌ PDF extraction failed: {e}")
            return await self.generate_from_context(brand_vibe=brand_vibe)
    
    # -------------------------------------------------------------------------
    # MODE B: GENERATIVE FALLBACK ("Senior Designer" Logic)
    # -------------------------------------------------------------------------
    
    async def generate_from_context(
        self,
        brand_vibe: str = "minimalist",
        logo_url: Optional[str] = None,
        website_url: Optional[str] = None,
        industry: Optional[str] = None,
        description: Optional[str] = None,
        brand_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete brand DNA from available context.
        
        This is the "Senior Designer" mode - even with minimal input,
        it produces a complete, valid brand identity.
        
        Args:
            brand_vibe: Selected brand aesthetic (premium_corporate, retail_playful, etc.)
            logo_url: Optional logo URL for color extraction
            website_url: Optional website for context
            industry: Optional industry for color psychology
            description: Text description of the brand
            brand_name: Known brand name
            
        Returns:
            Complete BrandDNA dictionary (never has null fields)
        """
        logger.info(f"🎨 BrandAnalysisService: Generating DNA for vibe='{brand_vibe}'")
        
        # Step 1: Determine colors
        colors = self._infer_colors(industry, brand_vibe, logo_url)
        
        # Step 2: Select fonts based on vibe
        fonts = self._select_font_pairing(brand_vibe)
        
        # Step 3: Generate pattern
        pattern = self._generate_pattern_for_vibe(brand_vibe, colors.primary)
        
        # Step 4: Build visual styles based on vibe
        visual_styles = self._generate_visual_styles(brand_vibe)
        
        # Step 5: Generate graphic elements
        graphic_elements = self._generate_graphic_elements(brand_vibe)
        
        # Step 6: Generate tone based on vibe
        tone = self._generate_tone(brand_vibe)
        
        # Build complete DNA
        dna = BrandDNA(
            brand_name=brand_name or "My Brand",
            offerings=["Premium Services"],
            tone=tone,
            visual_styles=visual_styles,
            color_palette=colors.to_dict(),
            graphic_elements=graphic_elements,
            cultural_nuance="Focus on quality, authenticity, and customer connection.",
            fonts=fonts.to_dict(),
            pattern=pattern,
            source="generated",
            brand_vibe=brand_vibe,
            version="2.0"
        )
        
        # If we have description, try to enrich with AI
        if description and self.genai_client:
            try:
                enriched = await self._enrich_with_ai(dna.to_dict(), description)
                return self._ensure_complete_dna(enriched, brand_vibe, source="generated")
            except Exception as e:
                logger.warning(f"⚠️ AI enrichment failed, using base DNA: {e}")
        
        return dna.to_dict()
    
    # -------------------------------------------------------------------------
    # INFERENCE HELPERS
    # -------------------------------------------------------------------------
    
    def _infer_colors(
        self, 
        industry: Optional[str], 
        brand_vibe: str,
        logo_url: Optional[str] = None
    ) -> ColorPalette:
        """
        Infer colors based on available information.
        
        Priority:
        1. Industry-specific colors (if industry known)
        2. Brand vibe colors
        3. Default professional colors
        """
        # TODO: Future enhancement - extract colors from logo_url using image analysis
        
        # Check industry
        if industry:
            industry_key = industry.lower().replace(" ", "_")
            if industry_key in INDUSTRY_COLORS:
                logger.info(f"📊 Using industry colors for: {industry}")
                return INDUSTRY_COLORS[industry_key]
            # Try partial matching
            for key, colors in INDUSTRY_COLORS.items():
                if key in industry_key or industry_key in key:
                    logger.info(f"📊 Using related industry colors: {key}")
                    return colors
        
        # Use vibe colors
        if brand_vibe in VIBE_COLORS:
            logger.info(f"🎨 Using vibe colors for: {brand_vibe}")
            return VIBE_COLORS[brand_vibe]
        
        # Default
        logger.info("🎨 Using default professional colors")
        return ColorPalette()
    
    def _select_font_pairing(self, brand_vibe: str) -> FontPairing:
        """Select font pairing based on brand vibe"""
        if brand_vibe in VIBE_FONT_MAP:
            return VIBE_FONT_MAP[brand_vibe]
        return FontPairing()  # Default fonts
    
    def _generate_pattern_for_vibe(self, brand_vibe: str, primary_color: str) -> Dict[str, Any]:
        """Generate the best pattern for the given brand vibe"""
        # Find best matching template
        best_template = "wave"  # Default
        for template_name, template_info in PATTERN_TEMPLATES.items():
            if brand_vibe in template_info.get("best_for", []):
                best_template = template_name
                break
        
        template_info = PATTERN_TEMPLATES[best_template]
        params = template_info["default_params"].copy()
        
        # Generate SVG
        generator = template_info["generator"]
        if best_template == "blob":
            svg_data = generator(primary_color, primary_color, **params)
        else:
            svg_data = generator(primary_color, **params)
        
        return PatternConfig(
            template=best_template,
            svg_data=svg_data,
            params={"color": primary_color, **params}
        ).to_dict()
    
    def _generate_visual_styles(self, brand_vibe: str) -> List[Dict[str, str]]:
        """Generate visual style options based on brand vibe"""
        style_options = {
            "premium_corporate": [
                {"id": "executive", "label": "Executive", "desc": "Refined corporate elegance with authoritative presence."},
                {"id": "professional", "label": "Professional", "desc": "Clean, trustworthy business aesthetic."},
                {"id": "sophisticated", "label": "Sophisticated", "desc": "Understated luxury with attention to detail."}
            ],
            "retail_playful": [
                {"id": "vibrant", "label": "Vibrant", "desc": "Energetic and eye-catching retail appeal."},
                {"id": "friendly", "label": "Friendly", "desc": "Approachable and inviting visual language."},
                {"id": "dynamic", "label": "Dynamic", "desc": "Fast-paced, action-oriented messaging."}
            ],
            "minimalist": [
                {"id": "minimal", "label": "Minimal", "desc": "Clean lines, ample whitespace, clarity."},
                {"id": "modern", "label": "Modern", "desc": "Contemporary simplicity with purpose."},
                {"id": "zen", "label": "Zen", "desc": "Calm, focused, distraction-free."}
            ],
            "luxury": [
                {"id": "opulent", "label": "Opulent", "desc": "Rich textures and premium materials."},
                {"id": "timeless", "label": "Timeless", "desc": "Classic elegance that never ages."},
                {"id": "exclusive", "label": "Exclusive", "desc": "Rare, coveted, invitation-only feel."}
            ],
            "tech_modern": [
                {"id": "futuristic", "label": "Futuristic", "desc": "Cutting-edge technology forward."},
                {"id": "innovative", "label": "Innovative", "desc": "Breaking new ground, disrupting norms."},
                {"id": "digital", "label": "Digital", "desc": "Connected, smart, seamless."}
            ]
        }
        return style_options.get(brand_vibe, [
            {"id": "modern", "label": "Modern Professional", "desc": "A clean, standard professional look."}
        ])
    
    def _generate_graphic_elements(self, brand_vibe: str) -> Dict[str, str]:
        """Generate graphic element guidelines based on vibe"""
        elements = {
            "premium_corporate": {"shapes": "clean rectangles", "line_weight": "thin", "vibe": "structured"},
            "retail_playful": {"shapes": "rounded, organic", "line_weight": "bold", "vibe": "energetic"},
            "minimalist": {"shapes": "simple geometric", "line_weight": "thin", "vibe": "clean"},
            "luxury": {"shapes": "elegant curves", "line_weight": "fine", "vibe": "opulent"},
            "tech_modern": {"shapes": "angular, futuristic", "line_weight": "medium", "vibe": "innovative"}
        }
        return elements.get(brand_vibe, {"shapes": "clean", "line_weight": "normal", "vibe": "modern"})
    
    def _generate_tone(self, brand_vibe: str) -> str:
        """Generate tone of voice based on brand vibe"""
        tones = {
            "premium_corporate": "Authoritative, confident, and trustworthy. Speaks with expertise.",
            "retail_playful": "Friendly, enthusiastic, and approachable. Celebrates the customer.",
            "minimalist": "Clear, concise, and purposeful. Every word matters.",
            "luxury": "Refined, exclusive, and aspirational. Whispers rather than shouts.",
            "tech_modern": "Innovative, forward-thinking, and empowering. Builds excitement for possibilities."
        }
        return tones.get(brand_vibe, "Professional and approachable.")
    
    def _generate_voice_for_vibe(self, brand_vibe: str) -> Dict[str, Any]:
        """
        Generate complete brand voice guidelines based on vibe.
        Phase 1: The Strategist & Editor
        
        Returns:
            Voice dictionary with personality, do's, and don'ts
        """
        voice_profiles = {
            "premium_corporate": {
                "personality": "Authoritative, confident, and trustworthy. Speaks with expertise and clarity.",
                "do": [
                    "Use formal but accessible language",
                    "Lead with data and evidence",
                    "Maintain professional tone",
                    "Focus on value and ROI"
                ],
                "dont": [
                    "Use slang or informal expressions",
                    "Make exaggerated claims",
                    "Use excessive exclamation marks",
                    "Sound salesy or pushy"
                ]
            },
            "retail_playful": {
                "personality": "Friendly, enthusiastic, and approachable. Celebrates the customer.",
                "do": [
                    "Use conversational language",
                    "Include emojis where appropriate",
                    "Create urgency with excitement",
                    "Celebrate customer wins"
                ],
                "dont": [
                    "Sound corporate or stiff",
                    "Use complex jargon",
                    "Be condescending",
                    "Ignore the fun factor"
                ]
            },
            "minimalist": {
                "personality": "Clear, concise, and purposeful. Every word matters.",
                "do": [
                    "Keep sentences short",
                    "Use active voice",
                    "Focus on one key message",
                    "Let whitespace breathe"
                ],
                "dont": [
                    "Use filler words",
                    "Over-explain",
                    "Use multiple CTAs",
                    "Clutter with unnecessary details"
                ]
            },
            "luxury": {
                "personality": "Refined, exclusive, and aspirational. Whispers rather than shouts.",
                "do": [
                    "Use elegant, sophisticated language",
                    "Emphasize exclusivity and rarity",
                    "Focus on experience and craftsmanship",
                    "Create desire through restraint"
                ],
                "dont": [
                    "Use discount language",
                    "Sound desperate or urgent",
                    "Use ALL CAPS or excessive punctuation",
                    "Compare to competitors directly"
                ]
            },
            "tech_modern": {
                "personality": "Innovative, forward-thinking, and empowering. Builds excitement for possibilities.",
                "do": [
                    "Use action-oriented language",
                    "Reference innovation and progress",
                    "Empower the user",
                    "Be direct and clear"
                ],
                "dont": [
                    "Use outdated references",
                    "Be overly technical without context",
                    "Sound boring or generic",
                    "Ignore the human element"
                ]
            }
        }
        
        return voice_profiles.get(brand_vibe, {
            "personality": "Professional and approachable",
            "do": ["Be clear and concise", "Use active voice", "Focus on benefits"],
            "dont": ["Use jargon without explanation", "Make unsubstantiated claims", "Use ALL CAPS"]
        })
    
    async def _enrich_with_ai(self, base_dna: Dict[str, Any], description: str) -> Dict[str, Any]:
        """Use AI to enrich brand DNA based on description"""
        prompt = f"""
        You are a Senior Brand Director. Enrich this brand DNA based on the description.
        
        Current DNA: {json.dumps(base_dna, indent=2)}
        
        Business Description: {description}
        
        Update and return ONLY a valid JSON object with the same structure.
        Focus on:
        1. Inferring brand_name if possible
        2. Identifying specific offerings
        3. Refining the tone to match the description
        4. Adding relevant cultural nuances
        
        Keep all existing fields, only enhance values where appropriate.
        """
        
        response = await self.genai_client.aio.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        clean_json = response.text.strip()
        clean_json = re.sub(r'^```json\s*', '', clean_json)
        clean_json = re.sub(r'\s*```$', '', clean_json)
        
        return json.loads(clean_json)
    
    # -------------------------------------------------------------------------
    # SENIOR CONSTRAINT ENFORCER
    # -------------------------------------------------------------------------
    
    def _ensure_complete_dna(
        self, 
        partial: Dict[str, Any], 
        brand_vibe: str,
        source: str = "generated"
    ) -> Dict[str, Any]:
        """
        The "Senior Constraint" enforcer.
        
        Guarantees that the returned DNA object is complete with no null fields.
        Any missing or "infer" values are filled with intelligent defaults.
        
        Args:
            partial: Partially complete DNA dictionary
            brand_vibe: Brand vibe for default selection
            source: "pdf" or "generated"
            
        Returns:
            Complete BrandDNA dictionary (never has null fields)
        """
        # Start with defaults
        defaults = BrandDNA(
            brand_vibe=brand_vibe,
            source=source
        ).to_dict()
        
        # Merge partial over defaults
        result = {**defaults, **partial}
        
        # Ensure nested objects are complete
        if not result.get("color_palette") or result["color_palette"].get("primary") in [None, "infer", "#HEX"]:
            colors = self._infer_colors(None, brand_vibe)
            result["color_palette"] = colors.to_dict()
        
        if not result.get("fonts") or result["fonts"].get("header") in [None, "infer"]:
            fonts = self._select_font_pairing(brand_vibe)
            result["fonts"] = fonts.to_dict()
        
        if not result.get("pattern") or not result["pattern"].get("svg_data"):
            primary_color = result["color_palette"].get("primary", "#3B82F6")
            result["pattern"] = self._generate_pattern_for_vibe(brand_vibe, primary_color)
        
        if not result.get("visual_styles") or len(result["visual_styles"]) == 0:
            result["visual_styles"] = self._generate_visual_styles(brand_vibe)
        
        if not result.get("graphic_elements"):
            result["graphic_elements"] = self._generate_graphic_elements(brand_vibe)
        
        if not result.get("tone") or result["tone"] == "infer":
            result["tone"] = self._generate_tone(brand_vibe)
        
        # Phase 1: Ensure voice and constraints are complete
        if not result.get("voice") or not result["voice"].get("personality"):
            result["voice"] = self._generate_voice_for_vibe(brand_vibe)
        
        if not result.get("constraints"):
            result["constraints"] = {
                "banned_phrases": [],
                "required_disclosures": [],
                "tone_guardrails": []
            }
        
        # Final null check - replace any remaining nulls
        for key, value in result.items():
            if value is None:
                result[key] = defaults.get(key, "")
        
        result["version"] = "2.0"
        result["source"] = source
        result["brand_vibe"] = brand_vibe
        
        logger.info(f"✅ DNA complete: {result.get('brand_name')} ({source})")
        return result
    
    # -------------------------------------------------------------------------
    # PATTERN REGENERATION
    # -------------------------------------------------------------------------
    
    def regenerate_pattern(
        self, 
        template: Optional[str] = None,
        color: str = "#3B82F6",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Regenerate a pattern with different parameters.
        
        Useful for the "Regenerate" button in the frontend.
        
        Args:
            template: Pattern template name (grid, wave, dots, circles, blob)
            color: Primary color for the pattern
            **kwargs: Additional parameters for the template
            
        Returns:
            PatternConfig dictionary
        """
        import random
        
        if not template:
            template = random.choice(list(PATTERN_TEMPLATES.keys()))
        
        if template not in PATTERN_TEMPLATES:
            template = "wave"
        
        template_info = PATTERN_TEMPLATES[template]
        params = {**template_info["default_params"], **kwargs}
        
        generator = template_info["generator"]
        if template == "blob":
            svg_data = generator(color, color, **params)
        else:
            svg_data = generator(color, **params)
        
        return PatternConfig(
            template=template,
            svg_data=svg_data,
            params={"color": color, **params}
        ).to_dict()


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

_service_instance: Optional[BrandAnalysisService] = None


def get_brand_analysis_service() -> BrandAnalysisService:
    """Get or create the singleton service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = BrandAnalysisService()
    return _service_instance


async def analyze_brand_pdf(pdf_bytes: bytes, brand_vibe: str = "minimalist") -> Dict[str, Any]:
    """Convenience function for PDF analysis"""
    service = get_brand_analysis_service()
    return await service.analyze_pdf(pdf_bytes, brand_vibe)


async def generate_brand_dna(
    brand_vibe: str = "minimalist",
    **kwargs
) -> Dict[str, Any]:
    """Convenience function for DNA generation"""
    service = get_brand_analysis_service()
    return await service.generate_from_context(brand_vibe=brand_vibe, **kwargs)
