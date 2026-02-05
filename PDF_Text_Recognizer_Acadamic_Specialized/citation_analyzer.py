"""
Citation Analyzer Module
Separates superscript detection (geometric) from citation judgment (semantic).
Provides normalization, deduplication, and validation for academic citations.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set, Optional, Any
from collections import defaultdict


@dataclass
class CitationOccurrence:
    """A single occurrence of a citation in the document"""
    page: int
    bbox: Tuple[float, float, float, float]
    anchor_text: str  # Context text before the citation
    raw_text: str     # Original text as found
    line_num: int = 0


@dataclass 
class RefEntry:
    """A unique citation reference with all its occurrences"""
    ref_id: str                           # Normalized ID (e.g., "1", "2")
    occurrences: List[CitationOccurrence] = field(default_factory=list)
    bib_detail: str = ""                  # Bibliography text if found
    bib_page: int = -1                    # Page where bib entry is located
    confidence: float = 1.0               # Confidence score
    
    @property
    def count(self) -> int:
        return len(self.occurrences)
    
    def add_occurrence(self, page: int, bbox: Tuple, anchor: str, raw: str, line_num: int = 0):
        """Add occurrence with deduplication using (page, line_num, center_x, center_y)"""
        # Better dedup key using line and bbox center
        center_x = round((bbox[0] + bbox[2]) / 2, 1)
        center_y = round((bbox[1] + bbox[3]) / 2, 1)
        dedup_key = (page, line_num, center_x, center_y)
        
        for occ in self.occurrences:
            existing_cx = round((occ.bbox[0] + occ.bbox[2]) / 2, 1)
            existing_cy = round((occ.bbox[1] + occ.bbox[3]) / 2, 1)
            # Use occ.line_num instead of the method argument line_num
            existing_key = (occ.page, occ.line_num, existing_cx, existing_cy)
            if dedup_key == existing_key:
                return  # Skip duplicate
        self.occurrences.append(CitationOccurrence(page, bbox, anchor, raw, line_num))


@dataclass
class AnalysisConfig:
    """Configuration for citation analysis thresholds"""
    # Superscript detection
    sup_size_ratio: float = 0.85
    sup_rise_ratio: float = 0.20
    
    # Citation validation
    max_ref_digits: int = 3              # Max digits (e.g., 999)
    min_ref_id: int = 1                  # Minimum valid ref ID
    max_ref_id: int = 999                # Maximum valid ref ID
    
    # Context filtering - HARD filters (not scoring)
    page_margin_top: float = 50.0        # Exclude headers
    page_margin_bottom_ratio: float = 0.95  # Exclude bottom 5% of page (footers)
    
    # Presets
    @classmethod
    def strict(cls) -> 'AnalysisConfig':
        return cls(sup_size_ratio=0.80, sup_rise_ratio=0.25, max_ref_id=200)
    
    @classmethod
    def balanced(cls) -> 'AnalysisConfig':
        return cls(sup_size_ratio=0.85, sup_rise_ratio=0.20, max_ref_id=500)
    
    @classmethod
    def recall(cls) -> 'AnalysisConfig':
        return cls(sup_size_ratio=0.90, sup_rise_ratio=0.15, max_ref_id=999)


class CitationAnalyzer:
    """
    Two-stage citation analysis:
    Stage 1: Geometric superscript detection (from LayoutAnalyzer)
    Stage 2: Semantic citation validation and deduplication
    """
    
    # Characters that are NOT citation numbers
    EXCLUDED_SYMBOLS = {'*', '†', '‡', '§', '¶', '#', '°', '©', '®', '™', '…'}
    
    # Unicode superscript normalization map
    SUPERSCRIPT_MAP = str.maketrans("¹²³⁴⁵⁶⁷⁸⁹⁰ⁱⁿ", "1234567890in")
    
    # Left context patterns that suggest NON-citation (units, exponents, etc.)
    NON_CITATION_LEFT_PATTERNS = [
        r'\d$',           # Ends with digit (exponent: 10^2)
        r'[=×÷+\-*/]$',   # Math operators
        r'(cm|mm|m|kg|g|s|Hz|°|%|mol|L|mL)$',  # Units
        r'\($',           # Open paren (might be formula)
        r'[Ee]$',         # Scientific notation (1.5E)
    ]
    
    # Left context patterns that suggest citation
    CITATION_LEFT_PATTERNS = [
        r'[.,:;!?]$',     # Punctuation (sentence end)
        r'[a-zA-Z]$',     # Word ending
        r'\)$',           # Close paren (after phrase)
        r'["\'"]$',       # Quote end
    ]
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        self.config = config or AnalysisConfig.balanced()
        self.ref_entries: Dict[str, RefEntry] = {}  # ref_id -> RefEntry
        self.bib_ids: Set[str] = set()              # Valid IDs from bibliography
        self.raw_superscripts: List[Dict] = []      # All detected superscripts
        
    def reset(self):
        """Clear all analysis state"""
        self.ref_entries.clear()
        self.bib_ids.clear()
        self.raw_superscripts.clear()
    
    # ==================== NORMALIZATION ====================
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize superscript text to standard form.
        ¹ -> 1, [1] -> 1, (1) -> 1
        """
        # Unicode superscripts
        text = text.translate(self.SUPERSCRIPT_MAP)
        # Remove brackets/parens
        text = re.sub(r'[\[\]()]', '', text)
        # Strip whitespace
        text = text.strip()
        return text
    
    def expand_range(self, text: str) -> List[str]:
        """
        Expand citation ranges and lists.
        "1-3" -> ["1", "2", "3"]
        "1,3,5" -> ["1", "3", "5"]
        "1" -> ["1"]
        """
        normalized = self.normalize_text(text)
        results = []
        
        # Handle range: 1-3 or 1–3 (en-dash)
        range_match = re.match(r'^(\d+)\s*[-–]\s*(\d+)$', normalized)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start <= end <= start + 20:  # Sanity check: max 20 refs in range
                return [str(i) for i in range(start, end + 1)]
            return []  # Invalid range
        
        # Handle list: 1,3,5
        if ',' in normalized:
            parts = [p.strip() for p in normalized.split(',')]
            for p in parts:
                if p.isdigit():
                    results.append(p)
            return results
        
        # Single number
        if normalized.isdigit():
            return [normalized]
        
        return []
    
    # ==================== VALIDATION ====================
    
    def is_valid_citation_id(self, ref_id: str) -> Tuple[bool, str]:
        """
        Check if a normalized ref_id is valid.
        Returns (is_valid, reason)
        """
        # Must be numeric
        if not ref_id.isdigit():
            return False, "not_numeric"
        
        num = int(ref_id)
        
        # Rule: No zero
        if num == 0:
            return False, "zero_not_allowed"
        
        # Rule: Within range
        if num < self.config.min_ref_id:
            return False, "below_min"
        if num > self.config.max_ref_id:
            return False, "above_max"
        
        # Rule: Max digits
        if len(ref_id) > self.config.max_ref_digits:
            return False, "too_many_digits"
        
        # If we have bibliography, check against it
        if self.bib_ids and ref_id not in self.bib_ids:
            return False, "not_in_bibliography"
        
        return True, "valid"
    
    def is_valid_raw_text(self, raw_text: str) -> Tuple[bool, str]:
        """
        Check if raw superscript text looks like a citation.
        Pre-normalizes before validation to handle unicode/brackets consistently.
        """
        text = raw_text.strip()
        
        # Empty
        if not text:
            return False, "empty"
        
        # Excluded symbols (check before normalization)
        if text in self.EXCLUDED_SYMBOLS:
            return False, "excluded_symbol"
        if any(s in text for s in self.EXCLUDED_SYMBOLS):
            return False, "contains_excluded"
        
        # Pre-normalize: apply unicode map and strip brackets
        normalized = text.translate(self.SUPERSCRIPT_MAP)
        normalized = re.sub(r'[\[\]()\s]', '', normalized)
        
        # HARD FILTER: Contains dot -> likely decimal/version number
        if '.' in normalized:
            return False, "contains_dot"
        
        # Check if anything remains after normalization
        if not normalized:
            return False, "empty_after_normalize"
        
        # Only allowed: digits, comma, dash (for ranges/lists)
        cleaned = normalized.replace(',', '').replace('-', '').replace('–', '')
        if not cleaned.isdigit():
            return False, "invalid_characters"
        
        return True, "valid"
    
    def is_in_header_footer(self, bbox: Tuple, page_height: float) -> bool:
        """HARD filter: check if token is in header/footer region"""
        top = bbox[1]
        bottom = bbox[3]
        
        # Header region (top margin)
        if top < self.config.page_margin_top:
            return True
        
        # Footer region (bottom X% of page)
        footer_threshold = page_height * self.config.page_margin_bottom_ratio
        if bottom > footer_threshold:
            return True
        
        return False
    
    def score_context(self, anchor_text: str) -> float:
        """
        Score the likelihood based on left context.
        Returns score from 0.0 to 1.0.
        """
        score = 0.5  # Neutral start
        
        if anchor_text:
            # Check for non-citation patterns (exponents, units, etc.)
            for pattern in self.NON_CITATION_LEFT_PATTERNS:
                if re.search(pattern, anchor_text, re.IGNORECASE):
                    score -= 0.3
                    break
            
            # Check for citation patterns (punctuation, words)
            for pattern in self.CITATION_LEFT_PATTERNS:
                if re.search(pattern, anchor_text):
                    score += 0.2
                    break
        
        return max(0.0, min(1.0, score))
    
    # ==================== MAIN ANALYSIS ====================
    
    def set_bibliography_ids(self, bib_ids: Set[str]):
        """Set valid bibliography IDs for constraint"""
        self.bib_ids = bib_ids
    
    def add_superscript(self, raw_text: str, page: int, bbox: Tuple, 
                        anchor_text: str = "", page_height: float = 792.0,
                        line_num: int = 0):
        """
        Add a superscript token for analysis.
        Uses HARD filters for header/footer and invalid text.
        """
        # Store raw for debugging
        self.raw_superscripts.append({
            'raw': raw_text, 'page': page, 'bbox': bbox, 'anchor': anchor_text
        })
        
        # HARD FILTER 1: Header/Footer region
        if self.is_in_header_footer(bbox, page_height):
            return  # Skip tokens in header/footer
        
        # HARD FILTER 2: Raw text validation (decimals, symbols, etc.)
        valid_raw, reason = self.is_valid_raw_text(raw_text)
        if not valid_raw:
            return  # Skip invalid raw text
        
        # HARD FILTER 3: Must expand to at least one valid ID
        ref_ids = self.expand_range(raw_text)
        if not ref_ids:
            return  # Cannot parse any valid ref IDs
        
        # Process each ref ID
        for ref_id in ref_ids:
            valid_id, id_reason = self.is_valid_citation_id(ref_id)
            if not valid_id:
                continue
            
            # Context scoring (soft filter - but with low threshold)
            score = self.score_context(anchor_text)
            if score < 0.2:  # Very low threshold - context is informational
                continue
            
            # Add to ref entries (with deduplication)
            if ref_id not in self.ref_entries:
                self.ref_entries[ref_id] = RefEntry(ref_id=ref_id, confidence=score)
            
            self.ref_entries[ref_id].add_occurrence(page, bbox, anchor_text, raw_text, line_num)
    
    def merge_adjacent_superscripts(self, superscripts: List[Dict]) -> List[Dict]:
        """
        Merge adjacent superscript tokens on the same line into complete refs.
        e.g., ['[', '1', ']'] -> ['[1]']
        """
        if not superscripts:
            return []
        
        merged = []
        buffer = []
        last_page = -1
        last_x1 = -1
        last_line = -1
        
        # Sort by page, line, x0
        sorted_sups = sorted(superscripts, key=lambda s: (
            s.get('page', 0), 
            s.get('_line_num', s.get('top', 0)), 
            s.get('bbox', (0,0,0,0))[0]
        ))
        
        for sup in sorted_sups:
            page = sup.get('page', 0)
            line = sup.get('_line_num', sup.get('top', 0))
            bbox = sup.get('bbox', (0, 0, 0, 0))
            x0, x1 = bbox[0], bbox[2]
            
            # Check if should merge with buffer
            same_context = (
                page == last_page and
                line == last_line and
                last_x1 > 0 and
                (x0 - last_x1) < 3.0  # Adjacent horizontally
            )
            
            if same_context and buffer:
                # Extend buffer
                buffer.append(sup)
            else:
                # Flush buffer
                if buffer:
                    merged.append(self._merge_buffer(buffer))
                buffer = [sup]
            
            last_page = page
            last_line = line
            last_x1 = x1
        
        # Flush final buffer
        if buffer:
            merged.append(self._merge_buffer(buffer))
        
        return merged
    
    def _merge_buffer(self, buffer: List[Dict]) -> Dict:
        """Merge a buffer of adjacent superscripts into one"""
        if len(buffer) == 1:
            return buffer[0]
        
        # Combine text
        combined_text = ''.join(s.get('text', '') for s in buffer)
        
        # Combine bbox
        x0 = min(s.get('bbox', (0,0,0,0))[0] for s in buffer)
        top = min(s.get('bbox', (0,0,0,0))[1] for s in buffer)
        x1 = max(s.get('bbox', (0,0,0,0))[2] for s in buffer)
        bottom = max(s.get('bbox', (0,0,0,0))[3] for s in buffer)
        
        return {
            'text': combined_text,
            'page': buffer[0].get('page', 0),
            'bbox': (x0, top, x1, bottom),
            'anchor': buffer[0].get('anchor', ''),
            '_line_num': buffer[0].get('_line_num', 0),
            'is_merged': True
        }
    
    def get_sorted_entries(self) -> List[RefEntry]:
        """Get ref entries sorted by numeric ID"""
        entries = list(self.ref_entries.values())
        entries.sort(key=lambda e: int(e.ref_id) if e.ref_id.isdigit() else 999)
        return entries
    
    def get_stats(self) -> Dict:
        """Get analysis statistics"""
        entries = self.get_sorted_entries()
        total_occurrences = sum(e.count for e in entries)
        return {
            'unique_refs': len(entries),
            'total_occurrences': total_occurrences,
            'raw_superscripts': len(self.raw_superscripts),
            'bib_constrained': len(self.bib_ids) > 0,
            'bib_count': len(self.bib_ids)
        }


def parse_bibliography_ids(text: str) -> Set[str]:
    """
    Extract bibliography entry IDs from References section text.
    Returns set of valid IDs like {"1", "2", "3", ...}
    """
    ids = set()
    
    # Pattern 1: [1] Author...
    for match in re.finditer(r'^\s*\[(\d+)\]', text, re.MULTILINE):
        ids.add(match.group(1))
    
    # Pattern 2: 1. Author...
    for match in re.finditer(r'^\s*(\d+)\.\s+[A-Z]', text, re.MULTILINE):
        num = match.group(1)
        if 1 <= int(num) <= 999:
            ids.add(num)
    
    return ids
