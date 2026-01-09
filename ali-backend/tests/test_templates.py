
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

if __name__ == '__main__':
    unittest.main()
