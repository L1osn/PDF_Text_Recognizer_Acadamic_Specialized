"""
Bracket Citation Channel
========================
Detects bracketed citations like [1], [1-3], [1,3,5].
High confidence, stable main detection channel.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from ..types import (
    Occurrence, CitationCandidate, Bibliography, normalize_ref_text, parse_ref_ids
)
from ..page_model import PageData


@dataclass
class BracketConfig:
    """Configuration for bracket channel"""
    base_confidence: float = 0.9
    max_span: int = 20  # Max range like [1-20]
    require_bib_constraint: bool = True


class BracketChannel:
    """
    Detect bracketed citation references.
    
    Patterns supported:
    - [1] - single reference
    - [1-3] or [1–3] - range
    - [1,3,5] - list
    - [1-3,7,9-10] - mixed
    """
    
    # Matches bracket citations like: [12], [1,3,5], [1-3], [1–3,7,9-10]
    BRACKET_PATTERN = re.compile(r"\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]")
    
    def __init__(self, config: Optional[BracketConfig] = None):
        self.config = config or BracketConfig()
    
    def extract(
        self,
        pages: List[PageData],
        bib: Bibliography
    ) -> List[CitationCandidate]:
        """
        Extract bracket citations from all pages.
        
        Args:
            pages: List of PageData
            bib: Bibliography for constraint filtering
        
        Returns:
            List of CitationCandidate
        """
        candidates = []
        
        for page in pages:
            page_cands = self._process_page(page, bib)
            candidates.extend(page_cands)
        
        return candidates
    
    def _process_page(
        self,
        page: PageData,
        bib: Bibliography
    ) -> List[CitationCandidate]:
        """Process single page using PageData locate_text_matches"""
        candidates: List[CitationCandidate] = []

        for tm in page.locate_text_matches(self.BRACKET_PATTERN):
            raw = tm.match_text
            norm = normalize_ref_text(raw)
            ref_ids = parse_ref_ids(norm, max_span=self.config.max_span)
            if not ref_ids:
                continue

            # Apply bib constraint
            if bib.is_valid() and self.config.require_bib_constraint:
                ref_ids = [r for r in ref_ids if bib.has_id(r)]
                if not ref_ids:
                    continue

            anchor_left = page.get_left_context(tm.line_id, tm.bbox[0], max_chars=32)

            occ = Occurrence(
                page=page.page_num,
                bbox=tm.bbox,
                line_id=tm.line_id,
                source="bracket",
                anchor_left=anchor_left,
            )

            cand = CitationCandidate(
                ref_ids=ref_ids,
                occurrence=occ,
                evidence={
                    "pattern": "bracket",
                    "raw": raw,
                },
                confidence=self.config.base_confidence,
            )
            candidates.append(cand)

        return candidates


def extract_bracket_candidates(
    pages: List[PageData],
    bib: Bibliography,
    config: Optional[BracketConfig] = None
) -> List[CitationCandidate]:
    """
    Convenience function for bracket extraction.
    """
    channel = BracketChannel(config)
    return channel.extract(pages, bib)
