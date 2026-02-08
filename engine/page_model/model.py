"""
Page Data Model
===============
Structures for representing page content with line grouping.
Used by all channels for consistent position analysis.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional, Iterable
from collections import Counter
import re
import statistics


@dataclass
class CharData:
    """
    Single character with all relevant properties.
    Normalized from pdfplumber char dict.
    """
    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    size: float
    fontname: str = "Unknown"
    
    @property
    def mid_y(self) -> float:
        """Vertical center of character"""
        return (self.top + self.bottom) / 2
    
    @property
    def mid_x(self) -> float:
        """Horizontal center of character"""
        return (self.x0 + self.x1) / 2
    
    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        """Bounding box as tuple"""
        return (self.x0, self.top, self.x1, self.bottom)
    
    @classmethod
    def from_pdfplumber(cls, char_dict: Dict[str, Any]) -> 'CharData':
        """Create from pdfplumber char dictionary"""
        return cls(
            text=char_dict.get('text', ''),
            x0=char_dict.get('x0', 0),
            top=char_dict.get('top', 0),
            x1=char_dict.get('x1', 0),
            bottom=char_dict.get('bottom', 0),
            size=char_dict.get('size', 0),
            fontname=char_dict.get('fontname', 'Unknown'),
        )


@dataclass
class LineData:
    """
    A line of characters grouped by vertical position.
    """
    line_id: int
    chars: List[CharData] = field(default_factory=list)
    zone: str = "body"  # title/body/footer
    
    @property
    def text(self) -> str:
        """Concatenated text of all chars"""
        return ''.join(c.text for c in self.chars)
    
    @property
    def top(self) -> float:
        """Top of line bounding box"""
        if not self.chars:
            return 0
        return min(c.top for c in self.chars)
    
    @property
    def bottom(self) -> float:
        """Bottom of line bounding box"""
        if not self.chars:
            return 0
        return max(c.bottom for c in self.chars)
    
    @property
    def x0(self) -> float:
        """Left edge of line"""
        if not self.chars:
            return 0
        return min(c.x0 for c in self.chars)
    
    @property
    def x1(self) -> float:
        """Right edge of line"""
        if not self.chars:
            return 0
        return max(c.x1 for c in self.chars)
    
    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        """Bounding box of entire line"""
        return (self.x0, self.top, self.x1, self.bottom)
    
    @property
    def body_size(self) -> float:
        """Most common font size in line (body text size)"""
        if not self.chars:
            return 10.0
        sizes = [round(c.size, 2) for c in self.chars]
        return Counter(sizes).most_common(1)[0][0]
    
    @property
    def body_baseline(self) -> float:
        """Average bottom of body-sized chars"""
        if not self.chars:
            return 0
        body = self.body_size
        base_chars = [c for c in self.chars if abs(c.size - body) < 0.5]
        if not base_chars:
            base_chars = self.chars
        return sum(c.bottom for c in base_chars) / len(base_chars)

    # Compatibility with spec naming
    @property
    def baseline_y(self) -> float:
        return self.body_baseline

    @property
    def median_size(self) -> float:
        return self.body_size
    
    @property
    def body_mid_y(self) -> float:
        """Average mid_y of body-sized chars"""
        if not self.chars:
            return 0
        body = self.body_size
        base_chars = [c for c in self.chars if abs(c.size - body) < 0.5]
        if not base_chars:
            base_chars = self.chars
        return sum(c.mid_y for c in base_chars) / len(base_chars)


@dataclass
class PageData:
    """
    Complete page data with line grouping.
    """
    page_num: int  # 1-indexed
    width: float
    height: float
    lines: List[LineData] = field(default_factory=list)
    
    @property
    def text(self) -> str:
        """Full page text with newlines"""
        return '\n'.join(line.text for line in self.lines)
    
    @property
    def char_count(self) -> int:
        """Total character count"""
        return sum(len(line.chars) for line in self.lines)
    
    def get_line(self, line_id: int) -> Optional[LineData]:
        """Get line by ID"""
        for line in self.lines:
            if line.line_id == line_id:
                return line
        return None
    
    def iter_chars(self):
        """Iterate all chars with (line_id, char) pairs"""
        for line in self.lines:
            for char in line.chars:
                yield line.line_id, char

    def get_left_context(self, line_id: int, x0: float, max_chars: int = 32) -> str:
        """
        Same-line left context for a bbox x0.
        Does not cross lines. Collapses whitespace.
        """
        line = self.get_line(line_id)
        if not line or not line.chars:
            return ""
        left_chars = [c for c in line.chars if c.x1 <= x0]
        if not left_chars:
            return ""
        s = "".join(c.text for c in left_chars[-max_chars:])
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @dataclass
    class TextMatch:
        page_num: int
        bbox: Tuple[float, float, float, float]
        line_id: int
        match_text: str

    def locate_text_matches(self, pattern: re.Pattern) -> List['PageData.TextMatch']:
        """
        Locate regex matches in line text and approximate bbox using char positions.
        """
        matches: List[PageData.TextMatch] = []
        for line in self.lines:
            text = line.text
            for m in pattern.finditer(text):
                bbox = _slice_bbox_from_line(line, m.start(), m.end())
                matches.append(PageData.TextMatch(
                    page_num=self.page_num,
                    bbox=bbox,
                    line_id=line.line_id,
                    match_text=m.group(0),
                ))
        return matches


def _slice_bbox_from_line(line: LineData, start: int, end: int) -> Tuple[float, float, float, float]:
    """
    Compute bbox for a substring in line.text using per-char boxes.
    Works best when CharData.text is single-character.
    """
    if not line.chars or start >= end:
        return line.bbox

    pos = 0
    start_char: Optional[CharData] = None
    end_char: Optional[CharData] = None

    for ch in line.chars:
        ch_len = max(1, len(ch.text))
        next_pos = pos + ch_len
        if start_char is None and start < next_pos:
            start_char = ch
        if end <= next_pos:
            end_char = ch
            break
        pos = next_pos

    if start_char and end_char:
        return (start_char.x0, min(start_char.top, end_char.top), end_char.x1, max(start_char.bottom, end_char.bottom))
    if start_char:
        return start_char.bbox
    return line.bbox


def build_page_data(
    page_chars: List[Dict[str, Any]],
    page_num: int,
    page_width: float = 612.0,
    page_height: float = 792.0,
    line_tolerance: float = 4.0  # kept for API compat, but dynamic is used
) -> PageData:
    """
    Build PageData from pdfplumber chars.
    
    Uses dynamic line tolerance based on median font size, and allows
    superscript characters to be "attached" back to their parent line.
    
    Args:
        page_chars: List of char dicts from pdfplumber
        page_num: 1-indexed page number
        page_width: Page width in points
        page_height: Page height in points
        line_tolerance: (legacy) Vertical tolerance for line grouping
    
    Returns:
        PageData with chars grouped into lines
    """
    if not page_chars:
        return PageData(page_num=page_num, width=page_width, height=page_height)
    
    # 1) Estimate page median font size -> dynamic line tolerance
    sizes_all = [c.get('size', 0) for c in page_chars if c.get('size', 0) > 0]
    median_size = statistics.median(sizes_all) if sizes_all else 10.0
    line_tol = max(3.0, median_size * 0.35)   # 10pt -> ~3.5px, 12pt -> ~4.2px
    attach_tol = max(6.0, median_size * 0.70)  # wider tolerance for superscript attachment
    
    def mid_y(ch):
        return (ch.get('top', 0) + ch.get('bottom', 0)) / 2
    
    # Sort by mid_y then x0 (better for mixed superscript lines)
    sorted_chars = sorted(page_chars, key=lambda c: (mid_y(c), c.get('x0', 0)))
    
    # Group into lines with superscript attachment
    raw_lines: List[List[Dict[str, Any]]] = []
    if sorted_chars:
        current_line = [sorted_chars[0]]
        for c in sorted_chars[1:]:
            prev = current_line[-1]
            dy = abs(mid_y(c) - mid_y(prev))
            
            # Rule A: normal character clustering with dynamic tolerance
            if dy <= line_tol:
                current_line.append(c)
                continue
            
            # Rule B: superscript "attach back to parent line"
            # Conditions: smaller font, near right side of prev char, vertical offset not extreme
            c_size = c.get('size', 0) or median_size
            p_size = prev.get('size', 0) or median_size
            gap = c.get('x0', 0) - prev.get('x1', 0)
            
            looks_like_sup_attach = (
                c_size <= p_size * 0.95 and
                -1.0 <= gap <= (median_size * 0.8) and
                dy <= attach_tol
            )
            if looks_like_sup_attach:
                current_line.append(c)
                continue
            
            # Start new line
            raw_lines.append(sorted(current_line, key=lambda x: x.get('x0', 0)))
            current_line = [c]
        
        raw_lines.append(sorted(current_line, key=lambda x: x.get('x0', 0)))
    
    # Convert raw lines to LineData
    lines: List[LineData] = []
    for raw_line in raw_lines:
        char_data_list = [CharData.from_pdfplumber(c) for c in raw_line]
        lines.append(LineData(
            line_id=len(lines),
            chars=char_data_list
        ))

    # Assign zones (title/body/footer) by vertical proportion
    # title: top 15%, footer: bottom 15%
    for ln in lines:
        mid_y = (ln.top + ln.bottom) / 2 if ln.chars else 0.0
        if page_height > 0 and mid_y < page_height * 0.15:
            ln.zone = "title"
        elif page_height > 0 and mid_y > page_height * 0.85:
            ln.zone = "footer"
        else:
            ln.zone = "body"

    return PageData(
        page_num=page_num,
        width=page_width,
        height=page_height,
        lines=lines
    )
