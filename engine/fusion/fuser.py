"""
Citation Fusion
===============
Merges candidates from multiple channels, deduplicates occurrences,
applies bib constraints, and produces final RefEntry list.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from collections import defaultdict

from ..types import (
    Occurrence, CitationCandidate, RefEntry, Bibliography
)


@dataclass
class FusionConfig:
    """Configuration for fusion"""
    dedup_center_round: float = 1.0
    min_confidence: float = 0.0
    degrade_mode: bool = False
    degrade_min_count: int = 2
    multi_source_boost: float = 0.1  # Confidence boost for multi-source refs
    multi_occurrence_boost: float = 0.05  # per extra occurrence
    max_occurrence_boost: float = 0.2
    
    # Soft constraint parameters
    soft_constraint_penalty: float = 0.3  # Confidence penalty for unlinked citations
    bib_min_ids_for_hard_constraint: int = 4  # Min bib entries to enforce hard filter
    
    # Upper bound filtering
    max_id_multiplier: float = 2.0  # Reject IDs > max(bib_ids) * this value


class CitationFuser:
    """
    Fuse citation candidates from multiple channels.
    
    Process:
    1. Group candidates by ref_id
    2. Deduplicate occurrences (same location)
    3. Merge sources
    4. Calculate confidence
    5. Apply bib constraint and degrade mode filters
    6. Link bibliography details
    """
    
    def __init__(self, config: Optional[FusionConfig] = None):
        self.config = config or FusionConfig()
    
    def fuse(
        self,
        candidates: List[CitationCandidate],
        bib: Bibliography
    ) -> List[RefEntry]:
        """
        Fuse candidates into final RefEntry list.
        
        Args:
            candidates: All candidates from all channels
            bib: Bibliography for linking
        
        Returns:
            List of RefEntry sorted by ref_id
        """
        # 1. Group by ref_id
        groups: Dict[int, List[CitationCandidate]] = defaultdict(list)
        
        for cand in candidates:
            for ref_id in cand.ref_ids:
                groups[ref_id].append(cand)
        
        # 1.5. Filter dense duplicates (page headers, figure numbers)
        groups = self._filter_dense_duplicates(groups)
        
        # 2. Create RefEntry for each ref_id
        entries: List[RefEntry] = []
        
        for ref_id, cands in groups.items():
            entry = self._create_entry(ref_id, cands, bib)
            if entry:
                entries.append(entry)
        
        # 3. Apply filters
        entries = self._apply_filters(entries, bib)
        
        # 4. Apply soft constraints and penalties
        entries = self._apply_soft_constraints(entries, bib)
        
        # 5. Sort by ref_id
        entries.sort(key=lambda e: e.ref_id)
        
        return entries
    
    def _create_entry(
        self,
        ref_id: int,
        cands: List[CitationCandidate],
        bib: Bibliography
    ) -> Optional[RefEntry]:
        """Create RefEntry from candidates for a single ref_id"""
        entry = RefEntry(ref_id=ref_id)
        
        seen_keys: Set[tuple] = set()
        max_confidence = 0.0
        sources: Set[str] = set()
        
        for cand in cands:
            occ = cand.occurrence
            
            # Deduplicate by location key
            cx = (occ.bbox[0] + occ.bbox[2]) / 2.0
            cy = (occ.bbox[1] + occ.bbox[3]) / 2.0
            r = self.config.dedup_center_round if self.config.dedup_center_round > 0 else 1.0
            rcx = round(cx / r) * r
            rcy = round(cy / r) * r
            dedup_key = (occ.page, occ.line_id, rcx, rcy, occ.source)
            
            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                entry.add_occurrence(occ)
            
            sources.add(occ.source)
            max_confidence = max(max_confidence, cand.confidence)
        
        # Multi-source boost
        if len(sources) > 1:
            max_confidence += self.config.multi_source_boost

        # Multi-occurrence boost
        if entry.count > 1:
            max_confidence += min(self.config.max_occurrence_boost, self.config.multi_occurrence_boost * (entry.count - 1))
        
        entry.confidence = min(max_confidence, 1.0)
        entry.sources = sources
        
        # Link bib detail
        if bib.has_id(ref_id):
            entry.bib_detail = bib.get_detail(ref_id)
            entry.unlinked_to_bib = False
        else:
            entry.unlinked_to_bib = True
        
        return entry if entry.occurrences else None
    
    def _apply_filters(
        self,
        entries: List[RefEntry],
        bib: Bibliography
    ) -> List[RefEntry]:
        """Apply confidence, degrade mode, and upper bound filters"""
        result = []
        
        # Calculate upper bound filter if bib is valid
        max_valid_id = None
        if bib.is_valid() and bib.bib_ids:
            max_bib_id = max(bib.bib_ids)
            max_valid_id = int(max_bib_id * self.config.max_id_multiplier)
        
        for entry in entries:
            # Confidence filter
            if entry.confidence < self.config.min_confidence:
                continue
            
            # Upper bound filter: reject obvious false IDs
            if max_valid_id is not None and entry.ref_id > max_valid_id:
                continue
            
            # Degrade mode: require minimum occurrences when no bib
            if not bib.is_valid() and self.config.degrade_mode:
                if entry.count < self.config.degrade_min_count:
                    continue
            
            result.append(entry)
        
        return result
    
    def _apply_soft_constraints(
        self,
        entries: List[RefEntry],
        bib: Bibliography
    ) -> List[RefEntry]:
        """
        Apply soft constraints for citations not in bibliography.
        
        Logic:
        - If bib has >= bib_min_ids_for_hard_constraint entries:
          - Citations NOT in bib get confidence penalty (soft constraint)
          - Citations still kept but flagged with unlinked_to_bib=True
        - If bib has < bib_min_ids_for_hard_constraint entries:
          - No penalty applied (bib may be incomplete)
        """
        # Only apply soft constraint if bib is substantial
        if not bib.is_valid():
            return entries
        
        if bib.count < self.config.bib_min_ids_for_hard_constraint:
            # Bib too small, don't penalize
            return entries
        
        # Apply penalty to unlinked citations
        for entry in entries:
            if entry.unlinked_to_bib:
                entry.confidence = max(0.0, entry.confidence - self.config.soft_constraint_penalty)
        
        # Filter out entries that fell below min_confidence after penalty
        return [e for e in entries if e.confidence >= self.config.min_confidence]
    
    def _filter_dense_duplicates(
        self,
        groups: Dict[int, List[CitationCandidate]]
    ) -> Dict[int, List[CitationCandidate]]:
        """
        Filter dense duplicates: same ref_id appearing multiple times
        on the same page/line (likely page headers, figure numbers).
        
        Strategy: For each ref_id, if there are multiple candidates on
        the same (page, line_id), keep only the first one.
        """
        filtered_groups: Dict[int, List[CitationCandidate]] = {}
        
        for ref_id, cands in groups.items():
            # Track (page, line_id) -> first candidate
            seen_lines: Dict[tuple, CitationCandidate] = {}
            kept_cands = []
            
            for cand in cands:
                page_line_key = (cand.occurrence.page, cand.occurrence.line_id)
                
                if page_line_key not in seen_lines:
                    # First occurrence on this line - keep it
                    seen_lines[page_line_key] = cand
                    kept_cands.append(cand)
                # else: duplicate on same line - skip it
            
            if kept_cands:
                filtered_groups[ref_id] = kept_cands
        
        return filtered_groups


def fuse_candidates(
    candidates: List[CitationCandidate],
    bib: Bibliography,
    config: Optional[FusionConfig] = None
) -> List[RefEntry]:
    """
    Convenience function for fusion.
    """
    fuser = CitationFuser(config)
    return fuser.fuse(candidates, bib)
