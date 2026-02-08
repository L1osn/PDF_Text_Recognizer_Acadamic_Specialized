"""
Superscript Citation Channel (Phase 2)
======================================
Detects superscript citations using geometric analysis.
"""

from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict, Any, Tuple
from collections import Counter, defaultdict

from ..types import (
    Occurrence, CitationCandidate, Bibliography, normalize_ref_text, parse_ref_ids
)
from ..page_model import PageData


@dataclass
class SupConfig:
    """Configuration for superscript channel"""
    base_confidence: float = 0.65
    max_digits: int = 3
    min_id: int = 1
    max_id: int = 999
    
    # Relaxed defaults for better recall
    rise_ratio: float = 0.10        # lowered from 0.15 (allow less rise)
    size_ratio: float = 0.92        # raised from 0.85 (allow near-body-size)
    adjacent_gap_ratio: float = 0.6
    
    # Right-attach rule for same-size superscripts
    right_attach_enabled: bool = True
    right_attach_rise_ratio: float = 0.06   # very small rise for attached
    right_attach_size_ratio: float = 1.05   # allow nearly same size
    right_attach_gap_max_ratio: float = 0.8
    
    zone_blocklist: Set[str] = field(default_factory=lambda: {"footer"})
    first_page_title_block: bool = True
    first_page_title_cutoff: float = 0.20  # only top 20% of first page
    
    degrade_mode: bool = False
    degrade_min_count: int = 2
    
    # Bib constraint relaxation when bib is small
    bib_hard_constraint: bool = True
    bib_min_ids_for_hard_constraint: int = 4  # Aligned with FusionConfig
    
    # Global body size (set by pipeline before extraction)
    global_body_size: Optional[float] = None
    
    # Debug
    debug: bool = False


@dataclass
class PageSupStats:
    """Per-page statistics for debugging"""
    page_num: int = 0
    lines_total: int = 0
    lines_in_zone_blocklist: int = 0
    chars_checked: int = 0
    chars_candidate: int = 0
    tokens_formed: int = 0
    tokens_rejected_dot: int = 0
    tokens_rejected_too_long: int = 0
    tokens_rejected_leading_zero: int = 0
    tokens_rejected_zero: int = 0
    tokens_rejected_no_ids: int = 0
    tokens_rejected_id_range: int = 0
    tokens_rejected_bib: int = 0
    candidates_accepted: int = 0
    sample_candidates: List[Dict[str, Any]] = field(default_factory=list)
    
    def summary(self) -> str:
        return (
            f"Page {self.page_num}: lines={self.lines_total} "
            f"(zone_blocked={self.lines_in_zone_blocklist}) | "
            f"chars={self.chars_checked}/{self.chars_candidate} | "
            f"tokens={self.tokens_formed} | "
            f"reject(dot={self.tokens_rejected_dot},long={self.tokens_rejected_too_long},"
            f"lz={self.tokens_rejected_leading_zero},zero={self.tokens_rejected_zero},"
            f"noid={self.tokens_rejected_no_ids},range={self.tokens_rejected_id_range},"
            f"bib={self.tokens_rejected_bib}) | "
            f"accepted={self.candidates_accepted}"
        )


class SuperscriptChannel:
    """
    Detect superscript citations using geometric analysis.
    """
    
    def __init__(self, config: Optional[SupConfig] = None):
        self.config = config or SupConfig()
        self.page_stats: List[PageSupStats] = []
    
    def extract(
        self,
        pages: List[PageData],
        bib: Bibliography
    ) -> List[CitationCandidate]:
        """
        Extract superscript citations from all pages.
        """
        self.page_stats = []
        
        # Determine effective bib constraint
        use_bib_hard = self.config.bib_hard_constraint
        if bib.is_valid() and len(bib.bib_ids) < self.config.bib_min_ids_for_hard_constraint:
            use_bib_hard = False  # Relax constraint when bib is small
            if self.config.debug:
                print(f"[SUP] Bib has only {len(bib.bib_ids)} IDs, relaxing hard constraint")
        
        # Determine base size: prefer global, fallback to 10.0
        global_base = self.config.global_body_size or 10.0
        
        if self.config.debug:
            print(f"[SUP] global_body_size={global_base:.2f}, use_bib_hard={use_bib_hard}")
        
        cands: List[CitationCandidate] = []
        
        for page in pages:
            stats = PageSupStats(page_num=page.page_num)
            stats.lines_total = len(page.lines)
            
            for line in page.lines:
                # Zone filter
                if line.zone in self.config.zone_blocklist:
                    stats.lines_in_zone_blocklist += 1
                    continue
                
                # First page title block filter
                if (self.config.first_page_title_block and 
                    page.page_num == 1 and 
                    line.zone == "title"):
                    # Only block if in top portion
                    line_mid = (line.top + line.bottom) / 2 if line.chars else 0
                    if line_mid < page.height * self.config.first_page_title_cutoff:
                        stats.lines_in_zone_blocklist += 1
                        continue
                
                # Use global base size, but allow page/line to influence slightly
                line_body_size = line.body_size or global_base
                # Use minimum of global and line (more conservative baseline)
                base_size = min(global_base, line_body_size) if line_body_size > 0 else global_base
                
                baseline_y = line.body_baseline
                rise_thresh = self.config.rise_ratio * base_size
                size_thresh = self.config.size_ratio * base_size
                
                # Candidate chars collection
                sup_chars = []
                prev_char = None
                
                for ch in line.chars:
                    stats.chars_checked += 1
                    t = ch.text
                    if not t:
                        prev_char = ch
                        continue
                    if t == ".":
                        prev_char = ch
                        continue
                    
                    # Character must be digit-like
                    is_digit_like = (t.isdigit() or 
                                   t in {",", "-", "–"} or 
                                   any(c in "¹²³⁴⁵⁶⁷⁸⁹⁰" for c in t))
                    if not is_digit_like:
                        prev_char = ch
                        continue
                    
                    # Method 1: Classic superscript detection (small AND raised)
                    is_classic_sup = (
                        ch.size <= size_thresh and 
                        ch.mid_y < baseline_y - rise_thresh
                    )
                    
                    # Method 2: Right-attach rule (allows near-body-size if raised and right of prev)
                    is_right_attach = False
                    if (self.config.right_attach_enabled and 
                        prev_char is not None and
                        not is_classic_sup):
                        gap = ch.x0 - prev_char.x1
                        # Check gap is reasonable
                        if -1.0 <= gap <= base_size * self.config.right_attach_gap_max_ratio:
                            # Check size is close to prev
                            if ch.size <= prev_char.size * self.config.right_attach_size_ratio:
                                # Check it's raised relative to prev (even slightly)
                                if ch.mid_y < prev_char.mid_y - base_size * self.config.right_attach_rise_ratio:
                                    is_right_attach = True
                    
                    if is_classic_sup or is_right_attach:
                        sup_chars.append(ch)
                        stats.chars_candidate += 1
                    
                    prev_char = ch
                
                if not sup_chars:
                    continue
                
                # Merge adjacent chars into tokens by x-gap
                sup_chars.sort(key=lambda c: c.x0)
                tokens: List[List[Any]] = []
                cur = [sup_chars[0]]
                for nxt in sup_chars[1:]:
                    prev = cur[-1]
                    gap = max(0.0, nxt.x0 - prev.x1)
                    if gap <= self.config.adjacent_gap_ratio * base_size:
                        cur.append(nxt)
                    else:
                        tokens.append(cur)
                        cur = [nxt]
                tokens.append(cur)
                stats.tokens_formed += len(tokens)
                
                for tok in tokens:
                    raw = "".join(c.text for c in tok)
                    
                    # Raw filters
                    if "." in raw:
                        stats.tokens_rejected_dot += 1
                        continue
                    
                    norm = normalize_ref_text(raw)
                    
                    # Digit-only constraints
                    digits_only = norm.isdigit()
                    if digits_only:
                        if len(norm) > self.config.max_digits:
                            stats.tokens_rejected_too_long += 1
                            continue
                        if len(norm) > 1 and norm.startswith("0"):
                            stats.tokens_rejected_leading_zero += 1
                            continue
                        if norm == "0":
                            stats.tokens_rejected_zero += 1
                            continue
                    
                    ref_ids = parse_ref_ids(norm, max_span=20)
                    if not ref_ids:
                        stats.tokens_rejected_no_ids += 1
                        continue
                    
                    # ID range filter
                    ref_ids = [r for r in ref_ids if self.config.min_id <= r <= self.config.max_id]
                    if not ref_ids:
                        stats.tokens_rejected_id_range += 1
                        continue
                    
                    # Bib constraint (if enabled and bib is valid and large enough)
                    if use_bib_hard and bib.is_valid():
                        filtered_ids = [r for r in ref_ids if bib.has_id(r)]
                        if not filtered_ids:
                            stats.tokens_rejected_bib += 1
                            continue
                        ref_ids = filtered_ids
                    
                    # Build candidate
                    x0 = min(c.x0 for c in tok)
                    top = min(c.top for c in tok)
                    x1 = max(c.x1 for c in tok)
                    bottom = max(c.bottom for c in tok)
                    bbox = (x0, top, x1, bottom)
                    anchor_left = page.get_left_context(line.line_id, x0, max_chars=32)
                    
                    tok_mid_y = (top + bottom) / 2.0
                    rise = (baseline_y - tok_mid_y) / (base_size or 1.0)
                    
                    occ = Occurrence(
                        page=page.page_num,
                        bbox=bbox,
                        line_id=line.line_id,
                        source="superscript",
                        anchor_left=anchor_left,
                    )
                    cand = CitationCandidate(
                        ref_ids=ref_ids,
                        occurrence=occ,
                        evidence={
                            "pattern": "superscript",
                            "raw": raw,
                            "zone": line.zone,
                            "rise": rise,
                            "base_size": base_size,
                            "tok_size": sum(c.size for c in tok) / len(tok),
                        },
                        confidence=self.config.base_confidence,
                    )
                    cands.append(cand)
                    stats.candidates_accepted += 1
                    
                    # Sample for debug
                    if len(stats.sample_candidates) < 5:
                        stats.sample_candidates.append({
                            "raw": raw,
                            "ref_ids": ref_ids,
                            "rise": round(rise, 3),
                            "anchor": anchor_left[:20] if anchor_left else "",
                        })
            
            self.page_stats.append(stats)
        
        # Debug output
        if self.config.debug:
            print("\n" + "=" * 60)
            print("SUPERSCRIPT CHANNEL PER-PAGE STATISTICS")
            print("=" * 60)
            pages_with_cands = []
            for s in self.page_stats:
                print(s.summary())
                if s.candidates_accepted > 0:
                    pages_with_cands.append(s.page_num)
                    if s.sample_candidates:
                        print(f"  Samples: {s.sample_candidates[:3]}")
            print("-" * 60)
            print(f"Pages with candidates: {pages_with_cands}")
            print(f"Total candidates before degrade filter: {len(cands)}")
            print("=" * 60 + "\n")
        
        # Degrade mode: require min occurrences per id when no bib
        if (not bib.is_valid()) and self.config.degrade_mode and self.config.degrade_min_count > 1:
            counts = Counter()
            for c in cands:
                for rid in c.ref_ids:
                    counts[rid] += 1
            filtered: List[CitationCandidate] = []
            for c in cands:
                keep_ids = [rid for rid in c.ref_ids if counts.get(rid, 0) >= self.config.degrade_min_count]
                if not keep_ids:
                    continue
                c.ref_ids = keep_ids
                filtered.append(c)
            
            if self.config.debug:
                print(f"[SUP] Degrade mode filtered: {len(cands)} -> {len(filtered)}")
            cands = filtered
        
        return cands
    
    def get_page_stats(self) -> List[PageSupStats]:
        """Get per-page statistics from last extraction"""
        return self.page_stats


def extract_superscript_candidates(
    pages: List[PageData],
    bib: Bibliography,
    config: Optional[SupConfig] = None
) -> List[CitationCandidate]:
    """
    Convenience function for superscript extraction.
    """
    channel = SuperscriptChannel(config)
    return channel.extract(pages, bib)
