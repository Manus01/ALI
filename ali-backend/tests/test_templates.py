
import unittest
from app.core import templates

class TestTemplates(unittest.TestCase):

    def test_font_pairings(self):
        """Verify FONT_PAIRINGS structure and content."""
        self.assertIn("luxury", templates.FONT_PAIRINGS)
        self.assertIn("cyber", templates.FONT_PAIRINGS)
        self.assertIn("header", templates.FONT_PAIRINGS["luxury"])
        self.assertIn("body", templates.FONT_PAIRINGS["luxury"])
        self.assertIn("link", templates.FONT_PAIRINGS["luxury"])

    def test_get_font_pairing(self):
        """Verify font pairing retrieval."""
        font = templates.get_font_pairing("luxury")
        self.assertEqual(font["header"], "Playfair Display")
        self.assertIn("body", font)

    def test_smart_sizing(self):
        """Verify text-huge class injection for short text."""
        short_text = "Short Headline"
        long_text = "This is a much longer headline that should not get the huge class"
        
        html_short = templates._luxury_template("img.jpg", "logo.png", "#000", short_text)
        self.assertIn('class="text-huge"', html_short)
        
        html_long = templates._luxury_template("img.jpg", "logo.png", "#000", long_text)
        self.assertNotIn('class="text-huge"', html_long)

    def test_layout_variants(self):
        """Verify layout variant class injection."""
        variant = "editorial-left"
        html = templates._luxury_template("img.jpg", "logo.png", "#000", "Text", layout_variant=variant)
        self.assertIn(f"variant-{variant}", html)
        
        html_cyber = templates._cyber_template("img.jpg", "logo.png", "#000", "Text", layout_variant=variant)
        self.assertIn(f"variant-{variant}", html_cyber)

    def test_youtube_shorts_layout_preference(self):
        """Phase 2: Verify youtube_shorts has correct layout preferences."""
        self.assertIn("youtube_shorts", templates.CHANNEL_LAYOUT_PREFERENCE)
        prefs = templates.CHANNEL_LAYOUT_PREFERENCE["youtube_shorts"]
        self.assertIn("top-banner", prefs)  # Safe for Shorts UI overlay

    def test_pattern_layer_css(self):
        """Phase 2: Verify PATTERN_LAYER_CSS constant exists."""
        self.assertIn("pattern-overlay", templates.PATTERN_LAYER_CSS)
        self.assertIn("mix-blend-mode: multiply", templates.PATTERN_LAYER_CSS)
        self.assertIn("opacity: 0.1", templates.PATTERN_LAYER_CSS)

    def test_pattern_overlay_helper(self):
        """Phase 2: Verify pattern overlay HTML helper function."""
        # Test with no pattern (should return empty)
        self.assertEqual(templates._get_pattern_overlay_html(None), "")
        self.assertEqual(templates._get_pattern_overlay_html(""), "")
        
        # Test with pattern (should include overlay div)
        pattern_svg = '<svg><rect width="10" height="10"/></svg>'
        html = templates._get_pattern_overlay_html(pattern_svg)
        self.assertIn("pattern-overlay", html)
        self.assertIn("data:image/svg+xml", html)

if __name__ == '__main__':
    unittest.main()
