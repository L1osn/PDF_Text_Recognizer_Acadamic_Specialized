"""
Citation Recognition Engine
===========================
Dual-channel (bracket + superscript) citation detection with bibliography constraint.

Architecture:
- page_model: Page data structures and line grouping
- bib: Bibliography section extraction and parsing
- channels: Detection channels (bracket, superscript)
- fusion: Multi-channel fusion with bib constraint

Usage:
    from engine import CitationPipeline
    pipeline = CitationPipeline()
    entries, debug = pipeline.run_from_pages(page_models, pages_text)
"""

from .types import (
    BBox,
    Occurrence,
    CitationCandidate,
    RefEntry,
    Bibliography,
)
from .pipeline import CitationPipeline, PipelineConfig, DebugBundle

__all__ = [
    'BBox',
    'Occurrence', 
    'CitationCandidate',
    'RefEntry',
    'Bibliography',
    'CitationPipeline',
    'PipelineConfig',
    'DebugBundle',
]

__version__ = '2.0.0'
