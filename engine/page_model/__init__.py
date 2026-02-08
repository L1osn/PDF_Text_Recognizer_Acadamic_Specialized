"""
Page Model Module
=================
Data structures and utilities for page-level text analysis.
"""

from .model import PageData, LineData, CharData, build_page_data

__all__ = ['PageData', 'LineData', 'CharData', 'build_page_data']
