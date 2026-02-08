"""
Citation Pipeline
=================
Single entry point for running the complete citation detection pipeline.
Orchestrates: PageModel -> BibExtraction -> Channels -> Fusion -> RefEntry
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional, Set
from collections import Counter

from .types import (
    CitationCandidate, RefEntry
)
from .page_model import PageData
from .bib import BibliographyExtractor, extract_bibliography
from .channels import BracketChannel, BracketConfig, SuperscriptChannel, SupConfig
from .fusion import CitationFuser, FusionConfig


@dataclass
class PipelineConfig:
    """Complete pipeline configuration"""
    # Channel configs
    bracket_config: BracketConfig = field(default_factory=BracketConfig)
    sup_config: SupConfig = field(default_factory=SupConfig)
    fusion_config: FusionConfig = field(default_factory=FusionConfig)
    
    # Feature toggles
    enable_bracket: bool = True
    enable_superscript: bool = False  # Phase 2
    
    # Debug
    debug: bool = False
    
    @classmethod
    def phase1(cls) -> 'PipelineConfig':
        """Phase 1 config: bracket only"""
        return cls(
            enable_bracket=True,
            enable_superscript=False,
        )
    
    @classmethod
    def phase2(cls) -> 'PipelineConfig':
        """Phase 2 config: bracket + superscript"""
        return cls(
            enable_bracket=True,
            enable_superscript=True,
        )


@dataclass
class DebugBundle:
    """Debug information from pipeline run"""
    bib_ids_count: int = 0
    bib_map_count: int = 0
    bib_ids_sample: List[int] = field(default_factory=list)
    
    bracket_candidates_count: int = 0
    superscript_candidates_count: int = 0
    
    entries_count: int = 0
    total_occurrences: int = 0
    
    reject_reasons: Dict[str, int] = field(default_factory=dict)
    
    # New fields for superscript debugging
    global_body_size: float = 0.0
    pages_with_sup_candidates: List[int] = field(default_factory=list)
    pages_in_entries: Set[int] = field(default_factory=set)
    sup_per_page_stats: List[str] = field(default_factory=list)
    bib_hard_constraint_used: bool = True
    
    def summary(self) -> str:
        """Generate summary string"""
        lines = [
            "=" * 60,
            "CITATION ENGINE DEBUG SUMMARY",
            "=" * 60,
            f"Global Body Size: {self.global_body_size:.2f}",
            f"Bibliography IDs: {self.bib_ids_count}",
            f"Bibliography Map: {self.bib_map_count}",
            f"Bib Hard Constraint: {self.bib_hard_constraint_used}",
            f"Bib IDs Sample: {self.bib_ids_sample[:10]}",
            "",
            f"Bracket Candidates: {self.bracket_candidates_count}",
            f"Superscript Candidates: {self.superscript_candidates_count}",
            f"Pages with Sup Candidates: {self.pages_with_sup_candidates}",
            "",
            f"Final Entries: {self.entries_count}",
            f"Total Occurrences: {self.total_occurrences}",
            f"Pages in Entries: {sorted(self.pages_in_entries)}",
            "",
            "Reject Reasons:",
        ]
        for reason, count in sorted(self.reject_reasons.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {reason}: {count}")
        
        if self.sup_per_page_stats:
            lines.append("")
            lines.append("Superscript Per-Page Stats (first 10):")
            for stat in self.sup_per_page_stats[:10]:
                lines.append(f"  {stat}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


def estimate_global_body_size(all_chars: List[Dict[str, Any]]) -> float:
    """
    Estimate the global body text size across all pages.
    
    Strategy:
    1. Collect all font sizes
    2. Filter out extremes (< 5pt or > 20pt)
    3. Use mode (most common) as body size
    """
    sizes = []
    for c in all_chars:
        s = c.get('size', 0)
        if 5.0 <= s <= 20.0:  # Reasonable body text range
            sizes.append(round(s, 1))  # Round for mode calculation
    
    if not sizes:
        return 10.0
    
    # Use mode (most common size)
    counter = Counter(sizes)
    mode_size = counter.most_common(1)[0][0]
    return mode_size


class CitationPipeline:
    """
    Main citation detection pipeline.
    
    Usage:
        pipeline = CitationPipeline()
        entries, debug = pipeline.run_from_pages(page_models, pages_text)
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig.phase1()
        
        # Initialize components
        self.bib_extractor = BibliographyExtractor()
        self.bracket_channel = BracketChannel(self.config.bracket_config)
        self.sup_channel = SuperscriptChannel(self.config.sup_config)
        self.fuser = CitationFuser(self.config.fusion_config)
    
    def run_from_pages(
        self,
        page_models: List[PageData],
        pages_text: List[str],
        global_body_size: Optional[float] = None
    ) -> Tuple[List[RefEntry], DebugBundle]:
        """
        Run pipeline from pre-built page models.
        
        Args:
            page_models: List of PageData objects
            pages_text: List of page text strings
            global_body_size: Optional pre-calculated global body size
        
        Returns:
            Tuple of (ref_entries, debug_bundle)
        """
        debug = DebugBundle()
        
        # Set global body size if provided
        if global_body_size is not None:
            debug.global_body_size = global_body_size
            self.sup_channel.config.global_body_size = global_body_size
        
        # Propagate debug flag
        self.sup_channel.config.debug = self.config.debug
        
        # 1. Extract bibliography
        bib = extract_bibliography(pages_text)
        
        debug.bib_ids_count = len(bib.bib_ids)
        debug.bib_map_count = len(bib.bib_map)
        debug.bib_ids_sample = sorted(list(bib.bib_ids))[:20]
        
        # Determine if bib hard constraint will be used
        debug.bib_hard_constraint_used = (
            self.sup_channel.config.bib_hard_constraint and
            bib.is_valid() and
            len(bib.bib_ids) >= self.sup_channel.config.bib_min_ids_for_hard_constraint
        )
        
        if self.config.debug:
            print(f"[PIPELINE] Bibliography: {debug.bib_ids_count} IDs, {debug.bib_map_count} mapped")
            print(f"[PIPELINE] Bib hard constraint: {debug.bib_hard_constraint_used}")
        
        # 2. Run channels
        candidates: List[CitationCandidate] = []
        
        # Bracket channel (Phase 1)
        if self.config.enable_bracket:
            bracket_cands = self.bracket_channel.extract(page_models, bib)
            candidates.extend(bracket_cands)
            debug.bracket_candidates_count = len(bracket_cands)
            
            if self.config.debug:
                print(f"[PIPELINE] Bracket candidates: {len(bracket_cands)}")
        
        # Superscript channel (Phase 2)
        if self.config.enable_superscript:
            # When bibliography is empty, enable degrade mode for superscript channel
            self.sup_channel.config.degrade_mode = (not bib.is_valid())
            sup_cands = self.sup_channel.extract(page_models, bib)
            candidates.extend(sup_cands)
            debug.superscript_candidates_count = len(sup_cands)
            
            # Collect per-page stats
            for stat in self.sup_channel.get_page_stats():
                debug.sup_per_page_stats.append(stat.summary())
                if stat.candidates_accepted > 0:
                    debug.pages_with_sup_candidates.append(stat.page_num)
            
            if self.config.debug:
                print(f"[PIPELINE] Superscript candidates: {len(sup_cands)}")
                print(f"[PIPELINE] Pages with sup candidates: {debug.pages_with_sup_candidates}")
        
        # 3. Fuse candidates
        # Auto-enable degrade mode if bibliography is empty
        if not bib.is_valid():
            self.fuser.config.degrade_mode = True
        entries = self.fuser.fuse(candidates, bib)
        
        debug.entries_count = len(entries)
        debug.total_occurrences = sum(e.count for e in entries)
        
        # Collect pages in entries
        for entry in entries:
            for occ in entry.occurrences:
                debug.pages_in_entries.add(occ.page)
        
        if self.config.debug:
            print(f"[PIPELINE] Final entries: {len(entries)}")
            print(f"[PIPELINE] Pages in entries: {sorted(debug.pages_in_entries)}")
        
        return entries, debug


def run_citation_pipeline(
    pdf_path: str,
    config: Optional[PipelineConfig] = None
) -> Tuple[List[RefEntry], DebugBundle]:
    """
    Spec-friendly single entry point for running the pipeline on a PDF path.
    """
    import pdfplumber
    from .page_model import build_page_data

    cfg = config or PipelineConfig.phase1()
    page_models: List[PageData] = []
    pages_text: List[str] = []
    all_chars: List[Dict[str, Any]] = []

    # First pass: collect all chars for global body size estimation
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.chars:
                all_chars.extend(page.chars)
    
    # Estimate global body size
    global_body_size = estimate_global_body_size(all_chars)
    
    if cfg.debug:
        print(f"[PIPELINE] Estimated global body size: {global_body_size:.2f}")
    
    # Second pass: build page models
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            page_data = build_page_data(
                page.chars,
                page_num=page_num,
                page_width=page.width or 612.0,
                page_height=page.height or 792.0,
            )
            page_models.append(page_data)
            pages_text.append(page_data.text)

    pipeline = CitationPipeline(cfg)
    return pipeline.run_from_pages(page_models, pages_text, global_body_size)
