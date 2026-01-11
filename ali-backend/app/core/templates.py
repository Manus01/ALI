"""
Master Motion Templates Library v2.0
"Veo-Level" HTML5/GSAP Animations with Film Grain, Particles, RGB Shift

Templates: luxury, cyber, editorial, minimal
Each template includes: Film grain overlay, GSAP animations, advanced CSS effects
"""

# CDN Links
GSAP_CDN = "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"
GSAP_CDN_FALLBACK = "https://cdn.jsdelivr.net/npm/gsap@3.12.2/dist/gsap.min.js"

def get_gsap_script_tag() -> str:
    """Generate GSAP script tag with fallback for CDN failures."""
    return f'''<script src="{GSAP_CDN}" onerror="this.onerror=null;this.src='{GSAP_CDN_FALLBACK}'"></script>'''

# Base64-encoded noise texture for film grain (16x16 repeating pattern)
GRAIN_TEXTURE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsTAAALEwEAmpwYAAABN0lEQVQ4jYWSMU7DQBBF/2zsGImGgoKCgpqSmpaOK3ABLkFJQUVBQcsFuAAVBR0SBQ0FDQ0NNfZis/PZ+Cd2bCXDSKvdnf/nzexsFTPDJpSUMCIQARGBCIgIREAEGPm4HwYhBEIIhBAItfq1vgwCwTQNJZYkeSRJnkCSZJCE0cg0TUMppZRSSillqFq9Wl+5XIpxHMdxvF7XdV3X9SJJkkSSgBCCEALDMAwhhFKqVqvVavW6rheLxWKxWCTkPI9EIpFIJBLxPM9hGIZhmGEYhmGapmmap"

# ============================================================================
# TYPOGRAPHY ENGINE - Brand-Specific Font Pairings
# ============================================================================
FONT_PAIRINGS = {
    "luxury": {
        "header": "Playfair Display",
        "body": "Lato",
        "link": "https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=Lato:wght@300;400&display=swap",
        "fallback_header": "Georgia, serif",
        "fallback_body": "Arial, sans-serif"
    },
    "cyber": {
        "header": "Orbitron",
        "body": "Rajdhani",
        "link": "https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600&display=swap",
        "fallback_header": "Courier New, monospace",
        "fallback_body": "Arial, sans-serif"
    },
    "minimal": {
        "header": "Montserrat",
        "body": "Open Sans",
        "link": "https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&family=Open+Sans:wght@300;400&display=swap",
        "fallback_header": "Arial, sans-serif",
        "fallback_body": "Arial, sans-serif"
    },
    "editorial": {
        "header": "DM Serif Display",
        "body": "Cormorant Garamond",
        "link": "https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&display=swap",
        "fallback_header": "Georgia, serif",
        "fallback_body": "Georgia, serif"
    },
    "pop": {
        "header": "Anton",
        "body": "Roboto",
        "link": "https://fonts.googleapis.com/css2?family=Anton&family=Roboto:wght@400;500;700&display=swap",
        "fallback_header": "Impact, sans-serif",
        "fallback_body": "Arial, sans-serif"
    },
    "scrapbook": {
        "header": "Permanent Marker",
        "body": "Patrick Hand",
        "link": "https://fonts.googleapis.com/css2?family=Permanent+Marker&family=Patrick+Hand&display=swap",
        "fallback_header": "Comic Sans MS, cursive",
        "fallback_body": "Arial, sans-serif"
    },
    "swiss": {
        "header": "Inter",
        "body": "Roboto Mono",
        "link": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Roboto+Mono:wght@400;500&display=swap",
        "fallback_header": "Helvetica, Arial, sans-serif",
        "fallback_body": "Courier New, monospace"
    },
    "aurora": {
        "header": "Inter",
        "body": "Roboto Flex",
        "link": "https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=Roboto+Flex:opsz,wght@8..144,100..1000&display=swap",
        "fallback_header": "sans-serif",
        "fallback_body": "sans-serif"
    },
    "gridlock": {
        "header": "Orbitron",
        "body": "Rajdhani",
        "link": "https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600&display=swap",
        "fallback_header": "Courier New, monospace",
        "fallback_body": "Arial, sans-serif"
    }
}

FONT_MAP = FONT_PAIRINGS

def get_font_pairing(template_name: str) -> dict:
    """Returns font pairing configuration for the given template."""
    return FONT_PAIRINGS.get(template_name, FONT_PAIRINGS["minimal"])

# Global CSS for film grain overlay (used by all templates)
GLOBAL_GRAIN_CSS = f'''
    .grain {{
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none;
        z-index: 9999;
        opacity: 0.08;
        background-image: url("{GRAIN_TEXTURE}");
        background-repeat: repeat;
        animation: grain 0.5s steps(10) infinite;
    }}
    @keyframes grain {{
        0%, 100% {{ transform: translate(0, 0); }}
        10% {{ transform: translate(-2%, -2%); }}
        20% {{ transform: translate(2%, 2%); }}
        30% {{ transform: translate(-1%, 1%); }}
        40% {{ transform: translate(1%, -1%); }}
        50% {{ transform: translate(-2%, 2%); }}
        60% {{ transform: translate(2%, -2%); }}
        70% {{ transform: translate(-1%, -1%); }}
        80% {{ transform: translate(1%, 1%); }}
        90% {{ transform: translate(-2%, -1%); }}
    }}
'''

# Global CSS for Smart Layouts & Topography
GLOBAL_LAYOUT_CSS = '''
    /* Smart Sizing */
    .text-huge {
        font-size: 5rem !important;
        line-height: 1.05 !important;
    }
    
    /* Layout Variants Utilities */
    .layout-flex {
        display: flex;
        flex-direction: column;
        width: 100%;
        height: 100%;
    }
    
    /* === ORIGINAL LAYOUTS === */
    .variant-hero-center {
        justify-content: center;
        align-items: center;
        text-align: center;
    }
    
    .variant-editorial-left {
        justify-content: center;
        align-items: flex-start;
        text-align: left;
        padding-left: 5%;
    }
    
    .variant-editorial-right {
        justify-content: center;
        align-items: flex-end;
        text-align: right;
        padding-right: 5%;
    }
    
    /* === V7.0 NEW LAYOUTS === */
    
    /* Lower-Third: TV/News style - text at bottom */
    .variant-lower-third {
        justify-content: flex-end;
        align-items: flex-start;
        text-align: left;
        padding: 0 5% 15% 5%;
    }
    .variant-lower-third .text-container {
        background: linear-gradient(transparent, rgba(0,0,0,0.7));
        padding: 30px;
        width: 100%;
    }
    
    /* Top-Banner: Safe for TikTok/Reels (avoid bottom UI) */
    .variant-top-banner {
        justify-content: flex-start;
        align-items: center;
        text-align: center;
        padding-top: 15%;
    }
    
    /* Corner-Badge: Minimal branding - logo in corner */
    .variant-corner-badge {
        justify-content: flex-end;
        align-items: flex-end;
        text-align: right;
        padding: 5%;
    }
    .variant-corner-badge .headline {
        font-size: 2rem !important;
    }
    
    /* Split-Screen: Half video, half text (for explainers) */
    .variant-split-screen {
        justify-content: center;
        align-items: center;
        text-align: center;
    }
    .variant-split-screen .text-container {
        background: rgba(0,0,0,0.85);
        padding: 40px;
        width: 90%;
        border-radius: 20px;
    }
'''

# V7.0 Layout Variant Configuration
LAYOUT_VARIANTS = {
    "hero-center": {
        "css_class": "variant-hero-center",
        "description": "Centered text, balanced composition",
        "best_for": ["general", "brand", "announcement"]
    },
    "editorial-left": {
        "css_class": "variant-editorial-left",
        "description": "Left-aligned text, magazine style",
        "best_for": ["text-heavy", "quotes", "testimonials"]
    },
    "editorial-right": {
        "css_class": "variant-editorial-right", 
        "description": "Right-aligned text, asymmetric balance",
        "best_for": ["product", "feature-highlight"]
    },
    "lower-third": {
        "css_class": "variant-lower-third",
        "description": "TV/News style bottom bar",
        "best_for": ["news", "updates", "professional"]
    },
    "top-banner": {
        "css_class": "variant-top-banner",
        "description": "Text at top, safe for TikTok/Reels",
        "best_for": ["tiktok", "reels", "shorts"],
        "safe_for_channels": ["tiktok", "instagram", "youtube_shorts"]
    },
    "corner-badge": {
        "css_class": "variant-corner-badge",
        "description": "Minimal branding, logo focus",
        "best_for": ["minimal", "brand-only", "teaser"]
    },
    "split-screen": {
        "css_class": "variant-split-screen",
        "description": "Text box overlay, explainer style",
        "best_for": ["explainer", "tutorial", "tips"]
    }
}

# Channel-aware layout recommendations
CHANNEL_LAYOUT_PREFERENCE = {
    "tiktok": ["top-banner", "hero-center", "split-screen"],
    "instagram": ["hero-center", "editorial-left", "lower-third"],
    "instagram_story": ["top-banner", "hero-center", "split-screen"],
    "youtube_shorts": ["top-banner", "hero-center", "lower-third"],
    "linkedin": ["hero-center", "editorial-left", "lower-third"],
    "facebook": ["hero-center", "editorial-left", "split-screen"],
    "twitter": ["hero-center", "corner-badge", "editorial-left"]
}

def get_layout_for_channel(channel: str, content_type: str = "general") -> str:
    """
    Get the best layout variant for a given channel and content type.
    Returns the CSS class name for the layout.
    """
    import random
    
    # Get channel preferences or default
    preferences = CHANNEL_LAYOUT_PREFERENCE.get(channel, ["hero-center", "editorial-left"])
    
    # Pick from top preferences with some randomization
    if len(preferences) > 1:
        # 60% chance of first choice, 30% second, 10% random
        roll = random.random()
        if roll < 0.6:
            choice = preferences[0]
        elif roll < 0.9:
            choice = preferences[1] if len(preferences) > 1 else preferences[0]
        else:
            choice = random.choice(preferences)
    else:
        choice = preferences[0]
    
    return LAYOUT_VARIANTS[choice]["css_class"]



# V4.1 Animation Fail-Safe CSS
# Ensures content is VISIBLE by default - GSAP will handle hiding & revealing
# If JS fails, content remains visible rather than invisible
GLOBAL_FAILSAFE_CSS = '''
    /* V4.1 Fail-Safe: Default visible state for animated elements */
    /* GSAP should use gsap.set() to hide before animating, NOT CSS opacity: 0 */
    #text, #logo, #glass-card, #text-container, #text-panel, 
    #headline, .headline, .copy-text, .accent-bar {
        opacity: 1 !important;
        visibility: visible !important;
    }
    
    /* Marker class for screenshot capture timing */
    body.animation-complete {
        /* No visual change - this class signals GSAP animations are done */
    }
    
    /* Fallback: If GSAP fails, elements stay visible but static */
    @supports not (animation: none) {
        #text, #logo, #glass-card { 
            transform: none !important;
            filter: none !important;
        }
    }
'''


def get_motion_template(template_name: str, image_url: str, logo_url: str, color: str, text: str, luminance_mode: str = 'dark', layout_variant: str = 'hero-center') -> str:
    """
    Returns complete HTML5 motion asset for the given template.
    
    Args:
        template_name: One of 'luxury', 'cyber', 'editorial', 'minimal', 'aurora', 'gridlock'
        image_url: Background image URL
        logo_url: Brand logo URL
        color: Primary brand color (hex)
        text: Headline/caption text
        luminance_mode: 'dark' (needs white text) or 'light' (needs black text)
        layout_variant: 'hero-center', 'editorial-left', 'editorial-right'
    
    Returns:
        Complete HTML string ready for base64 encoding
    """
    if template_name == "luxury":
        return _luxury_template(image_url, logo_url, color, text, layout_variant)
    elif template_name == "cyber":
        return _cyber_template(image_url, logo_url, color, text, layout_variant)
    elif template_name == "editorial":
        return _editorial_template(image_url, logo_url, color, text, layout_variant)
    elif template_name == "aurora":
        return _aurora_template(image_url, logo_url, color, text, luminance_mode, layout_variant)
    elif template_name == "gridlock":
        return _gridlock_template(image_url, logo_url, color, text, luminance_mode, layout_variant)
    elif template_name == "scrapbook":
        return _scrapbook_template(image_url, logo_url, color, text, layout_variant)
    elif template_name == "pop":
        return _pop_template(image_url, logo_url, color, text, layout_variant)
    elif template_name == "swiss":
        return _swiss_template(image_url, logo_url, color, text, layout_variant)
    else:
        return _minimal_template(image_url, logo_url, color, text, layout_variant)


def _luxury_template(image_url: str, logo_url: str, color: str, text: str, layout_variant: str = 'hero-center') -> str:
    """
    Luxury Cinematic Template - "Veo Competitor"
    Features: Ken Burns zoom, arch-shaped image mask, italic headline accents,
    floating canvas particles, glassmorphism, light leak overlays, film grain
    """
    font = get_font_pairing("luxury")
    text_size_class = "text-huge" if len(text) < 30 else ""
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="{font['link']}" rel="stylesheet">
    <style>
        :root {{
            --brand-color: {color};
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body, html {{ 
            width: 100%; height: 100%; overflow: hidden; 
            font-family: '{font['body']}', {font['fallback_body']};
            background: #0a0a0a;
        }}
        
        {GLOBAL_GRAIN_CSS}
        {GLOBAL_LAYOUT_CSS}
        {GLOBAL_FAILSAFE_CSS}
        
        /* Arch-shaped image container */
        #image-arch {{
            position: absolute; top: 5%; left: 10%; width: 80%; height: 65%;
            border-radius: 200px 200px 0 0;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }}
        
        #bg {{
            position: absolute; top: -10%; left: -10%; width: 120%; height: 120%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
            transform-origin: center center;
        }}
        
        /* Light Leak Overlays - Pulsating Orange/Purple */
        #light-leak-1 {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(135deg, 
                rgba(255, 150, 80, 0.25) 0%, 
                transparent 50%);
            mix-blend-mode: overlay;
            pointer-events: none;
        }}
        
        #light-leak-2 {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(315deg, 
                rgba(180, 100, 255, 0.2) 0%, 
                transparent 50%);
            mix-blend-mode: overlay;
            pointer-events: none;
        }}
        
        #particles {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none;
            z-index: 10;
        }}
        
        #glass-card {{
            position: absolute; bottom: 0; left: 0; right: 0;
            padding: 50px 40px 60px;
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border-top: 1px solid rgba(255, 255, 255, 0.15);
            z-index: 20;
            /* Layout Flex Integration */
            display: flex;
            flex-direction: column;
            min-height: 35%;
        }}
        
        #text {{
            color: white;
            font-family: '{font['header']}', {font['fallback_header']};
            font-size: 32px;
            font-weight: 500;
            line-height: 1.35;
            text-shadow: 0 4px 30px rgba(0,0,0,0.6);
            letter-spacing: 0.5px;
            width: 100%;
        }}
        
        /* Italic accent for luxury headlines */
        #text .italic-accent, #text em {{
            font-style: italic;
            color: var(--brand-color);
            font-weight: 600;
        }}
        
        #logo {{
            position: absolute; top: 35px; right: 35px;
            width: 90px; height: auto;
            filter: drop-shadow(0 4px 20px rgba(0,0,0,0.4));
            z-index: 50;
        }}
        
        #brand-glow {{
            position: absolute; top: -30%; right: -20%;
            width: 60%; height: 80%;
            background: radial-gradient(ellipse, {color}40 0%, transparent 60%);
            pointer-events: none;
        }}
        
        #vignette {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            box-shadow: inset 0 0 200px rgba(0,0,0,0.5);
            pointer-events: none;
            z-index: 15;
        }}
    </style>
    <script src="{GSAP_CDN}"></script>
</head>
<body>
    <!-- Arch-shaped image container -->
    <div id="image-arch">
        <div id="bg"></div>
    </div>
    <div id="light-leak-1"></div>
    <div id="light-leak-2"></div>
    <div id="brand-glow"></div>
    <canvas id="particles"></canvas>
    <div id="vignette"></div>
    <img id="logo" src="{logo_url}" onerror="this.style.display='none'">
    <div id="glass-card" class="variant-{layout_variant}">
        <div id="text" class="{text_size_class}">{text}</div>
    </div>
    <div class="grain"></div>
    
    <script>
        // Ken Burns Effect - Slow cinematic zoom with subtle rotation
        gsap.to("#bg", {{
            scale: 1.15,
            x: "-3%",
            y: "-3%",
            rotation: 0.8,
            duration: 15,
            ease: "none"
        }});
        
        // Text Blur Reveal - Elegant entrance
        gsap.from("#text", {{
            filter: "blur(25px)",
            opacity: 0,
            y: 40,
            duration: 2.8,
            ease: "power3.out",
            delay: 0.6
        }});
        
        // Logo Fade with Scale
        gsap.from("#logo", {{
            opacity: 0,
            scale: 0.8,
            y: -25,
            duration: 1.8,
            delay: 0.4,
            ease: "power2.out"
        }});
        
        // Glass Card Rise
        gsap.from("#glass-card", {{
            y: 120,
            opacity: 0,
            duration: 2,
            ease: "power3.out",
            delay: 0.3
        }});
        
        // Light Leak Pulsation @ 20% opacity variation
        gsap.to("#light-leak-1", {{
            opacity: 0.4,
            duration: 4,
            yoyo: true,
            repeat: -1,
            ease: "sine.inOut"
        }});
        
        gsap.to("#light-leak-2", {{
            opacity: 0.35,
            duration: 5,
            yoyo: true,
            repeat: -1,
            ease: "sine.inOut",
            delay: 1
        }});
        
        // Floating Particles (Dust/Sparks)
        const canvas = document.getElementById('particles');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const particles = [];
        for (let i = 0; i < 50; i++) {{
            particles.push({{
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                size: Math.random() * 2.5 + 0.5,
                speedY: -Math.random() * 0.4 - 0.15,
                speedX: (Math.random() - 0.5) * 0.2,
                opacity: Math.random() * 0.6 + 0.2,
                glow: Math.random() > 0.7
            }});
        }}
        
        function animateParticles() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => {{
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                if (p.glow) {{
                    ctx.shadowBlur = 10;
                    ctx.shadowColor = 'rgba(255, 200, 150, 0.5)';
                }}
                ctx.fillStyle = `rgba(255, 255, 255, ${{p.opacity}})`;
                ctx.fill();
                ctx.shadowBlur = 0;
                
                p.y += p.speedY;
                p.x += p.speedX;
                
                if (p.y < -10) {{
                    p.y = canvas.height + 10;
                    p.x = Math.random() * canvas.width;
                }}
            }});
            requestAnimationFrame(animateParticles);
        }}
        animateParticles();
    </script>
</body>
</html>'''


def _cyber_template(image_url: str, logo_url: str, color: str, text: str, layout_variant: str = 'hero-center') -> str:
    """
    Cyber Hype Template - "Tech/Sneaker Style"
    Features: Monochrome + neon color grading, RGB split, glitch effects, 
    SVG data brackets decorators, scanlines, chromatic aberration
    """
    font = get_font_pairing("cyber")
    text_size_class = "text-huge" if len(text) < 30 else ""
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="{font['link']}" rel="stylesheet">
    <style>
        :root {{
            --brand-color: {color};
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body, html {{ 
            width: 100%; height: 100%; overflow: hidden; 
            font-family: '{font['body']}', {font['fallback_body']};
            background: #0a0a0a;
        }}
        
        {GLOBAL_GRAIN_CSS}
        {GLOBAL_LAYOUT_CSS}
        {GLOBAL_FAILSAFE_CSS}
        
        /* Monochrome + Neon Color Grading */
        #bg {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
            filter: contrast(120%) grayscale(100%);
        }}
        
        /* Neon color overlay with color-dodge blend */
        #neon-overlay {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(135deg, 
                {color}40 0%, 
                transparent 40%,
                transparent 60%,
                #00ffff40 100%);
            mix-blend-mode: color-dodge;
            pointer-events: none;
        }}
        
        /* RGB Split Effect Layers */
        #rgb-red {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
            mix-blend-mode: screen;
            opacity: 0.5;
        }}
        
        #rgb-cyan {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
            mix-blend-mode: screen;
            opacity: 0.5;
        }}
        
        #overlay {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(180deg, 
                rgba(0,0,0,0.75) 0%, 
                transparent 30%,
                transparent 60%,
                rgba(0,0,0,0.85) 100%);
        }}
        
        #scanlines {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: repeating-linear-gradient(
                0deg,
                rgba(0, 0, 0, 0.2) 0px,
                rgba(0, 0, 0, 0.2) 1px,
                transparent 1px,
                transparent 3px
            );
            pointer-events: none;
            z-index: 30;
        }}
        
        /* Layout Flex Integration */
        #text-container {{
            position: absolute; bottom: 70px; left: 40px; right: 40px;
            z-index: 40;
            display: flex;
            flex-direction: column;
        }}
        
        #text {{
            color: white;
            font-family: '{font['header']}', {font['fallback_header']};
            font-size: 38px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 6px;
            line-height: 1.1;
            text-shadow: 
                3px 0 {color},
                -3px 0 #00ffff,
                0 0 30px {color};
        }}
        
        /* Glitch text effect */
        .glitch {{
            position: relative;
        }}
        .glitch::before, .glitch::after {{
            content: attr(data-text);
            position: absolute;
            top: 0; left: 0;
            width: 100%;
            height: 100%;
        }}
        .glitch::before {{
            color: #ff0040;
            animation: glitch-anim 2s infinite linear alternate-reverse;
            clip-path: polygon(0 0, 100% 0, 100% 35%, 0 35%);
            left: 3px;
        }}
        .glitch::after {{
            color: #00ffff;
            animation: glitch-anim 3s infinite linear alternate-reverse;
            clip-path: polygon(0 65%, 100% 65%, 100% 100%, 0 100%);
            left: -3px;
        }}
        
        @keyframes glitch-anim {{
            0%, 100% {{ transform: translate(0); }}
            20% {{ transform: translate(-4px, 3px); }}
            40% {{ transform: translate(4px, -3px); }}
            60% {{ transform: translate(-3px, 2px); }}
            80% {{ transform: translate(3px, -2px); }}
        }}
        
        #logo {{
            position: absolute; top: 35px; right: 35px;
            width: 80px; height: auto;
            filter: drop-shadow(0 0 15px {color});
            z-index: 50;
        }}
        
        #accent-bar {{
            position: absolute; bottom: 55px; left: 40px;
            width: 100px; height: 4px;
            background: linear-gradient(90deg, {color}, #00ffff);
            z-index: 40;
        }}
        
        /* SVG Data Brackets Decorators */
        .corner-deco {{
            position: absolute;
            font-family: '{font['body']}', {font['fallback_body']};
            font-size: 28px;
            font-weight: 700;
            color: var(--brand-color);
            opacity: 0.8;
            z-index: 60;
            text-shadow: 0 0 10px var(--brand-color);
        }}
        .corner-tl {{ top: 20px; left: 20px; }}
        .corner-tr {{ top: 20px; right: 20px; }}
        .corner-bl {{ bottom: 20px; left: 20px; }}
        .corner-br {{ bottom: 20px; right: 20px; }}
    </style>
    <script src="{GSAP_CDN}"></script>
</head>
<body>
    <div id="bg"></div>
    <div id="neon-overlay"></div>
    <div id="rgb-red"></div>
    <div id="rgb-cyan"></div>
    <div id="overlay"></div>
    <div id="scanlines"></div>
    
    <!-- SVG Data Brackets Decorators -->
    <span class="corner-deco corner-tl">[</span>
    <span class="corner-deco corner-tr">]</span>
    <span class="corner-deco corner-bl">+</span>
    <span class="corner-deco corner-br">+</span>
    
    <img id="logo" src="{logo_url}" onerror="this.style.display='none'">
    <div id="accent-bar"></div>
    <div id="text-container" class="variant-{layout_variant}">
        <div id="text" class="glitch {text_size_class}" data-text="{text}">{text}</div>
    </div>
    <div class="grain"></div>
    
    <script>
        // RGB Split Animation
        gsap.to("#rgb-red", {{
            x: 4, y: -2,
            duration: 0.15,
            repeat: -1,
            yoyo: true,
            ease: "steps(1)"
        }});
        
        gsap.to("#rgb-cyan", {{
            x: -4, y: 2,
            duration: 0.12,
            repeat: -1,
            yoyo: true,
            ease: "steps(1)"
        }});
        
        // Staggered Text Slide-Up
        gsap.from("#text", {{
            y: 100,
            skewY: 12,
            opacity: 0,
            duration: 0.9,
            ease: "back.out(1.5)"
        }});
        
        // Accent bar draw
        gsap.from("#accent-bar", {{
            width: 0,
            duration: 0.8,
            delay: 0.6,
            ease: "power2.out"
        }});
        
        // Logo glitch shake
        gsap.to("#logo", {{
            x: "random(-4, 4)",
            y: "random(-3, 3)",
            duration: 0.08,
            repeat: -1,
            yoyo: true,
            ease: "steps(1)"
        }});
        
        // Background intensity pulse
        gsap.to("#bg", {{
            filter: "saturate(1.6) contrast(1.35)",
            duration: 0.8,
            yoyo: true,
            repeat: -1,
            ease: "power1.inOut"
        }});
        
        // Scanline flicker
        gsap.to("#scanlines", {{
            opacity: 0.15,
            duration: 0.03,
            yoyo: true,
            repeat: -1,
            repeatDelay: 3
        }});
    </script>
</body>
</html>'''


def _editorial_template(image_url: str, logo_url: str, color: str, text: str, layout_variant: str = 'hero-center') -> str:
    """
    Modern Editorial Template - "Business Style"
    Features: Off-center broken grid layout, parallax effect, masked text reveal,
    mix-blend-mode: difference for text readability, elegant typography
    """
    font = get_font_pairing("editorial")
    text_size_class = "text-huge" if len(text) < 30 else ""
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="{font['link']}" rel="stylesheet">
    <style>
        :root {{
            --brand-color: {color};
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body, html {{ 
            width: 100%; height: 100%; overflow: hidden; 
            font-family: '{font['body']}', {font['fallback_body']};
            background: #111;
        }}
        
        {GLOBAL_GRAIN_CSS}
        {GLOBAL_LAYOUT_CSS}
        {GLOBAL_FAILSAFE_CSS}
        
        /* Off-Center Broken Grid Layout */
        #image-panel {{
            position: absolute; top: 0; left: -10%; width: 90%; height: 70%;
            overflow: hidden;
        }}
        
        #bg {{
            position: absolute; top: -10%; left: 0; width: 120%; height: 130%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
        }}
        
        /* Overlapping text panel with negative margin */
        #text-panel {{
            position: absolute; bottom: 10%; right: 5%; width: 60%;
            margin-left: -50px;
            background: rgba(17, 17, 17, 0.85);
            backdrop-filter: blur(10px);
            padding: 40px 50px;
            z-index: 20;
            display: flex;
            flex-direction: column;
        }}
        
        #text-mask {{
            overflow: hidden;
            height: auto;
        }}
        
        /* Text with difference blend for visibility on any background */
        #text {{
            color: white;
            font-family: '{font['header']}', {font['fallback_header']};
            font-size: 38px;
            font-weight: 400;
            font-style: italic;
            line-height: 1.2;
            letter-spacing: 1px;
            mix-blend-mode: difference;
        }}
        
        #divider {{
            width: 80px; height: 2px;
            background: var(--brand-color);
            margin-top: 25px;
        }}
        
        #logo {{
            position: absolute; top: 30px; right: 40px;
            width: 85px; height: auto;
            z-index: 50;
        }}
        
        #frame {{
            position: absolute;
            top: 20px; left: -10%; right: 30%;
            height: calc(70% - 20px);
            border: 1px solid rgba(255,255,255,0.15);
            pointer-events: none;
            z-index: 10;
        }}
        
        #gradient-fade {{
            position: absolute; left: 0; bottom: 30%; width: 100%; height: 20%;
            background: linear-gradient(to top, #111 0%, transparent 100%);
            z-index: 5;
        }}
        
        #accent {{
            position: absolute; left: 50px; bottom: 50%;
            width: 3px; height: 60px;
            background: var(--brand-color);
            transform: translateY(50%);
        }}
    </style>
    <script src="{GSAP_CDN}"></script>
</head>
<body>
    <div id="image-panel">
        <div id="bg"></div>
        <div id="frame"></div>
        <div id="gradient-fade"></div>
    </div>
    <div id="accent"></div>
    <div id="text-panel" class="variant-{layout_variant}">
        <div id="text-mask">
            <div id="text" class="{text_size_class}">{text}</div>
        </div>
        <div id="divider"></div>
    </div>
    <img id="logo" src="{logo_url}" onerror="this.style.display='none'">
    <div class="grain"></div>
    
    <script>
        // Parallax: Background moves slower than text
        gsap.to("#bg", {{
            y: "-8%",
            duration: 12,
            ease: "none"
        }});
        
        // Masked Text Reveal - Rising from below
        gsap.from("#text", {{
            y: "100%",
            duration: 1.5,
            delay: 0.8,
            ease: "power3.out"
        }});
        
        // Divider line draw
        gsap.from("#divider", {{
            width: 0,
            duration: 1.2,
            delay: 1.2,
            ease: "power2.inOut"
        }});
        
        // Accent bar height animate
        gsap.from("#accent", {{
            height: 0,
            duration: 1,
            delay: 0.5,
            ease: "power2.out"
        }});
        
        // Logo fade
        gsap.from("#logo", {{
            opacity: 0,
            y: -20,
            duration: 1.5,
            delay: 0.4
        }});
        
        // Frame fade
        gsap.from("#frame", {{
            opacity: 0,
            duration: 2.5
        }});
    </script>
</body>
</html>'''


def _minimal_template(image_url: str, logo_url: str, color: str, text: str, layout_variant: str = 'hero-center') -> str:
    """
    Minimal Template - "Clean/Wellness Style"
    Features: Montserrat font, subtle scale, floating elements, clean fades, accent lines
    """
    font = get_font_pairing("minimal")
    text_size_class = "text-huge" if len(text) < 30 else ""
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="{font['link']}" rel="stylesheet">
    <style>
        :root {{
            --brand-color: {color};
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body, html {{ 
            width: 100%; height: 100%; overflow: hidden; 
            font-family: '{font['body']}', {font['fallback_body']};
        }}
        
        {GLOBAL_GRAIN_CSS}
        {GLOBAL_LAYOUT_CSS}
        {GLOBAL_FAILSAFE_CSS}
        .grain {{ opacity: 0.04; }}
        
        #bg {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
        }}
        
        #gradient {{
            position: absolute; bottom: 0; left: 0; right: 0;
            height: 55%;
            background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 100%);
        }}
        
        /* Layout Flex Integration */
        #container {{
            position: absolute; bottom: 60px; left: 40px; right: 40px;
            display: flex;
            flex-direction: column;
        }}
        
        #text {{
            color: white;
            font-family: '{font['header']}', {font['fallback_header']};
            font-size: 26px;
            font-weight: 300;
            line-height: 1.55;
            letter-spacing: 0.3px;
        }}
        
        #logo {{
            position: absolute; top: 30px; right: 30px;
            width: 65px; height: auto;
            opacity: 0.95;
        }}
        
        #accent-line {{
            position: absolute; bottom: 50px; left: 40px;
            width: 50px; height: 2px;
            background: var(--brand-color);
        }}
        
        #corner-accent {{
            position: absolute; top: 30px; left: 30px;
            width: 25px; height: 25px;
            border-left: 2px solid var(--brand-color);
            border-top: 2px solid var(--brand-color);
        }}
    </style>
    <script src="{GSAP_CDN}"></script>
</head>
<body>
    <div id="bg"></div>
    <div id="gradient"></div>
    <img id="logo" src="{logo_url}" onerror="this.style.display='none'">
    <div id="corner-accent"></div>
    <div id="accent-line"></div>
    <div id="container" class="variant-{layout_variant}">
        <div id="text" class="{text_size_class}">{text}</div>
    </div>
    <div class="grain"></div>
    
    <script>
        // Soft Ken Burns
        gsap.to("#bg", {{
            scale: 1.06,
            duration: 12,
            ease: "none"
        }});
        
        // Floating text
        gsap.to("#text", {{
            y: -10,
            duration: 3,
            yoyo: true,
            repeat: -1,
            ease: "sine.inOut"
        }});
        
        // Text fade in
        gsap.from("#text", {{
            opacity: 0,
            y: 30,
            duration: 1.8,
            ease: "power2.out"
        }});
        
        // Logo soft entrance
        gsap.from("#logo", {{
            opacity: 0,
            rotation: -8,
            duration: 1.4,
            ease: "power2.out"
        }});
        
        // Accent line draw
        gsap.from("#accent-line", {{
            width: 0,
            duration: 1.2,
            delay: 0.5,
            ease: "power2.out"
        }});
        
        // Corner accent
        gsap.from("#corner-accent", {{
            opacity: 0,
            scale: 0.5,
            duration: 1,
            delay: 0.3
        }});
    </script>
</body>
</html>'''


def _aurora_template(image_url: str, logo_url: str, color: str, text: str, luminance_mode: str = 'dark', layout_variant: str = 'hero-center') -> str:
    """
    Aurora Template - "Apple" Look
    Features: Canvas blob background with 3 merging color blobs using sine waves,
    Variable font (Inter) with font-weight animation 100->900 on reveal,
    Ultra-premium frosted glass-morphism containers
    """
    # Determine text color based on luminance
    text_color = '#FFFFFF' if luminance_mode == 'dark' else '#111111'
    text_size_class = "text-huge" if len(text) < 30 else ""
    
    # Parse brand color for blob generation
    hex_color = color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    else:
        r, g, b = 100, 100, 255
    
    # Generate complementary blob colors
    blob_color_1 = f"rgba({r}, {g}, {b}, 0.8)"
    blob_color_2 = f"rgba({min(r+60, 255)}, {min(g+40, 255)}, {b}, 0.7)"
    blob_color_3 = f"rgba({r}, {min(g+60, 255)}, {min(b+40, 255)}, 0.6)"
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --brand-color: {color};
            --text-color: {text_color};
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body, html {{ 
            width: 100%; height: 100%; overflow: hidden; 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0a0a0a;
        }}
        
        {GLOBAL_GRAIN_CSS}
        {GLOBAL_LAYOUT_CSS}
        .grain {{ opacity: 0.03; }}
        
        /* Aurora Canvas Background */
        #aurora {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            z-index: 1;
        }}
        
        /* Background Image Layer */
        #bg {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
            opacity: 0.4;
            z-index: 0;
        }}
        
        /* Glass-Morphism Container */
        #glass-container {{
            position: absolute; bottom: 0; left: 0; right: 0;
            padding: 50px 40px 60px;
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border-top: 1px solid rgba(255, 255, 255, 0.12);
            z-index: 20;
            display: flex;
            flex-direction: column;
            min-height: 35%;
        }}
        
        /* Variable Font Text */
        #text {{
            color: var(--text-color);
            font-size: 36px;
            font-weight: 100;
            line-height: 1.3;
            letter-spacing: -0.02em;
        }}
        
        #logo {{
            position: absolute; top: 35px; right: 35px;
            width: 90px; height: auto;
            filter: drop-shadow(0 4px 20px rgba(0,0,0,0.3));
            z-index: 50;
        }}
        
        #brand-orb {{
            position: absolute; top: 20%; right: 10%;
            width: 200px; height: 200px;
            background: radial-gradient(circle, {color}60 0%, transparent 70%);
            border-radius: 50%;
            filter: blur(40px);
            z-index: 5;
        }}
    </style>
    <script src="{GSAP_CDN}"></script>
</head>
<body>
    <div id="bg"></div>
    <canvas id="aurora"></canvas>
    <div id="brand-orb"></div>
    <img id="logo" src="{logo_url}" onerror="this.style.display='none'">
    <div id="glass-container" class="variant-{layout_variant}">
        <div id="text" class="{text_size_class}">{text}</div>
    </div>
    <div class="grain"></div>
    
    <script>
        // Aurora Blob Animation - 3 Color Blobs with Sine Wave Movement
        const canvas = document.getElementById('aurora');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const blobs = [
            {{ x: canvas.width * 0.3, y: canvas.height * 0.4, radius: 180, color: '{blob_color_1}', speedX: 0.8, speedY: 0.6, phase: 0 }},
            {{ x: canvas.width * 0.6, y: canvas.height * 0.3, radius: 150, color: '{blob_color_2}', speedX: -0.6, speedY: 0.9, phase: 2 }},
            {{ x: canvas.width * 0.5, y: canvas.height * 0.6, radius: 200, color: '{blob_color_3}', speedX: 0.5, speedY: -0.7, phase: 4 }}
        ];
        
        let time = 0;
        
        function animateBlobs() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            blobs.forEach(blob => {{
                // Sine wave movement for organic motion
                const offsetX = Math.sin(time * blob.speedX + blob.phase) * 80;
                const offsetY = Math.cos(time * blob.speedY + blob.phase) * 60;
                
                const gradient = ctx.createRadialGradient(
                    blob.x + offsetX, blob.y + offsetY, 0,
                    blob.x + offsetX, blob.y + offsetY, blob.radius
                );
                gradient.addColorStop(0, blob.color);
                gradient.addColorStop(1, 'transparent');
                
                ctx.beginPath();
                ctx.arc(blob.x + offsetX, blob.y + offsetY, blob.radius, 0, Math.PI * 2);
                ctx.fillStyle = gradient;
                ctx.fill();
            }});
            
            time += 0.015;
            requestAnimationFrame(animateBlobs);
        }}
        animateBlobs();
        
        // Variable Font Weight Animation - 100 to 900 on reveal
        gsap.fromTo("#text", 
            {{ fontWeight: 100, opacity: 0, y: 40 }},
            {{ fontWeight: 900, opacity: 1, y: 0, duration: 2.5, ease: "power3.out" }}
        );
        
        // Glass container rise
        gsap.from("#glass-container", {{
            y: 120, opacity: 0, duration: 1.8, ease: "power3.out", delay: 0.2
        }});
        
        // Logo fade
        gsap.from("#logo", {{
            opacity: 0, scale: 0.9, duration: 1.5, delay: 0.4, ease: "power2.out"
        }});
        
        // Brand orb pulse
        gsap.to("#brand-orb", {{
            scale: 1.2, opacity: 0.6, duration: 4, yoyo: true, repeat: -1, ease: "sine.inOut"
        }});
    </script>
</body>
</html>'''


def _gridlock_template(image_url: str, logo_url: str, color: str, text: str, luminance_mode: str = 'dark', layout_variant: str = 'hero-center') -> str:
    """
    Gridlock Template - "High-Tech" Tron Look
    Features: Moving SVG perspective grid on floor (Tron style),
    Infinite scroll towards viewer, neon glow effects,
    Glass-morphism UI with premium frosted glass
    """
    # Determine text color based on luminance
    text_color = '#FFFFFF' if luminance_mode == 'dark' else '#111111'
    text_size_class = "text-huge" if len(text) < 30 else ""
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --brand-color: {color};
            --text-color: {text_color};
            --grid-color: {color};
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body, html {{ 
            width: 100%; height: 100%; overflow: hidden; 
            font-family: 'Orbitron', 'Arial Black', sans-serif;
            background: #050510;
        }}
        
        {GLOBAL_GRAIN_CSS}
        {GLOBAL_LAYOUT_CSS}
        .grain {{ opacity: 0.05; }}
        
        /* Perspective Grid Container */
        #grid-container {{
            position: absolute; bottom: 0; left: 0; width: 100%; height: 60%;
            perspective: 400px;
            overflow: hidden;
            z-index: 1;
        }}
        
        #grid {{
            position: absolute; bottom: 0; left: -50%; width: 200%; height: 200%;
            background-image: 
                linear-gradient(var(--grid-color) 1px, transparent 1px),
                linear-gradient(90deg, var(--grid-color) 1px, transparent 1px);
            background-size: 60px 60px;
            transform: rotateX(75deg);
            transform-origin: center bottom;
            animation: gridScroll 3s linear infinite;
            opacity: 0.4;
        }}
        
        @keyframes gridScroll {{
            0% {{ background-position: 0 0; }}
            100% {{ background-position: 0 60px; }}
        }}
        
        /* Horizon Glow */
        #horizon-glow {{
            position: absolute; bottom: 40%; left: 0; width: 100%; height: 200px;
            background: linear-gradient(to top, {color}40 0%, transparent 100%);
            z-index: 2;
        }}
        
        /* Background Image */
        #bg {{
            position: absolute; top: 0; left: 0; width: 100%; height: 50%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center top;
            mask-image: linear-gradient(to bottom, black 60%, transparent 100%);
            -webkit-mask-image: linear-gradient(to bottom, black 60%, transparent 100%);
            z-index: 0;
        }}
        
        /* Glass-Morphism Text Container */
        #glass-panel {{
            position: absolute; top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 80%;
            max-width: 600px;
            padding: 40px 60px;
            background: rgba(255, 255, 255, 0.06);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            z-index: 30;
            display: flex;
            flex-direction: column;
        }}
        
        #text {{
            color: var(--text-color);
            font-size: 28px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 4px;
            text-shadow: 0 0 30px var(--brand-color), 0 0 60px var(--brand-color);
        }}
        
        #logo {{
            position: absolute; top: 30px; right: 30px;
            width: 80px; height: auto;
            filter: drop-shadow(0 0 20px var(--brand-color));
            z-index: 50;
        }}
        
        /* Neon Accent Lines */
        .neon-line {{
            position: absolute;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--brand-color), transparent);
            box-shadow: 0 0 10px var(--brand-color), 0 0 20px var(--brand-color);
            z-index: 40;
        }}
        .neon-line-top {{ top: 25%; left: 10%; width: 30%; }}
        .neon-line-bottom {{ bottom: 25%; right: 10%; width: 25%; }}
        
        /* Corner Markers */
        .corner-marker {{
            position: absolute;
            width: 20px; height: 20px;
            border-color: var(--brand-color);
            z-index: 45;
        }}
        .cm-tl {{ top: 20px; left: 20px; border-top: 2px solid; border-left: 2px solid; }}
        .cm-tr {{ top: 20px; right: 20px; border-top: 2px solid; border-right: 2px solid; }}
        .cm-bl {{ bottom: 20px; left: 20px; border-bottom: 2px solid; border-left: 2px solid; }}
        .cm-br {{ bottom: 20px; right: 20px; border-bottom: 2px solid; border-right: 2px solid; }}
    </style>
    <script src="{GSAP_CDN}"></script>
</head>
<body>
    <div id="bg"></div>
    <div id="grid-container">
        <div id="grid"></div>
    </div>
    <div id="horizon-glow"></div>
    
    <div class="neon-line neon-line-top"></div>
    <div class="neon-line neon-line-bottom"></div>
    
    <div class="corner-marker cm-tl"></div>
    <div class="corner-marker cm-tr"></div>
    <div class="corner-marker cm-bl"></div>
    <div class="corner-marker cm-br"></div>
    
    <img id="logo" src="{logo_url}" onerror="this.style.display='none'">
    <div id="glass-panel" class="variant-{layout_variant}">
        <div id="text" class="{text_size_class}">{text}</div>
    </div>
    <div class="grain"></div>
    
    <script>
        // Text reveal with glitch effect
        gsap.from("#text", {{
            opacity: 0, y: 30, skewX: -5, duration: 1.2, ease: "power3.out"
        }});
        
        // Glass panel scale in
        gsap.from("#glass-panel", {{
            scale: 0.9, opacity: 0, duration: 1.5, ease: "back.out(1.2)"
        }});
        
        // Neon lines draw
        gsap.from(".neon-line", {{
            width: 0, duration: 1.2, stagger: 0.3, ease: "power2.out", delay: 0.5
        }});
        
        // Corner markers fade
        gsap.from(".corner-marker", {{
            opacity: 0, scale: 0.5, duration: 0.8, stagger: 0.1, delay: 0.8
        }});
        
        // Logo glow pulse
        gsap.to("#logo", {{
            filter: "drop-shadow(0 0 30px var(--brand-color))",
            duration: 2, yoyo: true, repeat: -1, ease: "sine.inOut"
        }});
        
        // Horizon glow intensity
        gsap.to("#horizon-glow", {{
            opacity: 0.6, duration: 3, yoyo: true, repeat: -1, ease: "sine.inOut"
        }});
    </script>
</body>
</html>'''


def _scrapbook_template(image_url: str, logo_url: str, color: str, text: str, layout_variant: str = 'hero-center') -> str:
    """
    Scrapbook Template - "Organic/Tactile"
    Features: Torn edges, stop motion animation, tape effect, handwritten font.
    """
    font = get_font_pairing("scrapbook")
    text_size_class = "text-huge" if len(text) < 30 else ""
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="{font['link']}" rel="stylesheet">
    <style>
        :root {{
            --brand-color: {color};
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body, html {{ 
            width: 100%; height: 100%; overflow: hidden; 
            font-family: '{font['body']}', {font['fallback_body']};
            background: #f4f1ea; /* Soft paper white */
        }}
        
        {GLOBAL_GRAIN_CSS}
        {GLOBAL_LAYOUT_CSS}
        
        /* Container for stop-motion effect */
        #container {{
            position: relative;
            width: 100%; height: 100%;
        }}

        #photo-card {{
            position: absolute; top: 15%; left: 10%; width: 80%; height: 50%;
            background: white;
            padding: 15px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.15);
            transform: rotate(-2deg);
        }}
        
        #photo {{
            width: 100%; height: 100%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
            /* Simple jagged clip-path to simulate torn edge */
            clip-path: polygon(
                0% 0%, 100% 0%, 100% 100%, 
                95% 98%, 90% 100%, 85% 98%, 80% 100%, 75% 98%, 70% 100%, 65% 98%, 60% 100%, 55% 98%, 
                50% 100%, 45% 98%, 40% 100%, 35% 98%, 30% 100%, 25% 98%, 20% 100%, 15% 98%, 10% 100%, 5% 98%, 
                0% 100%
            );
        }}
        
        /* Washi Tape CSS */
        .tape {{
            position: absolute;
            width: 120px; height: 35px;
            background-color: var(--brand-color);
            opacity: 0.8;
            z-index: 10;
        }}
        .tape-tl {{ top: -15px; left: -30px; transform: rotate(-30deg); }}
        .tape-br {{ bottom: -15px; right: -30px; transform: rotate(-30deg); }}
        
        #text-scrap {{
            position: absolute; bottom: 15%; right: 10%; width: 70%;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px 30px;
            font-family: '{font['header']}', {font['fallback_header']};
            font-size: 32px;
            color: #222;
            line-height: 1.4;
            transform: rotate(2deg);
            box-shadow: 2px 4px 8px rgba(0,0,0,0.1);
            border-radius: 2px;
            /* Layout Flex Integration */
            display: flex;
            flex-direction: column;
        }}
        
        #logo {{
            position: absolute; top: 30px; right: 30px;
            width: 80px; height: auto;
            transform: rotate(5deg);
        }}
        
        /* Doodles/Decor */
        .doodle {{
            position: absolute;
            border: 3px solid var(--brand-color);
            border-radius: 50%;
            z-index: 5;
            opacity: 0.6;
        }}
        .doodle-1 {{ top: 10%; right: 20%; width: 40px; height: 40px; border-radius: 50%; }}
        .doodle-2 {{ bottom: 10%; left: 15%; width: 60px; height: 6px; border-radius: 2px; border: none; background: var(--brand-color); }}

    </style>
    <script src="{GSAP_CDN}"></script>
</head>
<body>
    <div id="container">
        <div id="photo-card">
            <div id="photo"></div>
            <div class="tape tape-tl"></div>
            <div class="tape tape-br"></div>
        </div>
        
        <div class="doodle doodle-1"></div>
        <div class="doodle doodle-2"></div>
        
        <div id="text-scrap" class="variant-{layout_variant} {text_size_class}">{text}</div>
        <img id="logo" src="{logo_url}" onerror="this.style.display='none'">
    </div>
    <div class="grain"></div>
    
    <script>
        // Jitter / Stop Motion Effect
        function jitter(target, intensity) {{
            gsap.to(target, {{
                rotation: "random(-" + intensity + ", " + intensity + ")",
                x: "random(-1, 1)",
                y: "random(-1, 1)",
                duration: 0.2,
                repeat: -1,
                yoyo: true,
                ease: "steps(1)"
            }});
        }}
        
        jitter("#photo-card", 1.5);
        jitter("#text-scrap", 1);
        jitter("#logo", 2);
        
        // Entrance Animations
        gsap.from("#photo-card", {{
            y: -50, opacity: 0, rotation: -10, duration: 1, ease: "back.out"
        }});
        
        gsap.from("#text-scrap", {{
            y: 50, opacity: 0, rotation: 5, duration: 1, delay: 0.3, ease: "back.out"
        }});
        
        gsap.from(".tape", {{
            scaleX: 0, duration: 0.5, delay: 0.8, ease: "power2.out"
        }});
    </script>
</body>
</html>'''


def _pop_template(image_url: str, logo_url: str, color: str, text: str, layout_variant: str = 'hero-center') -> str:
    """
    Pop Template - "High Energy"
    Features: Bold borders, hard shadows, marquee text, high contrast.
    """
    font = get_font_pairing("pop")
    text_size_class = "text-huge" if len(text) < 30 else ""
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="{font['link']}" rel="stylesheet">
    <style>
        :root {{
            --brand-color: {color};
            --black: #000000;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body, html {{ 
            width: 100%; height: 100%; overflow: hidden; 
            font-family: '{font['body']}', {font['fallback_body']};
            background: white;
        }}
        
        {GLOBAL_GRAIN_CSS}
        {GLOBAL_LAYOUT_CSS}
        
        /* Bold Container */
        #main-image {{
            position: absolute; top: 15%; left: 5%; width: 90%; height: 50%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
            border: 4px solid var(--black);
            box-shadow: 8px 8px 0px var(--black);
            z-index: 10;
        }}
        
        #bg-pattern {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-image: radial-gradient(var(--brand-color) 20%, transparent 20%);
            background-size: 20px 20px;
            opacity: 0.15;
            z-index: 0;
        }}
        
        /* Marquee Bar */
        .marquee-container {{
            position: absolute; bottom: 20%; left: 0; width: 100%;
            background: var(--brand-color);
            border-top: 4px solid var(--black);
            border-bottom: 4px solid var(--black);
            padding: 15px 0;
            transform: rotate(-3deg) scale(1.1);
            z-index: 20;
            overflow: hidden;
            white-space: nowrap;
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            /* Marquee layout is fixed by nature, but we can adjust scaling for text huge */
        }}
        
        .marquee-text {{
            display: inline-block;
            font-family: '{font['header']}', {font['fallback_header']};
            font-size: 36px;
            font-weight: 900;
            color: white;
            text-transform: uppercase;
            padding-left: 100%;
            animation: marquee 8s linear infinite;
            -webkit-text-stroke: 2px var(--black);
        }}
        
        .text-huge {{
            font-size: 5rem;
        }}
        
        @keyframes marquee {{
            0% {{ transform: translate(0, 0); }}
            100% {{ transform: translate(-100%, 0); }}
        }}
        
        /* Sticker Logo */
        #logo {{
            position: absolute; top: 20px; right: 20px;
            width: 90px; height: auto;
            background: white;
            border: 3px solid var(--black);
            border-radius: 50%;
            padding: 5px;
            z-index: 50;
            box-shadow: 4px 4px 0px var(--black);
        }}
        
        /* Floating Shapes */
        .shape {{
            position: absolute;
            background: var(--brand-color);
            border: 3px solid var(--black);
            z-index: 5;
        }}
        .shape-circle {{ bottom: 10%; left: 10%; width: 50px; height: 50px; border-radius: 50%; }}
        .shape-square {{ top: 10%; right: 30%; width: 40px; height: 40px; transform: rotate(15deg); }}
        
    </style>
    <script src="{GSAP_CDN}"></script>
</head>
<body>
    <div id="bg-pattern"></div>
    <div id="main-image"></div>
    
    <div class="marquee-container variant-{layout_variant}">
        <div class="marquee-text {text_size_class}">{text} &nbsp;&bull;&nbsp; {text} &nbsp;&bull;&nbsp; {text} &nbsp;&bull;&nbsp;</div>
    </div>
    
    <div class="shape shape-circle"></div>
    <div class="shape shape-square"></div>
    
    <img id="logo" src="{logo_url}" onerror="this.style.display='none'">
    <div class="grain"></div>
    
    <script>
        // Pop Animations
        gsap.from("#main-image", {{
            scale: 0, rotation: 180, duration: 0.8, ease: "back.out(1.2)"
        }});
        
        gsap.from(".marquee-container", {{
            x: "-100%", duration: 0.8, delay: 0.3, ease: "power4.out"
        }});
        
        gsap.from("#logo", {{
            scale: 0, duration: 0.5, delay: 0.6, ease: "elastic.out(1, 0.5)"
        }});
        
        // Flash Colors
        gsap.to(".shape", {{
            backgroundColor: "#fff",
            duration: 0.2,
            repeat: -1,
            yoyo: true,
            ease: "steps(1)",
            repeatDelay: 0.5
        }});
    </script>
</body>
</html>'''


def _swiss_template(image_url: str, logo_url: str, color: str, text: str, layout_variant: str = 'hero-center') -> str:
    """
    Swiss Template - "Trust/Corporate"
    Features: Strict grid, horizontal lines, Helvetica/Inter, orderly animation.
    """
    font = get_font_pairing("swiss")
    text_size_class = "text-huge" if len(text) < 30 else ""
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="{font['link']}" rel="stylesheet">
    <style>
        :root {{
            --brand-color: {color};
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body, html {{ 
            width: 100%; height: 100%; overflow: hidden; 
            font-family: '{font['body']}', {font['fallback_body']};
            background: #ffffff;
            color: #111;
        }}
        
        {GLOBAL_GRAIN_CSS}
        {GLOBAL_LAYOUT_CSS}
        
        /* Grid Layout */
        .grid-container {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            grid-template-rows: 60px 1fr 1fr 60px;
            width: 100%; height: 100%;
            padding: 40px;
        }}
        
        .header-line {{
            grid-column: 1 / -1;
            border-top: 2px solid #111;
            padding-top: 10px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        
        #brand-name {{
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        #logo {{
            width: 40px; height: auto;
        }}
        
        .main-content {{
            grid-column: 1 / 3;
            grid-row: 2 / 4;
            display: flex;
            flex-direction: column;
            justify-content: center;
            border-top: 1px solid #ddd;
            padding-right: 40px;
            /* Layout variants apply here to align text within this cell */
        }}
        
        #headline {{
            font-family: '{font['header']}', {font['fallback_header']};
            font-size: 48px;
            font-weight: 700;
            line-height: 1.1;
            letter-spacing: -1px;
            margin-bottom: 20px;
        }}
        
        .text-huge {{
            font-size: 5rem;
        }}
        
        .image-col {{
            grid-column: 3 / 4;
            grid-row: 2 / 4;
            border-top: 1px solid #111;
            position: relative;
            overflow: hidden;
        }}
        
        #product-image {{
            width: 100%; height: 100%;
            background-image: url('{image_url}');
            background-size: cover;
            background-position: center;
        }}
        
        .footer-line {{
            grid-column: 1 / -1;
            grid-row: 4;
            border-top: 1px solid #111;
            margin-top: 20px;
            display: flex;
            align-items: center;
        }}
        
        .accent-block {{
            width: 40px; height: 40px;
            background: var(--brand-color);
            margin-right: 20px;
        }}

    </style>
    <script src="{GSAP_CDN}"></script>
</head>
<body>
    <div class="grid-container">
        <div class="header-line">
            <div id="brand-name">Collection 2026</div>
            <img id="logo" src="{logo_url}" onerror="this.style.display='none'">
        </div>
        
        <div class="main-content variant-{layout_variant}">
            <div id="headline" class="{text_size_class}">{text}</div>
        </div>
        
        <div class="image-col">
            <div id="product-image"></div>
        </div>
        
        <div class="footer-line">
            <div class="accent-block"></div>
            <div style="font-size: 12px;">DESIGN SYSTEM V1.0</div>
        </div>
    </div>
    <div class="grain"></div>
    
    <script>
        // Swiss Grid Animations
        gsap.from(".header-line", {{
            width: 0, duration: 1.2, ease: "power3.inOut"
        }});
        
        gsap.from(".footer-line", {{
            width: 0, duration: 1.2, delay: 0.2, ease: "power3.inOut"
        }});
        
        gsap.from("#product-image", {{
            y: "100%", duration: 1.5, delay: 0.4, ease: "power4.out"
        }});
        
        gsap.from("#headline", {{
            x: -50, opacity: 0, duration: 1, delay: 0.8, ease: "power2.out"
        }});
        
        gsap.from(".accent-block", {{
            scale: 0, duration: 0.5, delay: 1.2, ease: "back.out"
        }});
    </script>
</body>
</html>'''


# Template metadata for tone matching
TEMPLATE_TONES = {
    "luxury": ["luxury", "premium", "fashion", "elegant", "sophisticated", "coffee", "beauty"],
    "cyber": ["innovative", "tech", "gaming", "futuristic", "bold", "edgy", "sneaker", "hype"],
    "editorial": ["editorial", "publishing", "magazine", "artistic", "refined", "business", "professional"],
    "minimal": ["minimal", "calm", "wellness", "services", "clean", "simple"],
    "aurora": ["apple", "modern", "gradient", "flowing", "organic", "sleek", "premium"],
    "gridlock": ["tron", "grid", "neon", "cyberpunk", "retro", "synthwave", "matrix"],
    "scrapbook": ["organic", "tactile", "craft", "handmade", "fun", "warm", "food", "travel"],
    "pop": ["bold", "loud", "energetic", "sale", "event", "youth", "playful"],
    "swiss": ["professional", "trust", "clean", "finance", "law", "b2b", "corporate"],
}

# V6.0: Template Complexity Tiers for performance-aware selection
# High complexity templates have canvas-based animations (particles, blobs, grids)
# that increase video file size and may cause frame drops on lower-end devices
TEMPLATE_COMPLEXITY = {
    "luxury": "high",      # Has canvas particles + light leaks
    "cyber": "high",       # Has RGB split + glitch effects + scanlines
    "aurora": "high",      # Has canvas blob animation
    "gridlock": "high",    # Has SVG perspective grid animation
    "editorial": "medium", # Has parallax + masked text reveal
    "scrapbook": "medium", # Has torn edges + stop motion
    "pop": "medium",       # Has marquee text + hard shadows
    "minimal": "low",      # Simple fades and scales
    "swiss": "low"         # Orderly, simple animations
}

# V6.0: Industry-to-Template mapping for smarter defaults
INDUSTRY_TEMPLATE_MAP = {
    # Fashion & Beauty
    "fashion": "luxury",
    "beauty": "luxury", 
    "cosmetics": "luxury",
    "jewelry": "luxury",
    # Technology
    "technology": "cyber",
    "software": "aurora",
    "gaming": "cyber",
    "electronics": "gridlock",
    # Professional Services
    "finance": "swiss",
    "legal": "swiss",
    "consulting": "editorial",
    "b2b": "swiss",
    # Food & Hospitality
    "restaurant": "scrapbook",
    "food": "scrapbook",
    "cafe": "luxury",
    "travel": "scrapbook",
    # Health & Wellness
    "wellness": "minimal",
    "fitness": "pop",
    "healthcare": "minimal",
    # Retail & E-commerce
    "retail": "pop",
    "ecommerce": "pop",
    "sale": "pop",
    # Creative
    "art": "editorial",
    "photography": "editorial",
    "design": "aurora",
}

# List of all available templates for random selection
MOTION_TEMPLATES = ["luxury", "cyber", "editorial", "minimal", "aurora", "gridlock", "scrapbook", "pop", "swiss"]



def get_template_for_tone(tone: str) -> str:
    """
    Returns best template name for the given brand tone.
    """
    tone_lower = tone.lower()
    for template_name, tone_keywords in TEMPLATE_TONES.items():
        if any(keyword in tone_lower for keyword in tone_keywords):
            return template_name
    return "minimal"  # Safe default


def get_random_template() -> str:
    """
    Returns a random template name for variety.
    """
    import random
    return random.choice(MOTION_TEMPLATES)


def get_optimized_template(
    brand_dna: dict = None,
    goal: str = "",
    tone: str = "",
    channel: str = "",
    prefer_low_complexity: bool = False
) -> str:
    """
    V6.0: Optimized template selection with industry-awareness and complexity filtering.
    
    Priority order:
    1. Explicit brand_dna["preferred_template"] (user override)
    2. Industry-specific mapping from INDUSTRY_TEMPLATE_MAP
    3. Tone matching from TEMPLATE_TONES
    4. Random from filtered pool (complexity-aware)
    
    Args:
        brand_dna: Brand DNA dict (may contain 'industry', 'preferred_template')
        goal: Campaign goal text for keyword extraction
        tone: Tone string (e.g., "professional", "energetic")
        channel: Target channel (affects complexity preference)
        prefer_low_complexity: If True, avoid high-complexity templates
        
    Returns:
        Template name string
    """
    import random
    
    brand_dna = brand_dna or {}
    
    # 1. User Override - highest priority
    if brand_dna.get("preferred_template") in MOTION_TEMPLATES:
        return brand_dna["preferred_template"]
    
    # Determine if we should prefer lower complexity (TikTok, etc.)
    video_heavy_channels = ["tiktok", "youtube_shorts", "instagram_story", "facebook_story"]
    if channel.lower() in video_heavy_channels:
        prefer_low_complexity = True
    
    # Build candidate pool based on complexity
    if prefer_low_complexity:
        # Prefer low/medium complexity for video channels (smaller files, smoother playback)
        candidate_templates = [t for t in MOTION_TEMPLATES if TEMPLATE_COMPLEXITY.get(t) != "high"]
    else:
        candidate_templates = MOTION_TEMPLATES.copy()
    
    # 2. Industry Mapping
    industry = brand_dna.get("industry", "").lower()
    if industry in INDUSTRY_TEMPLATE_MAP:
        matched = INDUSTRY_TEMPLATE_MAP[industry]
        if matched in candidate_templates:
            return matched
        # If complexity filtering excluded it, pick from candidates instead
    
    # 3. Tone Matching (improved: 70% chance instead of 40%)
    if tone and random.random() < 0.70:
        matched = get_template_for_tone(tone)
        if matched in candidate_templates:
            return matched
    
    # 4. Goal keyword analysis
    goal_lower = goal.lower()
    for template_name, keywords in TEMPLATE_TONES.items():
        if template_name in candidate_templates:
            if any(kw in goal_lower for kw in keywords):
                return template_name
    
    # 5. Random from candidates
    return random.choice(candidate_templates) if candidate_templates else "minimal"


def get_templates_by_complexity(complexity: str) -> list:
    """
    Returns list of templates matching the given complexity tier.
    
    Args:
        complexity: 'low', 'medium', or 'high'
        
    Returns:
        List of template names
    """
    return [t for t, c in TEMPLATE_COMPLEXITY.items() if c == complexity]
