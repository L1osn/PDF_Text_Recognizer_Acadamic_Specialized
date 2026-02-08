"""
Bibliography Extractor
======================
Extracts bibliography section and parses reference IDs.
Provides constraint set for citation validation.
"""

import re
from typing import Dict, Set, List, Optional, Tuple, Union
from ..types import Bibliography


class BibliographyExtractor:
    """
    Extract and parse bibliography section from document text.
    
    Supports:
    - Header detection: "References", "Bibliography", "Works Cited", etc.
    - Entry formats: [1], 1., (1), etc.
    - Multiple entry patterns in one document
    """
    
    # Section header patterns (case-insensitive)
    HEADER_PATTERNS = [
        r'references\s*$',
        r'bibliography\s*$',
        r'works\s+cited\s*$',
        r'literature\s+cited\s*$',
        r'references\s+and\s+notes\s*$',
        r'参考文献\s*$',  # Chinese
    ]
    
    # Entry start patterns - STRICT: only match line beginnings
    # This prevents pollution from years and inline numbers
    ENTRY_PATTERNS = [
        (r'^\s*\[(\d+)\]', 'bracket'),     # [1] Author...
        (r'^\s*(\d+)\.', 'dot'),           # 1. Author...
        (r'^\s*\((\d+)\)', 'paren'),       # (1) Author...
    ]
    
    def __init__(self):
        self._header_regex = re.compile(
            '|'.join(f'({p})' for p in self.HEADER_PATTERNS),
            re.IGNORECASE | re.MULTILINE
        )
    
    def extract(self, full_text: str, min_entries: int = 3) -> Bibliography:
        """
        Extract bibliography from document text.
        
        Args:
            full_text: Complete document text
            min_entries: Minimum entries to confirm valid bibliography
        
        Returns:
            Bibliography object with parsed entries
        """
        # 1. Find bibliography section start
        section_start, section_text = self._find_section(full_text)
        
        if not section_text:
            # Fallback: Try content-based detection
            section_start, section_text = self._detect_by_content(full_text)
        
        if not section_text:
            return Bibliography()
        
        # 2. Parse entries
        bib_ids, bib_map = self._parse_entries(section_text)
        
        # 3. Validate minimum entries
        if len(bib_ids) < min_entries:
            return Bibliography()
        
        return Bibliography(
            bib_ids=bib_ids,
            bib_map=bib_map,
            start_page=-1,  # TODO: Track page from spans
            raw_text=section_text[:500]  # Store first 500 chars for debugging
        )
    
    def _find_section(self, text: str) -> Tuple[int, str]:
        """
        Find bibliography section by header.
        Returns (start_position, section_text).
        """
        # Search for headers in last 60% of document
        search_start = int(len(text) * 0.4)
        search_text = text[search_start:]
        
        match = self._header_regex.search(search_text)
        if match:
            # Find end of header line
            header_end = match.end()
            # Look for next newline to start parsing entries
            newline_pos = search_text.find('\n', header_end)
            if newline_pos == -1:
                newline_pos = header_end
            
            section_text = search_text[newline_pos:].strip()
            return search_start + match.start(), section_text
        
        return -1, ""
    
    def _detect_by_content(self, text: str) -> Tuple[int, str]:
        """
        Fallback: Detect bibliography by sequential entry pattern [1], [2], [3]...
        """
        # Search last 50% of document
        search_start = int(len(text) * 0.5)
        search_text = text[search_start:]
        
        # Look for start of numbered list: [1] or 1.
        patterns_to_try = [
            r'\n\s*\[1\]',    # [1]
            r'\n\s*1\.\s+[A-Z]',  # 1. followed by capital letter
        ]
        
        for pattern in patterns_to_try:
            match = re.search(pattern, search_text)
            if match:
                # Check if followed by [2] or 2.
                candidate_text = search_text[match.start():]
                if self._has_sequential_entries(candidate_text):
                    return search_start + match.start(), candidate_text
        
        return -1, ""
    
    def _has_sequential_entries(self, text: str, min_seq: int = 3) -> bool:
        """Check if text has sequential numbered entries"""
        # Look for [1], [2], [3] or 1., 2., 3.
        bracket_matches = re.findall(r'\[(\d+)\]', text[:2000])
        if len(bracket_matches) >= min_seq:
            nums = [int(m) for m in bracket_matches[:min_seq]]
            if nums == list(range(1, min_seq + 1)):
                return True
        
        dot_matches = re.findall(r'\n\s*(\d+)\.\s+[A-Z]', text[:2000])
        if len(dot_matches) >= min_seq:
            nums = [int(m) for m in dot_matches[:min_seq]]
            if nums == list(range(1, min_seq + 1)):
                return True
        
        return False
    
    def _parse_entries(self, section_text: str) -> Tuple[Set[int], Dict[int, str]]:
        """
        Parse bibliography entries from section text.
        Returns (bib_ids set, bib_map dict).
        """
        bib_ids: Set[int] = set()
        bib_map: Dict[int, str] = {}
        
        # Determine dominant pattern
        pattern, pattern_type = self._detect_entry_pattern(section_text)
        if pattern is None:
            return bib_ids, bib_map
        
        # Find all entries
        matches = list(re.finditer(pattern, section_text, re.MULTILINE))
        
        for i, match in enumerate(matches):
            ref_num = int(match.group(1))
            
            # FILTER OUT YEARS: If >= 1000 and looks like a year, skip it
            if ref_num >= 1000:
                if self._is_likely_year(ref_num):
                    continue
            
            # Entry text: from end of match to start of next match (or end)
            start = match.end()
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(section_text)
            
            entry_text = section_text[start:end].strip()
            # Clean up entry text
            entry_text = re.sub(r'\s+', ' ', entry_text)  # Normalize whitespace
            entry_text = entry_text[:500]  # Limit length
            
            bib_ids.add(ref_num)
            bib_map[ref_num] = entry_text
        
        return bib_ids, bib_map
    
    def _detect_entry_pattern(self, text: str) -> Tuple[Optional[str], str]:
        """Detect which entry pattern is dominant"""
        sample = text[:3000]
        
        best_pattern = None
        best_type = ""
        best_count = 0
        
        for pattern, ptype in self.ENTRY_PATTERNS:
            count = len(re.findall(pattern, sample, re.MULTILINE))
            if count > best_count:
                best_count = count
                best_pattern = pattern
                best_type = ptype
        
        if best_count < 2:
            return None, ""
        
        return best_pattern, best_type
    
    def _is_likely_year(self, num: int) -> bool:
        """
        Check if a number >= 1000 is likely a year (19xx or 20xx).
        Used to filter out false bibliography IDs.
        """
        return (1900 <= num <= 2099)


def extract_bibliography(pages_text: Union[List[str], str]) -> Bibliography:
    """
    Convenience function to extract bibliography.

    Accepts either:
    - pages_text: List[str] (preferred, per spec)
    - full_text: str (backward-compatible)
    """
    extractor = BibliographyExtractor()
    if isinstance(pages_text, list):
        full_text = "\n".join(pages_text)
    else:
        full_text = str(pages_text)
    return extractor.extract(full_text)
