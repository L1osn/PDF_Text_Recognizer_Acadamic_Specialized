
import unittest
import sys
import os

# Add parent directory to path to allow importing modules from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Pdf_to_text import LayoutAnalyzer, AcademicPDFRecognizer
from unittest.mock import MagicMock, patch

class TestLayoutAnalyzer(unittest.TestCase):
    def test_superscript_detection(self):
        # Create chars: Body text "Bod" and a small raised "1"
        chars = [
            {'text': 'B', 'top': 100, 'bottom': 110, 'x0': 10, 'x1': 20, 'size': 10, 'page': 1},
            {'text': 'o', 'top': 100, 'bottom': 110, 'x0': 20, 'x1': 30, 'size': 10, 'page': 1},
            {'text': 'd', 'top': 100, 'bottom': 110, 'x0': 30, 'x1': 40, 'size': 10, 'page': 1},
            # Superscript '1': smaller (e.g. 7) and raised (bottom is higher, e.g. 102)
            # Baseline is approx 110. Raised threshold 0.2 * 10 = 2. 
            # So bottom < 108 is considered raised.
            {'text': '1', 'top': 97, 'bottom': 102, 'x0': 40, 'x1': 47, 'size': 7, 'page': 1},
        ]
        
        # process_page now returns (processed_chars, sup_tokens)
        processed_chars, sup_tokens = LayoutAnalyzer.process_page(chars, page_num=1)
        
        # Verify the 4th char is detected as superscript
        sup_char = processed_chars[3]
        # TEXT IS NO LONGER MODIFIED - original '1' is preserved
        self.assertEqual(sup_char['text'], '1')
        self.assertTrue(sup_char['is_superscript'])
        # Check size is NOT changed
        self.assertEqual(sup_char['size'], 7)
        
        # Verify sup_tokens contains the token
        self.assertEqual(len(sup_tokens), 1)
        self.assertEqual(sup_tokens[0]['text'], '1')

    def test_exclude_noise(self):
        # '*' should not be tagged as superscript even if small and raised
        chars = [
             {'text': 'A', 'top': 100, 'bottom': 110, 'x0': 10, 'x1': 20, 'size': 10, 'page': 1},
             {'text': '*', 'top': 97, 'bottom': 102, 'x0': 20, 'x1': 25, 'size': 7, 'page': 1},
        ]
        processed_chars, sup_tokens = LayoutAnalyzer.process_page(chars, page_num=1)
        self.assertFalse(processed_chars[1].get('is_superscript', False))
        self.assertEqual(processed_chars[1]['text'], '*')
        # No tokens should be generated for '*'
        self.assertEqual(len(sup_tokens), 0)

    def test_unicode_preserved(self):
        # Unicode ¹ should be preserved (not modified) - normalization is handled by the new engine
        chars = [
            {'text': 'A', 'top': 100, 'bottom': 110, 'x0': 10, 'x1': 20, 'size': 10, 'page': 1},
            {'text': '¹', 'top': 97, 'bottom': 102, 'x0': 20, 'x1': 25, 'size': 7, 'page': 1},
        ]
        processed_chars, sup_tokens = LayoutAnalyzer.process_page(chars, page_num=1)
        # Text is now preserved as-is
        self.assertEqual(processed_chars[1]['text'], '¹')
        self.assertTrue(processed_chars[1]['is_superscript'])
        # Token contains original unicode
        self.assertEqual(sup_tokens[0]['text'], '¹')

    def test_extract_text_reassembly(self):
        # Test that extract_text reassembles text correctly with spaces/newlines
        rec = AcademicPDFRecognizer("dummy.pdf")
        
        # Mock pdfplumber open
        with patch("pdfplumber.open") as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.height = 792.0
            mock_page.chars = [
                 {'text': 'H', 'top': 100, 'bottom': 110, 'x0': 10, 'x1': 15, 'size': 10, 'page': 1},
                 {'text': 'i', 'top': 100, 'bottom': 110, 'x0': 15, 'x1': 20, 'size': 10, 'page': 1},
                 # Space gap (x0=25, prev_x1=20, gap=5 > 2.0)
                 {'text': 'T', 'top': 100, 'bottom': 110, 'x0': 25, 'x1': 30, 'size': 10, 'page': 1},
                 # New line gap (top=120, prev=100 > 5.0)
                 {'text': 'N', 'top': 120, 'bottom': 130, 'x0': 10, 'x1': 15, 'size': 10, 'page': 1}
            ]
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf
            
            text = rec.extract_text()
            # Expect "Hi T" (space due to gap) + "\n" (due to top gap) + "N"
            # Strip trailing newline from page-end control span
            self.assertEqual(text.rstrip('\n'), "Hi T\nN")

if __name__ == "__main__":
    unittest.main()
