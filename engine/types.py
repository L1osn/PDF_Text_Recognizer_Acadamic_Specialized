"""
Unified Data Types for Citation Engine
======================================
All modules MUST use these types. No custom structures allowed.

Type Hierarchy:
- BBox: Bounding box tuple
- Occurrence: Single citation occurrence at a location
- CitationCandidate: Detection result from a channel (before fusion)
- RefEntry: Final merged reference (after fusion)
- Bibliography: Parsed bibliography section
"""

from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Set, Any, Optional


# ============================================================
# Primitive Types
# ============================================================

# Bounding Box: (x0, top, x1, bottom) in PDF coordinates
BBox = Tuple[float, float, float, float]


# ============================================================
# Core Data Structures
# ============================================================

@dataclass
class Occurrence:
    """
    A single occurrence of a citation in the document.
    
    Attributes:
        page: 1-indexed page number
        bbox: Bounding box in PDF coordinates (x0, top, x1, bottom)
        line_id: Line index within the page (for deduplication)
        source: Detection channel that found this ("bracket", "superscript")
        anchor_left: Context text before the citation (up to 30 chars)
    """
    page: int
    bbox: BBox
    line_id: int
    source: str  # "bracket" | "superscript"
    anchor_left: str = ""
    
    def dedup_key(self) -> Tuple[int, int, float, float]:
        """Generate deduplication key: (page, line_id, center_x, center_y)"""
        cx = round((self.bbox[0] + self.bbox[2]) / 2, 1)
        cy = round((self.bbox[1] + self.bbox[3]) / 2, 1)
        return (self.page, self.line_id, cx, cy)
    
    def __hash__(self):
        return hash(self.dedup_key())
    
    def __eq__(self, other):
        if not isinstance(other, Occurrence):
            return False
        return self.dedup_key() == other.dedup_key()


@dataclass
class CitationCandidate:
    """
    A citation detection result from a single channel (before fusion).
    
    Attributes:
        ref_ids: List of reference IDs detected (e.g., [1, 2, 3] for "1-3")
        occurrence: Location and context of detection
        evidence: Channel-specific evidence (fonts, patterns, etc.)
        confidence: Detection confidence score (0.0 to 1.0)
    """
    ref_ids: List[int]
    occurrence: Occurrence
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    
    @property
    def primary_id(self) -> int:
        """Return the first (primary) ref ID"""
        return self.ref_ids[0] if self.ref_ids else 0
    
    def is_range(self) -> bool:
        """Check if this is a range citation (e.g., 1-3)"""
        return len(self.ref_ids) > 1


@dataclass
class RefEntry:
    """
    A finalized reference entry after fusion.
    This is the output type exposed to the UI.
    
    Attributes:
        ref_id: Unique reference ID (integer, e.g., 1, 2, 3)
        occurrences: All deduplicated occurrences of this ref
        bib_detail: Bibliography text if found (or None)
        sources: Set of channels that detected this ref
        confidence: Final confidence score after fusion
        unlinked_to_bib: True if citation not found in bibliography (soft constraint)
    
    UI Display Contract:
        - ref_id: Display as "[n]"
        - count: len(occurrences)
        - page: First occurrence page
        - bib_detail: Bibliography text or "No detail found"
        - source: Comma-joined sources ("bracket", "superscript", "bracket,superscript")
        - unlinked_to_bib: Can be used to hide/dim unlinked citations in UI
    """
    ref_id: int
    occurrences: List[Occurrence] = field(default_factory=list)
    bib_detail: Optional[str] = None
    sources: Set[str] = field(default_factory=set)
    confidence: float = 0.5
    unlinked_to_bib: bool = False
    
    @property
    def count(self) -> int:
        """Number of occurrences"""
        return len(self.occurrences)
    
    @property
    def first_page(self) -> int:
        """Page of first occurrence (for sorting/display)"""
        if self.occurrences:
            return self.occurrences[0].page
        return 0
    
    @property
    def first_bbox(self) -> Optional[BBox]:
        """BBox of first occurrence"""
        if self.occurrences:
            return self.occurrences[0].bbox
        return None
    
    @property
    def source_str(self) -> str:
        """Comma-joined source channels"""
        return ",".join(sorted(self.sources))
    
    def add_occurrence(self, occ: Occurrence) -> bool:
        """
        Add occurrence with deduplication.
        Returns True if added, False if duplicate.
        """
        if occ in self.occurrences:
            return False
        self.occurrences.append(occ)
        self.sources.add(occ.source)
        return True
    
    def merge_from(self, other: 'RefEntry'):
        """Merge another RefEntry into this one"""
        for occ in other.occurrences:
            self.add_occurrence(occ)
        self.sources.update(other.sources)
        # Take higher confidence
        self.confidence = max(self.confidence, other.confidence)
        # Prefer non-None bib_detail
        if self.bib_detail is None and other.bib_detail is not None:
            self.bib_detail = other.bib_detail


@dataclass
class Bibliography:
    """
    Parsed bibliography section.
    
    Attributes:
        bib_ids: Set of valid reference IDs found in bibliography
        bib_map: Mapping from ref_id to bibliography text
        start_page: Page where bibliography section starts
        raw_text: Raw text of bibliography section (for debugging)
    """
    bib_ids: Set[int] = field(default_factory=set)
    bib_map: Dict[int, str] = field(default_factory=dict)
    start_page: int = -1
    raw_text: str = ""
    
    def has_id(self, ref_id: int) -> bool:
        """Check if ref_id exists in bibliography"""
        return ref_id in self.bib_ids
    
    def get_detail(self, ref_id: int) -> Optional[str]:
        """Get bibliography text for ref_id"""
        return self.bib_map.get(ref_id)
    
    def is_valid(self) -> bool:
        """Check if bibliography was successfully parsed"""
        return len(self.bib_ids) > 0
    
    @property
    def count(self) -> int:
        """Number of bibliography entries"""
        return len(self.bib_ids)


# ============================================================
# Helper Functions
# ============================================================

def normalize_ref_id(raw: str) -> Optional[int]:
    """
    Normalize raw text to integer ref_id.
    
    Handles:
    - "[1]" -> 1
    - "1." -> 1
    - "¹" -> 1 (unicode superscript)
    - "1" -> 1
    
    Returns None if invalid.
    """
    # Unicode superscript mapping
    SUPERSCRIPT_MAP = str.maketrans("¹²³⁴⁵⁶⁷⁸⁹⁰", "1234567890")
    
    # Apply unicode normalization
    text = raw.translate(SUPERSCRIPT_MAP)
    
    # Strip brackets, parens, dots
    import re
    text = re.sub(r'[\[\]().,:;\s]', '', text)
    
    # Must be numeric now
    if not text.isdigit():
        return None
    
    # Reject leading zeros (except "0" itself, which we also reject)
    if len(text) > 1 and text.startswith('0'):
        return None
    
    num = int(text)
    
    # Must be positive
    if num <= 0:
        return None
    
    # Sanity check: max 999
    if num > 999:
        return None
    
    return num


def expand_range(text: str) -> List[int]:
    """
    Expand citation ranges and lists to list of integers.
    
    Examples:
    - "1-3" -> [1, 2, 3]
    - "1,3,5" -> [1, 3, 5]
    - "[1]" -> [1]
    - "1–3" (en-dash) -> [1, 2, 3]
    
    Returns empty list if invalid.
    """
    import re
    
    # Unicode superscript mapping
    SUPERSCRIPT_MAP = str.maketrans("¹²³⁴⁵⁶⁷⁸⁹⁰", "1234567890")
    text = text.translate(SUPERSCRIPT_MAP)
    
    # Strip brackets
    text = re.sub(r'[\[\]()]', '', text).strip()
    
    # Handle range: 1-3 or 1–3 (en-dash)
    range_match = re.match(r'^(\d+)\s*[-–]\s*(\d+)$', text)
    if range_match:
        start, end = int(range_match.group(1)), int(range_match.group(2))
        if start <= end <= start + 20:  # Max 20 refs in range
            return list(range(start, end + 1))
        return []
    
    # Handle list: 1,3,5
    if ',' in text:
        results = []
        parts = [p.strip() for p in text.split(',')]
        for p in parts:
            if p.isdigit():
                num = int(p)
                if 0 < num <= 999:
                    results.append(num)
        return results
    
    # Single number
    if text.isdigit():
        num = int(text)
        if 0 < num <= 999:
            return [num]
    
    return []


# ============================================================
# Unified Normalization / Parsing (new pipeline)
# ============================================================

_SUPERSCRIPT_TRANSLATION = str.maketrans("¹²³⁴⁵⁶⁷⁸⁹⁰", "1234567890")
_DASH_TRANSLATION = str.maketrans({
    "–": "-",  # en-dash
    "—": "-",  # em-dash
    "−": "-",  # minus sign
    "‑": "-",  # non-breaking hyphen
})


def normalize_ref_text(raw: str) -> str:
    """
    Normalize citation raw text into a compact parseable form.

    Behavior:
    - Unicode superscripts -> normal digits
    - En-dash -> hyphen
    - Remove whitespace
    - Strip wrapping brackets/parentheses (outermost only)
    """
    if raw is None:
        return ""
    s = str(raw)
    s = s.translate(_SUPERSCRIPT_TRANSLATION)
    s = s.translate(_DASH_TRANSLATION)
    s = "".join(ch for ch in s if not ch.isspace())
    # strip one layer of wrappers
    if len(s) >= 2 and ((s[0] == "[" and s[-1] == "]") or (s[0] == "(" and s[-1] == ")")):
        s = s[1:-1]
    return s


def parse_ref_ids(norm: str, max_span: int = 20) -> List[int]:
    """
    Parse a normalized citation string into a list of ref ids.

    Supports:
    - "12" -> [12]
    - "1,3,5" -> [1,3,5]
    - "1-3" -> [1,2,3]
    - "1-3,7,9-10" -> [1,2,3,7,9,10]

    Rules:
    - range span limited by max_span
    - reject 0
    - reject multi-digit leading zeros (e.g. "01")
    - de-duplicate while preserving order
    """
    import re

    s = normalize_ref_text(norm)
    if not s:
        return []

    out: List[int] = []
    seen: Set[int] = set()

    # Split by commas into parts (each part may be single or range)
    parts = [p for p in s.split(",") if p]
    for part in parts:
        # range?
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            a, b = m.group(1), m.group(2)
            if (len(a) > 1 and a.startswith("0")) or (len(b) > 1 and b.startswith("0")):
                continue
            start, end = int(a), int(b)
            if start <= 0 or end <= 0:
                continue
            if end < start:
                continue
            if end - start > max_span:
                continue
            for n in range(start, end + 1):
                if n not in seen:
                    seen.add(n)
                    out.append(n)
            continue

        # single number
        if not part.isdigit():
            continue
        if len(part) > 1 and part.startswith("0"):
            continue
        n = int(part)
        if n <= 0:
            continue
        if n not in seen:
            seen.add(n)
            out.append(n)

    return out
