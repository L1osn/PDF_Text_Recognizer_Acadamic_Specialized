"""
Bibliography Extraction Module
==============================
Extract and parse bibliography/references section from PDF text.
"""

from .extractor import BibliographyExtractor, extract_bibliography

__all__ = ['BibliographyExtractor', 'extract_bibliography']
