"""
Fusion Module
=============
Merges candidates from multiple channels with deduplication.
"""

from .fuser import CitationFuser, FusionConfig, fuse_candidates

__all__ = ['CitationFuser', 'FusionConfig', 'fuse_candidates']
