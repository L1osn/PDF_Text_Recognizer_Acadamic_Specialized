"""
Tests for CitationAnalyzer module
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from citation_analyzer import (
    CitationAnalyzer, 
    AnalysisConfig, 
    RefEntry, 
    parse_bibliography_ids
)


class TestCitationAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = CitationAnalyzer(AnalysisConfig.balanced())
    
    def test_normalize_text(self):
        # Unicode superscripts
        self.assertEqual(self.analyzer.normalize_text("¹"), "1")
        self.assertEqual(self.analyzer.normalize_text("²³"), "23")
        
        # Brackets/parens
        self.assertEqual(self.analyzer.normalize_text("[1]"), "1")
        self.assertEqual(self.analyzer.normalize_text("(5)"), "5")
        self.assertEqual(self.analyzer.normalize_text("[12]"), "12")
    
    def test_expand_range(self):
        # Single number
        self.assertEqual(self.analyzer.expand_range("1"), ["1"])
        self.assertEqual(self.analyzer.expand_range("[5]"), ["5"])
        
        # Range
        self.assertEqual(self.analyzer.expand_range("1-3"), ["1", "2", "3"])
        self.assertEqual(self.analyzer.expand_range("[1-3]"), ["1", "2", "3"])
        
        # List
        self.assertEqual(self.analyzer.expand_range("1,3,5"), ["1", "3", "5"])
    
    def test_is_valid_citation_id(self):
        # Valid
        self.assertTrue(self.analyzer.is_valid_citation_id("1")[0])
        self.assertTrue(self.analyzer.is_valid_citation_id("50")[0])
        self.assertTrue(self.analyzer.is_valid_citation_id("100")[0])
        
        # Invalid: zero
        self.assertFalse(self.analyzer.is_valid_citation_id("0")[0])
        
        # Invalid: too large
        self.assertFalse(self.analyzer.is_valid_citation_id("9999")[0])
        
        # Invalid: non-numeric
        self.assertFalse(self.analyzer.is_valid_citation_id("abc")[0])
    
    def test_is_valid_raw_text(self):
        # Valid
        self.assertTrue(self.analyzer.is_valid_raw_text("[1]")[0])
        self.assertTrue(self.analyzer.is_valid_raw_text("1-3")[0])
        self.assertTrue(self.analyzer.is_valid_raw_text("¹²")[0])  # Unicode superscripts
        
        # Invalid: excluded symbols
        self.assertFalse(self.analyzer.is_valid_raw_text("*")[0])
        self.assertFalse(self.analyzer.is_valid_raw_text("†")[0])
        
        # Invalid: contains dot (decimal/version)
        self.assertFalse(self.analyzer.is_valid_raw_text("0.75")[0])
        self.assertFalse(self.analyzer.is_valid_raw_text("100.05")[0])
        self.assertFalse(self.analyzer.is_valid_raw_text("1.0")[0])
    
    def test_header_footer_filter(self):
        # In header (top of page)
        self.assertTrue(self.analyzer.is_in_header_footer((100, 30, 110, 40), 792.0))
        
        # In footer (bottom of page)
        self.assertTrue(self.analyzer.is_in_header_footer((100, 760, 110, 770), 792.0))
        
        # In body (middle of page)
        self.assertFalse(self.analyzer.is_in_header_footer((100, 400, 110, 410), 792.0))
    
    def test_deduplication(self):
        self.analyzer.reset()
        
        # Add same ref multiple times on same page, same location
        bbox = (100, 200, 110, 210)
        self.analyzer.add_superscript("1", 1, bbox, "text context", 792.0, 5)
        self.analyzer.add_superscript("1", 1, bbox, "text context", 792.0, 5)  # Duplicate
        
        entries = self.analyzer.get_sorted_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].count, 1)  # Should dedupe to 1
    
    def test_multiple_occurrences(self):
        self.analyzer.reset()
        
        # Add same ref on different pages
        self.analyzer.add_superscript("1", 1, (100, 200, 110, 210), "context A", 792.0, 5)
        self.analyzer.add_superscript("1", 2, (50, 100, 60, 110), "context B", 792.0, 3)
        
        entries = self.analyzer.get_sorted_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].count, 2)  # 2 occurrences
    
    def test_bibliography_constraint(self):
        self.analyzer.reset()
        self.analyzer.set_bibliography_ids({"1", "2", "3"})
        
        # Valid: in bibliography
        self.analyzer.add_superscript("1", 1, (100, 200, 110, 210), "context", 792.0, 5)
        
        # Invalid: not in bibliography
        self.analyzer.add_superscript("99", 1, (200, 200, 210, 210), "context", 792.0, 5)
        
        entries = self.analyzer.get_sorted_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].ref_id, "1")
    
    def test_header_filtered(self):
        """Verify that tokens in header region are filtered out"""
        self.analyzer.reset()
        
        # In header (y < 50)
        self.analyzer.add_superscript("1", 1, (100, 20, 110, 30), "header context", 792.0, 0)
        
        # In body
        self.analyzer.add_superscript("2", 1, (100, 200, 110, 210), "body context", 792.0, 5)
        
        entries = self.analyzer.get_sorted_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].ref_id, "2")
    
    def test_parse_bibliography_ids(self):
        text = """
[1] Smith, J. (2020). A paper.
[2] Jones, K. (2021). Another paper.
[3] Brown, L. (2022). Third paper.
"""
        ids = parse_bibliography_ids(text)
        self.assertEqual(ids, {"1", "2", "3"})


class TestAnalysisConfig(unittest.TestCase):
    
    def test_presets(self):
        strict = AnalysisConfig.strict()
        balanced = AnalysisConfig.balanced()
        recall = AnalysisConfig.recall()
        
        # Strict should have smaller thresholds
        self.assertLess(strict.sup_size_ratio, balanced.sup_size_ratio)
        self.assertLess(strict.max_ref_id, balanced.max_ref_id)
        
        # Recall should have larger thresholds
        self.assertGreater(recall.sup_size_ratio, balanced.sup_size_ratio)


if __name__ == "__main__":
    unittest.main()
