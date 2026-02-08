"""
Citation Detection Channels
===========================
Each channel detects citations using a specific signal:
- bracket: Detects [n], [n-m], [n,m,o] patterns in text
- superscript: Detects geometric superscript numbers (Phase 2)
"""

from .bracket import BracketChannel, BracketConfig, extract_bracket_candidates
from .superscript import SuperscriptChannel, SupConfig, extract_superscript_candidates

__all__ = [
    'BracketChannel', 'BracketConfig', 'extract_bracket_candidates',
    'SuperscriptChannel', 'SupConfig', 'extract_superscript_candidates',
]
