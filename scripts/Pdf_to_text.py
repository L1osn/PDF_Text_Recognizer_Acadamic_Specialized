
import pdfplumber
import pyperclip
import re
import os
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional

# New engine imports
from engine import CitationPipeline, RefEntry
from engine.pipeline import PipelineConfig, DebugBundle
from engine.page_model import build_page_data, PageData
from engine.types import Bibliography

@dataclass
class TextSpan:
    """Represents a continuous span of text with the same font properties"""
    text: str
    font_name: str
    font_size: float
    page: int
    bbox: Tuple[float, float, float, float]  # (x0, top, x1, bottom)
    color: Tuple[float, ...] = (0, 0, 0) # R, G, B or C, M, Y, K
    is_bold: bool = False
    is_italic: bool = False
    is_superscript: bool = False

class LayoutAnalyzer:
    """
    Centralized geometry engine for PDF layout analysis.
    Handles line grouping, body text detection, and geometric superscript identification.
    
    V2: Improved superscript detection using:
    - Mid-Y (center of mass) instead of bottom
    - X-height estimation from lowercase chars
    - Right-attachment heuristic for upper-right superscripts
    - Relaxed content filter (allow alphanumeric)
    - Dynamic gap threshold based on body_size
    - Fallback sweep for small chars at line end
    """
    
    @staticmethod
    def process_page(page_chars: List[Dict[str, Any]], 
                     sup_size_ratio: float = 0.80,
                     sup_rise_ratio: float = 0.15,
                     page_num: int = 1,
                     page_height: float = 792.0) -> Tuple[List[Dict[str, Any]], List[Dict]]:
        """
        Input: List of page char objects from pdfplumber
        Output: Tuple of (processed_chars, sup_tokens)
            - processed_chars: char objects with is_superscript marked (text NOT modified)
            - sup_tokens: aggregated superscript tokens by line adjacency
        """
        if not page_chars: 
            return [], []
        
        # 1. Vertical Clustering: Group lines by 'top' coordinate (tolerance 4px)
        sorted_chars = sorted(page_chars, key=lambda c: c.get('top', 0))
        lines = []
        
        if sorted_chars:
            current_line = [sorted_chars[0]]
            for c in sorted_chars[1:]:
                if abs(c.get('top', 0) - current_line[-1].get('top', 0)) > 4.0: 
                    lines.append(sorted(current_line, key=lambda x: x.get('x0', 0)))
                    current_line = [c]
                else:
                    current_line.append(c)
            lines.append(sorted(current_line, key=lambda x: x.get('x0', 0)))

        # 2. In-line Analysis
        processed_chars = []
        sup_tokens = []
        
        # Symbols that are definitely NOT citations (footnote markers, special chars)
        exclude_symbols = {'*', '†', '‡', '§', '¶', '#', '°', '©', '®', '™', '…'}
        
        for line_num, line in enumerate(lines):
            if not line: continue
            
            # ============ A. Calculate Body Metrics ============
            sizes = [round(c.get('size', 0), 2) for c in line]
            if not sizes: continue
            
            # Body size = most common size in line
            body_size = Counter(sizes).most_common(1)[0][0]
            if body_size < 0.1: body_size = 10.0
            
            # Estimate x-height from lowercase letters (more accurate than body_size)
            lowercase_chars = [c for c in line if c.get('text', '').islower()]
            if lowercase_chars:
                x_height = sum(c.get('size', 0) for c in lowercase_chars) / len(lowercase_chars)
            else:
                x_height = body_size * 0.7  # Fallback estimate
            
            # Body baseline from normal-sized chars
            base_chars = [c for c in line if abs(c.get('size', 0) - body_size) < 0.5]
            if not base_chars: base_chars = line
            body_baseline = sum(c.get('bottom', 0) for c in base_chars) / len(base_chars)
            body_mid_y = sum((c.get('top', 0) + c.get('bottom', 0)) / 2 for c in base_chars) / len(base_chars)
            
            # Median x position for fallback detection
            all_x0 = sorted(c.get('x0', 0) for c in line)
            median_x = all_x0[len(all_x0) // 2] if all_x0 else 0

            # ============ B. First Pass: Mark Superscripts ============
            line_chars = []
            prev_char = None
            
            for i, char in enumerate(line):
                new_char = char.copy() 
                raw_text = new_char.get('text', '')
                new_char['_line_num'] = line_num
                
                char_size = new_char.get('size', 0)
                char_top = new_char.get('top', 0)
                char_bottom = new_char.get('bottom', 0)
                char_mid_y = (char_top + char_bottom) / 2
                char_x0 = new_char.get('x0', 0)
                
                is_sup = False
                
                # --- Rule 0: Unicode superscripts are always superscripts ---
                if raw_text in "¹²³⁴⁵⁶⁷⁸⁹⁰ⁱⁿ":
                    is_sup = True
                
                # --- Rule 1: Size + Raised (using mid_y, not bottom) ---
                # More lenient: use x_height for size comparison
                elif char_size <= x_height * sup_size_ratio:
                    # Check if raised: mid_y is above body center by threshold
                    rise_threshold = body_size * sup_rise_ratio
                    if char_mid_y < (body_mid_y - rise_threshold):
                        # Content filter: allow digits and letters, exclude special symbols
                        if raw_text not in exclude_symbols:
                            is_sup = True
                
                # --- Rule 2: Right-Attachment Heuristic (RELAXED) ---
                # Allow same-size chars that are positioned right+higher
                if not is_sup and prev_char:
                    prev_x1 = prev_char.get('x1', 0)
                    prev_size = prev_char.get('size', body_size)
                    prev_mid_y = (prev_char.get('top', 0) + prev_char.get('bottom', 0)) / 2
                    
                    # Conditions: close to right, not much larger, higher
                    gap = char_x0 - prev_x1
                    is_right_adjacent = 0 <= gap < body_size * 0.6
                    is_higher = char_mid_y < prev_mid_y - max(1.0, body_size * 0.10)
                    
                    # Key: allow same size, only "much bigger" is rejected
                    size_ok = char_size <= prev_size * 1.05
                    
                    if is_right_adjacent and is_higher and size_ok and raw_text not in exclude_symbols:
                        is_sup = True
                
                new_char['is_superscript'] = is_sup
                line_chars.append(new_char)
                processed_chars.append(new_char)
                prev_char = new_char
            
            # ============ C. Fallback Sweep: Small chars at line end ============
            # If there are small chars clustered at the right side, mark them as superscripts
            small_candidates = [c for c in line_chars 
                               if c.get('size', 0) < body_size * 0.85 
                               and not c.get('is_superscript')
                               and c.get('text', '') not in exclude_symbols]
            
            if small_candidates:
                # Check if they're all on the right side of median
                candidate_x0s = [c.get('x0', 0) for c in small_candidates]
                if min(candidate_x0s) > median_x:
                    # Check if they're raised compared to body
                    candidate_mid_y = sum((c.get('top', 0) + c.get('bottom', 0)) / 2 for c in small_candidates) / len(small_candidates)
                    if candidate_mid_y < body_mid_y:
                        # Mark all as superscripts
                        for c in small_candidates:
                            c['is_superscript'] = True

            # ============ D. Collect Superscript Tokens ============
            # Dynamic gap threshold based on body_size
            gap_threshold = body_size * 0.8
            
            token_buffer = []
            anchor_buffer = []
            
            for i, char in enumerate(line_chars):
                if char.get('is_superscript'):
                    # Check adjacency
                    if token_buffer:
                        prev_x1 = token_buffer[-1].get('x1', 0)
                        curr_x0 = char.get('x0', 0)
                        if (curr_x0 - prev_x1) > gap_threshold:
                            # Gap too large - flush current token
                            sup_tokens.append(LayoutAnalyzer._flush_sup_token(
                                token_buffer, anchor_buffer, line_num, page_num, page_height
                            ))
                            token_buffer = []
                    token_buffer.append(char)
                else:
                    # Non-superscript: flush pending token
                    if token_buffer:
                        sup_tokens.append(LayoutAnalyzer._flush_sup_token(
                            token_buffer, anchor_buffer, line_num, page_num, page_height
                        ))
                        token_buffer = []
                    # Add to anchor (keep last 30 chars for context)
                    anchor_buffer.append(char.get('text', ''))
                    if len(anchor_buffer) > 30:
                        anchor_buffer.pop(0)
            
            # Flush remaining token at end of line
            if token_buffer:
                sup_tokens.append(LayoutAnalyzer._flush_sup_token(
                    token_buffer, anchor_buffer, line_num, page_num, page_height
                ))
                
        # Restore reading order
        processed_chars.sort(key=lambda c: (c.get('_line_num', 0), c.get('x0', 0)))
        return processed_chars, sup_tokens
    
    @staticmethod
    def _flush_sup_token(chars: List[Dict], anchor_chars: List[str], 
                         line_num: int, page_num: int, page_height: float) -> Dict:
        """Create a superscript token from adjacent characters"""
        # Combine text (original, no modifications)
        text = ''.join(c.get('text', '') for c in chars)
        
        # Combine bbox
        x0 = min(c.get('x0', 0) for c in chars)
        top = min(c.get('top', 0) for c in chars)
        x1 = max(c.get('x1', 0) for c in chars)
        bottom = max(c.get('bottom', 0) for c in chars)
        bbox = (x0, top, x1, bottom)
        
        # Anchor text from preceding non-superscript chars
        anchor = ''.join(anchor_chars)
        
        return {
            'text': text,
            'page': page_num,
            'bbox': bbox,
            'anchor': anchor,
            '_line_num': line_num,
            'page_height': page_height
        }

class AcademicPDFRecognizer:
    """PDF Text Recognizer specialized for academic papers"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.text_spans: List[TextSpan] = []
        self.extracted_text = ""
        self.is_color_rich = False
        self.superscripts = []  # Raw superscript tokens (geometric detection)
        # Citation analysis is handled by the new engine pipeline (`engine/`).
    
    def iter_extract_text_with_fonts(self):
        """
        Generator yielding (page_num, spans) for each page.
        Primary entry point for GUI progress updates.
        """
        # Reset state at start of new extraction
        self.superscripts = []
        self._plain_text_parts = []  # For bibliography analysis (no page separators)
        
        with pdfplumber.open(self.pdf_path) as pdf:
            colors_seen = set()
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                page_height = page.height or 792.0
                
                # [Crucial Step] Unified Geometric Analysis
                # Now returns (processed_chars, sup_tokens)
                processed_chars, sup_tokens = LayoutAnalyzer.process_page(
                    page.chars, 
                    sup_size_ratio=0.80, 
                    sup_rise_ratio=0.15,
                    page_num=page_num,
                    page_height=page_height
                )
                
                # Collect superscripts from LayoutAnalyzer (line-based tokens)
                self.superscripts.extend(sup_tokens)
                
                # Re-cluster into spans for display
                page_spans = self._cluster_chars_to_spans(processed_chars, page_num)
                
                # Build plain text for bibliography analysis
                page_text = ''.join(s.text for s in page_spans)
                self._plain_text_parts.append(page_text)
                
                # Update stats
                for s in page_spans:
                    if s.color != (0,0,0): colors_seen.add(s.color)

                yield page_num, page_spans
            
            self.is_color_rich = len(colors_seen) > 2
            
            # Store plain text for analysis (without page separators)
            self.extracted_text = '\n\n'.join(self._plain_text_parts)

    def _cluster_chars_to_spans(self, chars, page_num):
        """
        Aggregates characters into TextSpans.
        Handles:
        - Font/Color changes -> Split Span
        - Large horizontal gap -> Insert Space
        - Large vertical gap -> Split Span (Force new line)
        - Superscript flag -> Split Span (usually)
        """
        if not chars: return []
        spans = []
        buffer = []
        
        # State tracking
        curr_font = None
        curr_size = 0.0
        curr_color = (0,0,0)
        curr_bold = False
        curr_italic = False
        curr_is_sup = False
        
        last_char = None
        
        def flush_buffer():
            nonlocal buffer, curr_font, curr_size, curr_color, curr_bold, curr_italic, curr_is_sup
            if not buffer: return
            
            # Construct text with spaces
            text_parts = []
            if len(buffer) > 0:
                text_parts.append(buffer[0].get('text', ''))
                for i in range(1, len(buffer)):
                    prev = buffer[i-1]
                    curr = buffer[i]
                    # Horizontal gap check (Space insertion)
                    # Gap > 2.0 (approx 20-30% of font size usually)
                    if (curr.get('x0', 0) - prev.get('x1', 0)) > 2.0:
                        text_parts.append(" ")
                    text_parts.append(curr.get('text', ''))
            
            text_str = "".join(text_parts)
            
            if not text_str: # emptiness check
                buffer = []
                # Don't reset current font info yet, keeps continuity
                return

            # BBox calculation
            x0 = min(x.get('x0', 0) for x in buffer)
            top = min(x.get('top', 0) for x in buffer)
            x1 = max(x.get('x1', 0) for x in buffer)
            bottom = max(x.get('bottom', 0) for x in buffer)
            bbox = (x0, top, x1, bottom)
            
            spans.append(TextSpan(
                text=text_str,
                font_name=curr_font,
                font_size=curr_size,
                page=page_num,
                bbox=bbox,
                color=curr_color,
                is_bold=curr_bold,
                is_italic=curr_italic,
                is_superscript=curr_is_sup
            ))
            
            # NOTE: Superscript collection is now done in LayoutAnalyzer.process_page
            # using line-based adjacent character aggregation, not span-based
            
            buffer = []

        for c in chars:
            # Properties
            font = c.get('fontname', 'Unknown')
            size = c.get('size', 0.0)
            
            raw_color = c.get('non_stroking_color', (0,0,0))
            if raw_color is None: color = (0,0,0)
            elif isinstance(raw_color, (int, float)): color = (raw_color,)
            else: color = tuple(raw_color)
            
            is_sup = c.get('is_superscript', False)
            
            font_lower = font.lower()
            is_bold = "bold" in font_lower or "black" in font_lower
            is_italic = "italic" in font_lower
            
            # Decide if we need to split
            # 1. Logic: Attribute Change
            attr_change = (
                font != curr_font or 
                abs(size - curr_size) > 1.0 or 
                color != curr_color or 
                is_bold != curr_bold or 
                is_italic != curr_italic or 
                is_sup != curr_is_sup
            )
            
            # 2. Logic: Vertical Jump (New Line / Section)
            # Use _line_num from unified engine for stable line break detection
            vertical_jump = False
            if last_char:
                vertical_jump = c.get('_line_num') != last_char.get('_line_num')
            
            if attr_change or vertical_jump:
                flush_buffer()
                
                # Insert newline span if there was a vertical jump
                if vertical_jump:
                    spans.append(TextSpan("\n", "Control", 0, page_num, (0,0,0,0)))
                
                # Reset State
                curr_font = font
                curr_size = size
                curr_color = color
                curr_bold = is_bold
                curr_italic = is_italic
                curr_is_sup = is_sup
                
                buffer.append(c)
            else:
                buffer.append(c)
            
            last_char = c

        flush_buffer()
        
        return spans

    def extract_text_with_fonts(self) -> List[TextSpan]:
        """Extract text with font information (Blocking wrapper)"""
        self.text_spans = []  # Clear state
        for _, spans in self.iter_extract_text_with_fonts():
            self.text_spans.extend(spans)
        return self.text_spans
    
    def get_font_statistics(self) -> Dict:
        """Get statistics about fonts used in PDF"""
        font_stats = Counter()
        size_stats = Counter()
        color_stats = Counter()
        total_chars = 0
        
        for span in self.text_spans:
            if span.text == "\n": continue
            span_len = len(span.text)
            font_stats[span.font_name] += span_len
            size_stats[round(span.font_size, 1)] += span_len
            color_stats[str(span.color)] += span_len
            total_chars += span_len
        
        return {
            'fonts': dict(font_stats.most_common()),
            'sizes': dict(sorted(size_stats.most_common())),
            'colors': dict(color_stats.most_common()),
            'is_color_rich': self.is_color_rich,
            'total_chars': total_chars
        }
    
    def _detect_reference_boundary(self, use_smart_color: str = 'auto') -> Tuple[int, str]:
        """Smart detection of Reference section"""
        if not self.text_spans:
            self.extract_text_with_fonts()
        
        if not self.text_spans: return -1, ""
        
        # Determine body color
        valid_spans = [s for s in self.text_spans if s.text != "\n"]
        color_counts = Counter(str(s.color) for s in valid_spans)
        body_color_str = color_counts.most_common(1)[0][0] if color_counts else str((0,0,0))

        use_color = False
        if use_smart_color == 'force': use_color = True
        elif use_smart_color == 'auto': use_color = self.is_color_rich

        sizes = [s.font_size for s in valid_spans]
        if not sizes: return -1, ""
        median_size = sorted(sizes)[len(sizes)//2]
        
        candidates = []
        ref_keywords = ['references', 'bibliography', 'literature cited', 'references and notes']
        
        for span in self.text_spans:
            text_lower = span.text.strip().lower()
            is_match = any(text_lower == k or (text_lower.startswith(k) and len(text_lower) < 40) for k in ref_keywords)
            
            if is_match:
                score = 0
                if span.is_bold: score += 3
                if span.font_size > median_size * 1.1: score += 2
                if span.font_size > median_size * 1.5: score += 1
                
                if use_color:
                    if str(span.color) != body_color_str: score += 3
                
                max_page = self.text_spans[-1].page or 1
                rel_pos = span.page / max_page
                
                if rel_pos > 0.6: score += 3
                elif rel_pos > 0.3: score += 1
                else: score -= 2
                
                candidates.append((score, span))
        
        if candidates:
            candidates.sort(key=lambda x: (x[0], x[1].page), reverse=True)
            best_score, best_span = candidates[0]
            if best_score > 0:
                return best_span.page, best_span.text.strip()
            
        return -1, ""

    def extract_text(self, join_paragraphs=True, fix_hyphenation=True, remove_references=True, detect_headers_by_color='auto') -> str:
        """
        Extract plain text using unified LayoutAnalyzer for high fidelity.
        Reuses _cluster_chars_to_spans for consistent spacing/newline logic.
        """
        full_text_list = []
        
        # Temporarily disable superscript accumulation side-effect for plain text mode
        original_superscripts = self.superscripts
        self.superscripts = []  # Reset temporarily
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_height = page.height or 792.0
                    
                    # 1. Use Unified Layout Analysis (returns tuple now)
                    processed_chars, _ = LayoutAnalyzer.process_page(
                        page.chars,
                        sup_size_ratio=0.80,
                        sup_rise_ratio=0.15,
                        page_num=page_num,
                        page_height=page_height
                    )
                    
                    if not processed_chars: 
                        continue
                    
                    # 2. Reuse span clustering for consistent spacing logic
                    page_spans = self._cluster_chars_to_spans(processed_chars, page_num)
                    
                    # 3. Build plain text from spans
                    page_parts = []
                    for span in page_spans:
                        page_parts.append(span.text)
                    
                    page_text = "".join(page_parts)
                    full_text_list.append(page_text)
            
            self.extracted_text = "\n\n".join(full_text_list)
            
            # Restore original superscripts (don't pollute with plain text extraction)
            self.superscripts = original_superscripts
            
            return self.extracted_text
        except Exception as e:
            self.superscripts = original_superscripts  # Restore on error
            print(f"Error extracting text: {e}")
            return str(e)

    def copy_to_clipboard(self, text: str = None) -> bool:
        """Copy text to clipboard"""
        try:
            if text is None: text = self.extracted_text
            pyperclip.copy(text)
            return True
        except Exception as e:
            print(f"Clipboard error: {e}")
            return False

    # ==================== CITATION ANALYSIS (NEW ENGINE) ====================
    
    def run_citation_engine(
        self,
        enable_superscript: bool = False,
        debug: bool = False
    ) -> Tuple[List[RefEntry], DebugBundle]:
        """
        Run the new citation engine pipeline.
        
        Args:
            enable_superscript: Enable superscript channel (Phase 2)
            debug: Enable debug output
        
        Returns:
            Tuple of (ref_entries, debug_bundle)
        """
        # Print module paths for verification
        if debug:
            import engine.page_model.model as pm_module
            import engine.channels.superscript as sup_module
            import engine.pipeline as pipe_module
            print(f"[ENGINE] page_model.model: {pm_module.__file__}")
            print(f"[ENGINE] channels.superscript: {sup_module.__file__}")
            print(f"[ENGINE] pipeline: {pipe_module.__file__}")
        
        # Configure pipeline
        if enable_superscript:
            config = PipelineConfig.phase2()
        else:
            config = PipelineConfig.phase1()
        config.debug = debug
        
        # Build page models and calculate global body size
        page_models, pages_text, global_body_size = self._build_engine_page_models(debug=debug)
        
        # Create pipeline and run
        pipeline = CitationPipeline(config)
        entries, debug_bundle = pipeline.run_from_pages(page_models, pages_text, global_body_size)
        
        # Store for GUI access
        self._engine_entries = entries
        self._engine_debug = debug_bundle
        
        return entries, debug_bundle
    
    def _build_engine_page_models(self, debug: bool = False) -> Tuple[List[PageData], List[str], float]:
        """
        Build page models for the new engine.
        
        Returns:
            Tuple of (page_models, pages_text, global_body_size)
        """
        from collections import Counter
        
        page_models = []
        pages_text = []
        all_sizes = []  # For global body size estimation
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                page_width = page.width or 612.0
                page_height = page.height or 792.0
                
                # Collect sizes for global estimation (filter to reasonable body text range)
                if page.chars:
                    for c in page.chars:
                        s = c.get('size', 0)
                        if 5.0 <= s <= 20.0:
                            all_sizes.append(round(s, 1))
                
                # Build page model
                page_data = build_page_data(
                    page.chars,
                    page_num=page_num,
                    page_width=page_width,
                    page_height=page_height,
                )
                page_models.append(page_data)
                pages_text.append(page_data.text)
        
        # Calculate global body size (mode of all sizes)
        if all_sizes:
            counter = Counter(all_sizes)
            global_body_size = counter.most_common(1)[0][0]
        else:
            global_body_size = 10.0
        
        if debug:
            print(f"[ENGINE] Global body size estimated: {global_body_size:.2f}")
            print(f"[ENGINE] Total pages: {len(page_models)}")
            if all_sizes:
                top_sizes = counter.most_common(5)
                print(f"[ENGINE] Top font sizes: {top_sizes}")
        
        return page_models, pages_text, global_body_size
    
    def get_engine_entries(self) -> List[RefEntry]:
        """Get citation entries from the new engine"""
        return getattr(self, '_engine_entries', [])
    
    def get_engine_debug(self) -> Optional[DebugBundle]:
        """Get debug bundle from the new engine"""
        return getattr(self, '_engine_debug', None)