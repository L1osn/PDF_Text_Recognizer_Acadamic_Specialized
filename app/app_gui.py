"""
PDF Text Recognizer - Modern GUI Application
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading
import traceback
from PIL import Image, ImageTk
import pdfplumber
import re
import csv
from typing import Tuple, Optional
from scripts.Pdf_to_text import AcademicPDFRecognizer


class PDFTextRecognizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Text Recognizer Pro")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # --- Modern Flat Theme Colors ---
        self.bg_app = "#fafafa"         # Overall App Background (Light Grey)
        self.bg_card = "#ffffff"        # Card Background (White)
        self.border_color = "#e0e0e0"   # Light Border
        self.primary_color = "#0969da"  # Primary Action Blue
        self.text_color = "#333333"     # Dark Text
        self.text_muted = "#666666"     # Muted Text
        self.sidebar_color = self.bg_app # Sidebar matches App BG
        
        # --- Functional Colors ---
        self.match_color = "#fff8c5"    # Search Highlight
        self.current_match_color = "#bf8700" # Current Search Highlight
        self.font_select_color = "#ddf4ff" # Font Analysis Highlight
        self.accent_color = self.primary_color # Accent Color mapped to Primary
        
        # --- Style Configuration ---
        self.style.configure("TFrame", background=self.bg_app)
        self.style.configure("Sidebar.TFrame", background=self.sidebar_color)
        
        # Card Style (White background + Light Border)
        # Note: bordercolor is not standard ttk, use relief and draw manually if needed
        self.style.configure("Card.TFrame", background=self.bg_card, relief="solid", borderwidth=1)
        
        # Typography
        self.style.configure("TLabel", background=self.bg_app, foreground=self.text_color, font=("Segoe UI", 9))
        self.style.configure("Sidebar.TLabel", background=self.sidebar_color, foreground=self.text_color, font=("Segoe UI", 9))
        self.style.configure("Card.TLabel", background=self.bg_card, foreground=self.text_color, font=("Segoe UI", 9))
        self.style.configure("Header.TLabel", background=self.sidebar_color, foreground=self.text_color, font=("Segoe UI", 12, "bold"))
        self.style.configure("Status.TLabel", background=self.sidebar_color, foreground=self.text_muted, font=("Segoe UI", 8))
        self.style.configure("Section.TLabel", background=self.bg_app, foreground=self.text_muted, font=("Segoe UI", 9, "bold"))

        # Buttons - Secondary (Default)
        self.style.configure("TButton", 
                             background=self.bg_card, 
                             foreground=self.text_color, 
                             borderwidth=1, 
                             relief="solid",
                             padding=6,
                             font=("Segoe UI", 9))
                             
        # --- Screen Scale Detection ---
        try:
            dpi = self.root.winfo_fpixels('1i')
            self.screen_scale = dpi / 72.0
        except:
            self.screen_scale = 1.0 # Default fallback
            
        self.pdf_zoom = 1.0 * self.screen_scale  # Initial zoom adjusted for screen
        self.style.map("TButton", 
                       background=[("active", "#f0f0f0"), ("pressed", "#e5e5e5")])
        
        # Buttons - Primary (Solid Color)
        self.style.configure("Primary.TButton", 
                             background=self.primary_color, 
                             foreground="#ffffff",
                             borderwidth=0,
                             relief="flat",
                             padding=8,
                             font=("Segoe UI", 10, "bold"))
        self.style.map("Primary.TButton", 
                       background=[("active", "#085dc0"), ("pressed", "#0750a4")])

        # Tables / Treeview
        self.style.configure("Treeview", 
                             background="white",
                             fieldbackground="white",
                             foreground=self.text_color,
                             rowheight=28,
                             font=("Segoe UI", 9),
                             borderwidth=0)
        self.style.configure("Treeview.Heading", 
                             font=("Segoe UI", 9, "bold"), 
                             background=self.bg_app, 
                             foreground=self.text_color,
                             relief="flat")
        
        # Tabs
        self.style.configure("TNotebook", background=self.bg_app, borderwidth=0)
        self.style.configure("TNotebook.Tab", 
                             background=self.bg_app, 
                             foreground=self.text_muted, 
                             padding=[16, 8],
                             borderwidth=0,
                             font=("Segoe UI", 10))
        self.style.map("TNotebook.Tab", 
                       background=[("selected", self.bg_card)],
                       foreground=[("selected", self.primary_color)],
                       font=[("selected", ("Segoe UI", 10, "bold"))])

        # Toolbars
        self.style.configure("Toolbar.TFrame", background="#ffffff", relief="flat")
        
        # Tool Buttons (Icon style)
        self.style.configure("Tool.TButton", 
                             background="#ffffff", 
                             foreground=self.text_color,
                             borderwidth=0,
                             relief="flat",
                             padding=[6, 4])
        self.style.map("Tool.TButton", background=[("active", "#f0f0f0")])

        self.style.configure("TCombobox", 
                             fieldbackground="#ffffff", 
                             background="#ffffff", 
                             arrowcolor=self.text_color,
                             relief="solid",
                             padding=5)
        
        # Scrollbars
        self.style.configure("TScrollbar", background="#cccccc", troughcolor="#f5f5f7", borderwidth=0, arrowcolor=self.text_color) 

        # OLD LabelFrames -> Maps to Card Style now, or kept for compatibility
        self.style.configure("TLabelframe", background=self.bg_app, bordercolor=self.border_color, relief="flat")
        self.style.configure("TLabelframe.Label", background=self.bg_app, foreground=self.text_color)
        
        self.recognizer = None
        self.current_text = ""
        self._worker_running = False
        self._job_id = 0  # monotonic counter; stale after() callbacks are discarded
        self._no_spanmap_warned = False  # avoid spamming log/status on clicks before extraction
        
        # Minimal file log (no console needed)
        try:
            self._log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log")
        except Exception:
            self._log_path = "app.log"
        
        # Cached pdfplumber handle (avoid re-opening per render)
        self._pdf_handle = None
        
        # Navigation
        self.match_items = []
        self.current_match_index = -1
        
        # PDF Viewer State (LRU cache: keep max _IMG_CACHE_SIZE pages)
        self.pdf_images = {}
        self._img_lru = []  # page_num order, most recent at end
        self._IMG_CACHE_SIZE = 8
        self.current_page = 1
        self.total_pages = 0
        # self.pdf_zoom already set above (screen_scale aware)
        self.supersample = 2.0
        
        # Drag State (Panning)
        self._drag_data = {"x": 0, "y": 0, "moved": False}
        
        # Mappings & Stats
        self.page_mapping = {}
        self.span_mapping = {}
        self.font_spans = []
        self.font_stats = {} # (name, size) -> count
        self.tree_items = [] # Cache for filtering
        
        # Settings
        self.font_family_var = tk.StringVar(value="Times New Roman")
        self.font_size_var = tk.StringVar(value="12")
        # Render quality: fixed supersample (set in self.supersample)
        
        self._create_ui()
        self._create_context_menu()
    
    def _create_ui(self):
        self.sidebar = ttk.Frame(self.root, style="Sidebar.TFrame", width=300)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        # App Title / Brand
        title_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        title_frame.pack(fill=tk.X, padx=20, pady=(24, 16))
        ttk.Label(title_frame, text="PDF Recognizer", style="Header.TLabel", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(title_frame, text="Pro Edition", style="Status.TLabel").pack(anchor=tk.W)

        # Actions Area (Open PDF)
        action_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        action_frame.pack(fill=tk.X, padx=20)
        
        self.btn_open_pdf = ttk.Button(action_frame, text="Open PDF Document", command=self._browse_file, style="Primary.TButton")
        self.btn_open_pdf.pack(fill=tk.X, pady=(0, 6), ipady=5)
        
        self.lbl_file_status = ttk.Label(action_frame, text="No file selected", style="Status.TLabel")
        self.lbl_file_status.pack(anchor=tk.W, pady=(0, 16))
        
        # --- Card: Extraction ---
        card_extract = ttk.Frame(self.sidebar, style="Card.TFrame", padding=15)
        card_extract.pack(fill=tk.X, padx=16, pady=(0, 12))
        
        ttk.Label(card_extract, text="EXTRACTION", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        
        self.btn_extract_plain = ttk.Button(card_extract, text="Extract Plain Text", command=self._extract_text, state=tk.DISABLED)
        self.btn_extract_plain.pack(fill=tk.X, pady=4)
        
        self.btn_extract_fonts = ttk.Button(card_extract, text="Extract with Fonts", command=self._extract_with_fonts, state=tk.DISABLED)
        self.btn_extract_fonts.pack(fill=tk.X, pady=4)

        self.btn_cancel = ttk.Button(card_extract, text="Cancel", command=self._cancel_task, state=tk.DISABLED)
        self.btn_cancel.pack(fill=tk.X, pady=(10, 0))
        
        # --- Card 3: Configuration ---
        card_config = ttk.Frame(self.sidebar, style="Card.TFrame", padding=15)
        card_config.pack(fill=tk.X, padx=16, pady=(0, 12))
        
        ttk.Label(card_config, text="CONFIGURATION", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        
        # Toggle Switch Row
        switch_frame = ttk.Frame(card_config, style="Card.TFrame") # Match BG
        switch_frame.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(switch_frame, text="Auto Analyze Refs", style="Card.TLabel").pack(side=tk.LEFT)
        
        # Custom Canvas Switch
        self.var_auto_analyze = tk.BooleanVar(value=True)
        self.cv_switch = tk.Canvas(switch_frame, width=44, height=24, bg=self.bg_card, highlightthickness=0)
        self.cv_switch.pack(side=tk.RIGHT)
        self._draw_toggle_switch()
        self.cv_switch.bind("<Button-1>", self._toggle_analyze_switch)
        
        ttk.Label(card_config, text="(Removes bibliography & links in-text citations)", style="Status.TLabel", background=self.bg_card).pack(anchor=tk.W, pady=(0, 12))

        # Ref Mode Combo
        ttk.Label(card_config, text="Removal Sensitivity", style="Card.TLabel").pack(anchor=tk.W, pady=(0, 4))
        self.var_ref_color_mode = tk.StringVar(value="Auto")
        self.combo_ref_mode = ttk.Combobox(card_config, textvariable=self.var_ref_color_mode, 
                                          values=["Auto (Color+Font)", "Force Color", "Off (Scan Only)"], 
                                          state="readonly")
        self.combo_ref_mode.pack(fill=tk.X, pady=(0, 12))
        self.combo_ref_mode.bind("<<ComboboxSelected>>", lambda e: self.root.focus())

        # Export Actions
        self.btn_export_refs = ttk.Button(card_config, text="Export Debug Report", command=self._export_debug_report, state=tk.DISABLED)
        self.btn_export_refs.pack(fill=tk.X)

        # Footer Actions
        footer_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)
        
        ttk.Button(footer_frame, text="Copy Text", command=self._copy_to_clipboard, state=tk.DISABLED).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        ttk.Button(footer_frame, text="Save As...", command=self._save_text, state=tk.DISABLED).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))
        
        # Main Split
        self.main_split = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_split.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # PDF Pane
        self.frame_pdf = ttk.Frame(self.main_split)
        
        ctrl_frame = ttk.Frame(self.frame_pdf, style="Toolbar.TFrame")
        ctrl_frame.pack(fill=tk.X, ipady=4)
        
        # Navigation
        ttk.Button(ctrl_frame, text="‹", width=3, command=self._prev_page, style="Tool.TButton").pack(side=tk.LEFT, padx=1)
        self.lbl_page = ttk.Label(ctrl_frame, text="0 / 0", background="#f6f8fa", font=("Segoe UI", 9))
        self.lbl_page.pack(side=tk.LEFT, padx=8)
        ttk.Button(ctrl_frame, text="›", width=3, command=self._next_page, style="Tool.TButton").pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(ctrl_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y, pady=4)

        # Zoom Controls
        ttk.Button(ctrl_frame, text="−", width=3, command=self._zoom_out, style="Tool.TButton").pack(side=tk.LEFT)
        self.combo_zoom = ttk.Combobox(ctrl_frame, values=["50%", "75%", "100%", "125%", "150%", "200%"], width=6)
        self.combo_zoom.set("100%")
        self.combo_zoom.pack(side=tk.LEFT, padx=(4, 4))
        self.combo_zoom.bind('<<ComboboxSelected>>', self._apply_custom_zoom)
        self.combo_zoom.bind('<Return>', self._apply_custom_zoom)
        ttk.Button(ctrl_frame, text="+", width=3, command=self._zoom_in, style="Tool.TButton").pack(side=tk.LEFT)
        
        # Search Bar (Top Right)
        search_frame = ttk.Frame(self.frame_pdf, style="Toolbar.TFrame")
        search_frame.pack(fill=tk.X, pady=4, padx=4)
        
        # PDF Canvas Background (Dark Reader Style)
        self.canvas_pdf = tk.Canvas(self.frame_pdf, bg="#525659", highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(self.frame_pdf, orient="vertical", command=self.canvas_pdf.yview)
        self.h_scroll = ttk.Scrollbar(self.frame_pdf, orient="horizontal", command=self.canvas_pdf.xview)
        self.canvas_pdf.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas_pdf.pack(fill=tk.BOTH, expand=True)
        
        # New bindings for drag scrolling
        self.canvas_pdf.bind("<ButtonPress-1>", self._on_pdf_press)
        self.canvas_pdf.bind("<B1-Motion>", self._on_pdf_drag)
        self.canvas_pdf.bind("<ButtonRelease-1>", self._on_pdf_release)
        self.canvas_pdf.bind("<Button-3>", lambda e: self._show_context_menu(e, 'pdf')) # Right Click
        
        # Mouse Wheel - Scroll (default) / Zoom (Ctrl)
        self.canvas_pdf.bind("<Enter>", lambda e: self.canvas_pdf.focus_set()) 
        
        self.canvas_pdf.bind("<MouseWheel>", self._on_mouse_scroll)
        self.canvas_pdf.bind("<Control-MouseWheel>", self._on_mouse_zoom)
        
        # Linux
        self.canvas_pdf.bind("<Button-4>", self._on_mouse_scroll)
        self.canvas_pdf.bind("<Button-5>", self._on_mouse_scroll)
        self.canvas_pdf.bind("<Control-Button-4>", self._on_mouse_zoom)
        self.canvas_pdf.bind("<Control-Button-5>", self._on_mouse_zoom) 
        
        # Text Pane
        self.frame_text = ttk.Frame(self.main_split)
        self.notebook = ttk.Notebook(self.frame_text)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # -- Tab 1: Text Content --
        self.tab_text = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_text, text="Text Content")
        
        tb = ttk.Frame(self.tab_text, style="Toolbar.TFrame")
        tb.pack(fill=tk.X, pady=(0, 1), ipady=4)
        
        self.combo_font = ttk.Combobox(tb, textvariable=self.font_family_var, values=["Times New Roman", "Consolas", "Segoe UI"], width=15)
        self.combo_font.pack(side=tk.LEFT, padx=(8, 0))
        self.combo_font.bind("<<ComboboxSelected>>", self._update_font)
        
        self.combo_size = ttk.Combobox(tb, textvariable=self.font_size_var, values=["10", "12", "14", "18"], width=5)
        self.combo_size.pack(side=tk.LEFT, padx=5)
        self.combo_size.bind("<<ComboboxSelected>>", self._update_font)
        
        self.search_entry = ttk.Entry(tb, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", lambda e: self._search_text())
        ttk.Button(tb, text="Search", command=self._search_text, style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        
        ttk.Button(tb, text="∧", width=3, command=self._prev_match, style="Tool.TButton").pack(side=tk.LEFT, padx=(5,1))
        ttk.Button(tb, text="∨", width=3, command=self._next_match, style="Tool.TButton").pack(side=tk.LEFT, padx=1)
        ttk.Button(tb, text="×", width=3, command=self._clear_selection, style="Tool.TButton").pack(side=tk.LEFT, padx=(5,1))
        
        self.lbl_search_status = ttk.Label(tb, text="", background="#f6f8fa")
        self.lbl_search_status.pack(side=tk.LEFT, padx=5)
        
        self.txt_output = scrolledtext.ScrolledText(self.tab_text, 
                                                    font=("Consolas", 11), 
                                                    relief="flat",
                                                    padx=10, pady=10)
        self.txt_output.pack(fill=tk.BOTH, expand=True)
        self.txt_output.bind("<ButtonRelease-1>", self._on_text_click)
        self.txt_output.bind("<Button-3>", self._on_right_click)
        
        self.txt_output.tag_config("match", background=self.match_color, foreground="black")
        self.txt_output.tag_config("current_match", background=self.current_match_color, foreground="white")
        self.txt_output.tag_config("citation", background="#e0c0e0")
        self.txt_output.tag_config("pdf_selection", background="#ddf4ff")
        self.txt_output.tag_config("font_selection", background=self.font_select_color)
        
        # -- Tab 2: Fonts --
        self.tab_fonts = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_fonts, text="Fonts")
        
        font_tb = ttk.Frame(self.tab_fonts, style="Toolbar.TFrame")
        font_tb.pack(fill=tk.X, padx=0, pady=0, ipady=4)
        
        ttk.Label(font_tb, text="Font:", background="#f6f8fa").pack(side=tk.LEFT, padx=(8, 4))
        self.combo_filter_name = ttk.Combobox(font_tb, state="readonly", width=30)
        self.combo_filter_name.pack(side=tk.LEFT, padx=0)
        self.combo_filter_name.bind("<<ComboboxSelected>>", self._filter_fonts)
        self.combo_filter_name.set("All Fonts")
        
        ttk.Label(font_tb, text="Size:", background="#f6f8fa").pack(side=tk.LEFT, padx=(10, 4))
        self.combo_filter_size = ttk.Combobox(font_tb, state="readonly", width=10)
        self.combo_filter_size.pack(side=tk.LEFT, padx=5)
        self.combo_filter_size.bind("<<ComboboxSelected>>", self._filter_fonts)
        self.combo_filter_size.set("All Sizes")
        
        self.tree_fonts = ttk.Treeview(self.tab_fonts, columns=("font", "size", "count"), show="headings")
        self.tree_fonts.heading("font", text="Font Name")
        self.tree_fonts.heading("size", text="Size")
        self.tree_fonts.heading("count", text="Occurrences")
        self.tree_fonts.column("font", width=200)
        self.tree_fonts.column("size", width=50)
        self.tree_fonts.column("count", width=80)
        
        scrollbar_fonts = ttk.Scrollbar(self.tab_fonts, orient="vertical", command=self.tree_fonts.yview)
        self.tree_fonts.configure(yscrollcommand=scrollbar_fonts.set)
        
        scrollbar_fonts.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_fonts.pack(fill=tk.BOTH, expand=True)
        
        self.tree_fonts.bind("<Double-1>", self._on_font_tree_double_click)
        
        # -- Tab 4: Refs --
        self.tab_refs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_refs, text="Refs")
        
        # Status Label
        self.lbl_ref_status = ttk.Label(self.tab_refs, text="Click 'Extract with Fonts' then enable 'Auto Analyze Refs'", foreground="gray")
        self.lbl_ref_status.pack(fill=tk.X, padx=5, pady=5)
        
        # Filters
        ref_toolbar = ttk.Frame(self.tab_refs, style="Toolbar.TFrame")
        ref_toolbar.pack(fill=tk.X, padx=5, pady=0)
        
        self.var_hide_no_detail = tk.BooleanVar(value=True)
        self.chk_hide_detail = ttk.Checkbutton(ref_toolbar, text="Hide entries with No Detail", variable=self.var_hide_no_detail, command=lambda: self._analyze_citations(verbose=False))
        self.chk_hide_detail.pack(side=tk.LEFT)
        
        columns = ("id", "full_text", "page")
        self.tree_refs = ttk.Treeview(self.tab_refs, columns=columns, show="headings")
        self.tree_refs.heading("id", text="Ref")
        self.tree_refs.heading("full_text", text="Reference Details")
        self.tree_refs.heading("page", text="Pg")
        
        self.tree_refs.column("id", width=40)
        self.tree_refs.column("full_text", width=350)
        self.tree_refs.column("page", width=40)
        
        ref_scroll = ttk.Scrollbar(self.tab_refs, orient="vertical", command=self.tree_refs.yview)
        self.tree_refs.configure(yscrollcommand=ref_scroll.set)
        
        ref_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_refs.pack(fill=tk.BOTH, expand=True)
        self.tree_refs.bind("<Double-1>", self._on_ref_double_click)
        self.tree_refs.bind("<Button-3>", lambda e: self._show_context_menu(e, 'ref')) # Right Click
        
        # Details Panel for Ref
        self.txt_ref_detail = tk.Text(self.tab_refs, height=5, wrap=tk.WORD, bg="#f0f0f0")
        self.txt_ref_detail.pack(fill=tk.X, side=tk.BOTTOM)
        self.tree_refs.bind("<<TreeviewSelect>>", self._on_ref_select)

        self.main_split.add(self.frame_pdf, weight=1)
        self.main_split.add(self.frame_text, weight=1)
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var).pack(fill=tk.X, side=tk.BOTTOM)
        
        self._create_context_menu()

    def _create_context_menu(self):
        # Global Right Click Menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu_data = {} # Store temp data for the click (e.g. x,y)

    def _show_context_menu(self, event, context_type="general"):
        """
        Generic Context Menu Handler
        context_type: 'pdf', 'text', 'ref', 'general'
        """
        self.context_menu.delete(0, tk.END)
        
        # 1. Context Specific Options
        # 1. Context Specific Options
        if context_type == 'text':
            self.context_menu.add_command(label="Copy", command=self._copy_selection)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Show in PDF View", command=lambda: self._sync_from_text_to_pdf(event))
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Select All with this Font", command=self._select_by_font)
            
        elif context_type == 'pdf':
            self.context_menu.add_command(label="Show in Text View", command=lambda: self._sync_from_pdf_to_text(event))
            
        elif context_type == 'ref':
            self.context_menu.add_command(label="Show in PDF View", command=self._sync_from_ref_to_pdf)
            self.context_menu.add_command(label="Show in Text View", command=self._sync_from_ref_to_text)
        
        self.context_menu.tk_popup(event.x_root, event.y_root)
        self.click_font_info = None # Context menu might set this


    def _close_pdf_handle(self):
        """Close the cached pdfplumber handle."""
        if self._pdf_handle is not None:
            try:
                self._pdf_handle.close()
            except Exception:
                pass
            self._pdf_handle = None

    def _report_bg_error(self, kind: str, error: Exception, tb_str: str):
        """Unified background error reporting (main thread only)."""
        short = str(error) if error is not None else "Unknown error"
        self._log(f"ERROR kind={kind} msg={short}\n{tb_str or ''}")
        self.status_var.set(f"{kind} failed: {short}")

    def _start_bg_task(self, kind: str, job_id: int, compute_fn, done_fn):
        """
        Run compute_fn() on a daemon thread.
        All UI updates must happen in done_fn (called on main thread).
        Any exception is caught and routed as (None, error, traceback) into done_fn.
        """
        def worker():
            try:
                payload = compute_fn()
                self.root.after(0, lambda: done_fn(payload, None, "", job_id))
            except Exception as e:
                tb = traceback.format_exc()
                self.root.after(0, lambda: done_fn(None, e, tb, job_id))
        threading.Thread(target=worker, daemon=True).start()

    def _get_pdf_handle(self):
        """Get (or open) the cached pdfplumber handle."""
        if self._pdf_handle is None and self.recognizer:
            self._pdf_handle = pdfplumber.open(self.recognizer.pdf_path)
        return self._pdf_handle

    def _log(self, msg: str):
        """Append one timestamped line to app.log (no console needed)."""
        import datetime
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")
        except Exception:
            pass

    def _browse_file(self):
        if self._worker_running:
            self.status_var.set("Cannot switch files while a task is running.")
            return
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            # Invalidate any in-flight after() callbacks from previous file
            self._job_id += 1
            self._no_spanmap_warned = False
            
            # Close previous handle if switching files
            self._close_pdf_handle()
            
            try:
                self.recognizer = AcademicPDFRecognizer(path)
                self.lbl_file_status.config(text=os.path.basename(path))
                self.pdf_images = {}
                self._img_lru.clear()
                
                pdf = self._get_pdf_handle()
                self.total_pages = len(pdf.pages)
                self._log(f"OPEN path={path} pages={self.total_pages}")
                self._show_pdf_page(1)
                self.btn_extract_plain.config(state=tk.NORMAL)
                self.btn_extract_fonts.config(state=tk.NORMAL)
            except Exception as e:
                self._close_pdf_handle()
                self.status_var.set(f"Failed to open PDF: {e}")
                self._log(f"OPEN_FAIL path={path} err={e}")

    def _on_mouse_scroll(self, event):
        # Pure Scroll Handler
        # On Windows: delta 120 (up) / -120 (down)
        # yview_scroll: +n (down) / -n (up)
        # So we invert delta.
        if hasattr(event, 'delta') and event.delta != 0:
            # Speed: 3 units per notch?
            count = -int(event.delta / 40) 
            self.canvas_pdf.yview_scroll(count, "units")
        # Linux Buttons
        elif event.num == 5:
            self.canvas_pdf.yview_scroll(1, "units")
        elif event.num == 4:
            self.canvas_pdf.yview_scroll(-1, "units")
            
    def _on_mouse_zoom(self, event):
        # pure Zoom Handler (triggered by Ctrl+Wheel)
        if event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            factor = 0.9
        else:
            factor = 1.1

        new_zoom = self.pdf_zoom * factor
        if 0.5 < new_zoom < 5.0:
            self.pdf_zoom = new_zoom
            try:
                x = self.canvas_pdf.canvasx(event.x)
                y = self.canvas_pdf.canvasy(event.y)
            except: pass
            self._update_zoom()
        return "break" # Prevent default

    # Removed _on_wheel_zoom to avoid confusion

    def _copy_selection(self):
        try:
            if self.txt_output.tag_ranges(tk.SEL):
                text = self.txt_output.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
        except: pass

    # ---- Drag Panning Logic ----
    def _on_pdf_press(self, event):
        self.canvas_pdf.scan_mark(event.x, event.y)
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._drag_data["moved"] = False

    def _on_pdf_drag(self, event):
        self.canvas_pdf.scan_dragto(event.x, event.y, gain=1)
        if abs(event.x - self._drag_data["x"]) > 5 or abs(event.y - self._drag_data["y"]) > 5:
            self._drag_data["moved"] = True

    def _on_pdf_release(self, event):
        if not self._drag_data["moved"]:
            self._on_pdf_click(event) 
            
    def _on_pdf_click(self, event):
        if not self.span_mapping:
            if not self._no_spanmap_warned:
                self._no_spanmap_warned = True
                self.status_var.set("No span mapping. Please run 'Extract with Fonts' first.")
                self._log("CLICK_NO_SPANMAP (user clicked PDF without spans)")
            return
        try:
            # Single page mode: canvas coords map directly to image coords
            canvas_x = self.canvas_pdf.canvasx(event.x)
            canvas_y = self.canvas_pdf.canvasy(event.y)
            
            # pdf_points = canvas_pixels / pdf_zoom
            pdf_x = canvas_x / self.pdf_zoom
            pdf_y = canvas_y / self.pdf_zoom
            
            page_spans = self.span_mapping.get(self.current_page, [])
            found = False
            self.txt_output.tag_remove("pdf_selection", "1.0", tk.END)
            for span_data in page_spans:
                x0, top, x1, bottom = span_data["bbox"]
                if x0 <= pdf_x <= x1 and top <= pdf_y <= bottom:
                    start = span_data["start"]
                    end = span_data["end"]
                    self.txt_output.tag_add("pdf_selection", start, end)
                    self.txt_output.see(start)
                    found = True
                    break
            if found: 
                self.status_var.set("Match found")
            elif page_spans:
                # Log nearest span for debugging coordinate alignment
                nearest = min(page_spans, key=lambda s: (
                    max(s["bbox"][0] - pdf_x, 0, pdf_x - s["bbox"][2]) ** 2 +
                    max(s["bbox"][1] - pdf_y, 0, pdf_y - s["bbox"][3]) ** 2))
                nb = nearest["bbox"]
                self._log(f"CLICK_MISS page={self.current_page} "
                          f"pdf=({pdf_x:.1f},{pdf_y:.1f}) "
                          f"nearest_bbox=({nb[0]:.1f},{nb[1]:.1f},{nb[2]:.1f},{nb[3]:.1f})")
        except Exception as e:
            self.status_var.set(f"Click error: {e}")

    def _zoom_in(self):
        self.pdf_zoom += 0.1 # Finer step
        self._update_zoom()
    def _zoom_out(self):
        if self.pdf_zoom > 0.1:
            self.pdf_zoom -= 0.1
            self._update_zoom()
            
    def _apply_custom_zoom(self, event=None):
        try:
            val_str = self.combo_zoom.get().strip().replace('%', '')
            val = float(val_str)
            if val < 10: val = 10
            if val > 500: val = 500
            self.pdf_zoom = val / 100.0
            self._update_zoom()
            # Force focus out to prevent stuck interaction
            self.root.focus()
        except: 
            self._update_zoom() # Revert if invalid

    def _update_zoom(self):
        self.combo_zoom.set(f"{int(self.pdf_zoom * 100)}%")
        self.pdf_images = {}
        self._img_lru.clear()
        self.canvas_pdf.delete("all")
        self._show_pdf_page(self.current_page)

    def _show_pdf_page(self, page_num):
        if not self.recognizer or page_num < 1 or page_num > self.total_pages: return
        try:
            if page_num not in self.pdf_images:
                pdf = self._get_pdf_handle()
                if pdf is None: return
                page = pdf.pages[page_num - 1]
                
                total_scale = self.pdf_zoom * self.supersample
                im_high = page.to_image(resolution=72 * total_scale).original
                target_w = int(im_high.width / self.supersample)
                target_h = int(im_high.height / self.supersample)
                im = im_high.resize((target_w, target_h), Image.Resampling.LANCZOS)
                self.pdf_images[page_num] = ImageTk.PhotoImage(im)
            
            # LRU: move to end, evict oldest if over limit
            if page_num in self._img_lru:
                self._img_lru.remove(page_num)
            self._img_lru.append(page_num)
            while len(self._img_lru) > self._IMG_CACHE_SIZE:
                old = self._img_lru.pop(0)
                self.pdf_images.pop(old, None)
            
            self.canvas_pdf.delete("all")
            self.canvas_pdf.create_image(0, 0, image=self.pdf_images[page_num], anchor=tk.NW)
            self.canvas_pdf.config(scrollregion=self.canvas_pdf.bbox(tk.ALL))
            self.current_page = page_num
            self.lbl_page.config(text=f"Page {page_num}/{self.total_pages}")
        except Exception as e:
            self.status_var.set(f"Page render error: {e}")

    def _prev_page(self): 
        if self.current_page > 1: 
            self._show_pdf_page(self.current_page - 1)
    def _next_page(self): 
        if self.current_page < self.total_pages: 
            self._show_pdf_page(self.current_page + 1)
            
    def _extract_text(self):
        if not self.recognizer: return
        self.txt_output.delete(1.0, tk.END)
        self.match_items = []
        
        # Map GUI options to API
        mode_str = self.var_ref_color_mode.get()
        color_arg = 'auto'
        remove_refs = self.var_auto_analyze.get()
        
        if "Force" in mode_str: color_arg = 'force'
        if "Off" in mode_str: color_arg = 'off'
            
        full_text = self.recognizer.extract_text(detect_headers_by_color=color_arg, remove_references=remove_refs)
        
        self.txt_output.insert(1.0, full_text)
        self.span_mapping = {}
        self.page_mapping = {}
        self.font_spans = []
        self.font_stats = {}
        
        # Auto-update rich color status
        if hasattr(self.recognizer, 'is_color_rich') and self.recognizer.is_color_rich:
             self.status_var.set("Rich Color Document Detected")
        else:
             self.status_var.set("Ready")

        self._refresh_font_tree()
        
        if self.var_auto_analyze.get():
            self._analyze_citations()

    def _set_busy(self, busy: bool):
        """Enable/disable action buttons during background work."""
        state = tk.DISABLED if busy else tk.NORMAL
        for btn in (getattr(self, "btn_open_pdf", None), self.btn_extract_plain, self.btn_extract_fonts, getattr(self, "btn_cancel", None)):
            try:
                if btn is not None:
                    btn.config(state=state)
            except Exception:
                pass
        if hasattr(self, "btn_cancel") and self.btn_cancel is not None:
            try:
                self.btn_cancel.config(state=tk.NORMAL if busy else tk.DISABLED)
            except Exception:
                pass
        self._worker_running = busy

    def _cancel_task(self):
        """Soft-cancel: invalidate current job_id; UI becomes interactive immediately."""
        if not self._worker_running:
            return
        self._job_id += 1
        self._set_busy(False)
        self.status_var.set("Cancelled.")
        self._log("CANCEL job_id advanced; pending callbacks will be discarded")

    def _extract_with_fonts(self):
        if not self.recognizer: return
        if self._worker_running:
            self.status_var.set("A task is already running...")
            return
        
        # Reset GUI & Maps (main thread)
        self.txt_output.delete(1.0, tk.END)
        self.span_mapping = {}
        self.page_mapping = {}
        self.font_spans = []
        self.font_stats = {}
        self.match_items = []
        self.recognizer.text_spans = []
        self._no_spanmap_warned = False
        
        self._job_id += 1
        my_job = self._job_id
        
        self._set_busy(True)
        self.status_var.set("Extracting (background)...")
        total = self.total_pages
        
        def compute():
            """Collect all page spans in background thread — no Tk widget access."""
            all_pages = []
            count = 0
            for page_num, spans in self.recognizer.iter_extract_text_with_fonts():
                if my_job != self._job_id:
                    return None  # cancelled / superseded
                all_pages.append((page_num, spans))
                count += 1
                self.root.after(0, lambda c=count: self.status_var.set(f"Extracting page {c}/{total}..."))
            return all_pages

        self._start_bg_task("EXTRACT", my_job, compute, self._extract_done)
    
    def _extract_done(self, all_pages, error, tb_str="", job_id=None):
        """Process extraction results on main thread."""
        # Discard stale callback (user switched file / re-triggered)
        if job_id is not None and job_id != self._job_id:
            return
        self._set_busy(False)
        
        if error:
            self._report_bg_error("EXTRACT", error, tb_str)
            try:
                messagebox.showerror("Error", f"Extraction failed:\n{error}")
            except Exception:
                pass
            return
        if all_pages is None:
            # Cancelled/superseded. Nothing to do.
            return
        
        # Insert all data into widgets (main thread only)
        for page_num, spans in all_pages:
            self.recognizer.text_spans.extend(spans)
            
            for span in spans:
                text_content = span.text.replace('\r', '')
                if text_content == "":
                    continue

                if text_content == "\n":
                    self.txt_output.insert(tk.END, "\n")
                    continue

                start_idx = self.txt_output.index(tk.END)
                self.txt_output.insert(tk.END, text_content)
                end_idx = self.txt_output.index(tk.END)

                if span.page not in self.span_mapping:
                    self.span_mapping[span.page] = []
                self.span_mapping[span.page].append({
                    "bbox": span.bbox,
                    "start": start_idx,
                    "end": end_idx
                })

                self.font_spans.append({
                    "text": span.text,
                    "font": span.font_name,
                    "size": span.font_size,
                    "is_bold": getattr(span, 'is_bold', False),
                    "is_italic": getattr(span, 'is_italic', False),
                    "start": start_idx,
                    "end": end_idx
                })

                s_line = int(start_idx.split('.')[0])
                e_line = int(end_idx.split('.')[0])
                for l in range(s_line, e_line + 1):
                    self.page_mapping[l] = span.page

                key = (span.font_name, round(span.font_size, 1))
                self.font_stats[key] = self.font_stats.get(key, 0) + 1

        self.status_var.set(f"Extraction complete. {len(self.font_spans)} text segments found.")
        self._log(f"EXTRACT spans={len(self.font_spans)} pages={len(all_pages)}")
        self.recognizer.extracted_text = self.txt_output.get("1.0", tk.END)
        self._refresh_font_tree()
        
        if self.var_auto_analyze.get():
            self._analyze_citations()

    def _on_analyze_toggle(self):
        if self.var_auto_analyze.get():
            self._analyze_citations()

    def _analyze_citations(self, verbose=False):
        """
        Citation analysis using the new dual-channel engine.
        Heavy engine work runs in a background thread.
        """
        if self._worker_running:
            self.status_var.set("A task is already running...")
            return

        # Make it visible even without console
        try:
            base_title = self.root.title().split(" | ")[0]
            self.root.title(f"{base_title} | NEW_ENGINE")
        except Exception:
            pass

        # Ensure we have extracted text
        if not hasattr(self.recognizer, 'extracted_text') or not self.recognizer.extracted_text:
            if verbose or self.var_auto_analyze.get(): 
                self.status_var.set("Extracting text for citation analysis...")
                self.root.update()
                self.recognizer.extract_text_with_fonts()
        
        # Clear UI
        self.tree_refs.delete(*self.tree_refs.get_children())
        self.citation_map = {}
        
        self._job_id += 1
        my_job = self._job_id
        
        # Run the engine in background thread
        self._set_busy(True)
        self.status_var.set("Running citation engine (background)...")
        
        def compute():
            """Run citation engine — no Tk widget access."""
            if my_job != self._job_id:
                return None
            entries, debug_bundle = self.recognizer.run_citation_engine(
                enable_superscript=True,
                debug=True
            )
            return (entries, debug_bundle)

        self._start_bg_task("CITE", my_job, compute, self._analyze_done)
    
    def _analyze_done(self, payload, error, tb_str="", job_id=None):
        """Populate UI with citation results (main thread)."""
        # Discard stale callback (user switched file / re-triggered)
        if job_id is not None and job_id != self._job_id:
            return
        self._set_busy(False)
        
        if error:
            self._report_bg_error("CITE", error, tb_str)
            try:
                self.lbl_ref_status.config(text=f"Engine error: {error}")
            except Exception:
                pass
            return

        if payload is None:
            # Cancelled/superseded. Nothing to do.
            return

        entries, debug_bundle = payload
        
        # Store debug_bundle for export
        self._last_debug_bundle = debug_bundle
        
        # Display entries in tree with clean output contract
        matches_found = 0
        
        for entry in entries:
            # --- HARD ASSERTS: only new engine contract allowed ---
            if not isinstance(getattr(entry, "ref_id", None), int):
                raise RuntimeError(f"[CITE] Illegal entry.ref_id type: {type(getattr(entry,'ref_id',None))} -> {getattr(entry,'ref_id',None)}")
            if not isinstance(getattr(entry, "occurrences", None), list):
                raise RuntimeError(f"[CITE] Illegal entry.occurrences type: {type(getattr(entry,'occurrences',None))}")

            bib_detail = entry.bib_detail if entry.bib_detail else "No detail found."
            if isinstance(bib_detail, str) and ("Font:" in bib_detail or "Size:" in bib_detail):
                raise RuntimeError(f"[CITE] Illegal Reference Details (legacy meta leaked): {bib_detail[:200]}")
            
            if self.var_hide_no_detail.get() and bib_detail == "No detail found.":
                continue
            
            first_page = entry.first_page
            first_bbox = entry.first_bbox
            
            display_id = f"[{entry.ref_id}]"
            if entry.count > 1:
                display_id += f" (×{entry.count})"
            
            item_id = self.tree_refs.insert("", tk.END, values=(
                display_id,
                bib_detail[:100] + "..." if len(bib_detail) > 100 else bib_detail,
                first_page
            ))
            
            tk_pos, match_len = self._find_citation_in_text(str(entry.ref_id))
            if tk_pos is None:
                tk_pos = "1.0"
                match_len = len(str(entry.ref_id))
            self.citation_map[item_id] = {
                'ref_id': entry.ref_id,
                'start': tk_pos,
                'end': f"{tk_pos}+{match_len}c",
                'bib_detail': bib_detail,
                'occurrences': entry.occurrences,
                'first_bbox': first_bbox,
                'first_page': first_page,
                'source': entry.source_str,
                'count': entry.count,
                'confidence': entry.confidence,
            }
            
            matches_found += 1
        
        # Build compact status line
        pages_list = sorted(debug_bundle.pages_in_entries)
        if pages_list:
            pages_str = f"{len(pages_list)}({min(pages_list)}-{max(pages_list)})"
        else:
            pages_str = "0"
        
        bib_hard_int = 1 if debug_bundle.bib_hard_constraint_used else 0
        
        status_msg = (
            f"NEW_ENGINE | g={debug_bundle.global_body_size:.1f} | "
            f"bib={debug_bundle.bib_ids_count} | bibHard={bib_hard_int} | "
            f"sup={debug_bundle.superscript_candidates_count} | "
            f"occ={debug_bundle.total_occurrences} | pages={pages_str}"
        )
        
        self.status_var.set(status_msg)
        self.lbl_ref_status.config(text=status_msg, foreground=self.accent_color)
        self._log(f"CITE entries={matches_found} occ={debug_bundle.total_occurrences} "
                  f"bib={debug_bundle.bib_ids_count} sup={debug_bundle.superscript_candidates_count} "
                  f"bracket={debug_bundle.bracket_candidates_count}")
        
        if matches_found > 0:
            self.btn_export_refs.config(state=tk.NORMAL)
        else:
            self.btn_export_refs.config(state=tk.DISABLED)
    
    def _find_citation_in_text(self, ref_key: str) -> Tuple[Optional[str], int]:
        """
        Find citation marker position in text output.
        
        Returns:
            Tuple of (position, matched_length) or (None, 0) if not found
        """
        patterns = [f"[{ref_key}]", ref_key, f"({ref_key})"]
        for pattern in patterns:
            pos = self.txt_output.search(pattern, "1.0", stopindex=tk.END)
            if pos:
                return pos, len(pattern)
        return None, 0

    def _on_ref_select(self, event):
        item_id = self.tree_refs.focus()
        if item_id and item_id in self.citation_map:
            data = self.citation_map[item_id]
            
            # New dict format
            if isinstance(data, dict):
                bib_detail = data.get('bib_detail', 'N/A')
                occurrences = data.get('occurrences', [])
                ref_id = data.get('ref_id', '?')
                
                # Build context from occurrences
                occ_text = f"Found {len(occurrences)} occurrence(s):\n"
                for i, occ in enumerate(occurrences[:10]):  # Show first 10
                    anchor = getattr(occ, "anchor_left", "") or ""
                    occ_text += f"  {i+1}. Page {occ.page}: ...{anchor[-60:]}...\n"
                if len(occurrences) > 10:
                    occ_text += f"  ... and {len(occurrences) - 10} more\n"
                
                self.txt_ref_detail.delete("1.0", tk.END)
                self.txt_ref_detail.insert("1.0", f"REF [{ref_id}]\n\n{occ_text}\n\nBIBLIOGRAPHY:\n{bib_detail}")
            else:
                raise RuntimeError("[CITE] Legacy ref data leaked into citation_map (should be dict from new engine).")

    def _on_ref_double_click(self, event):
        item_id = self.tree_refs.focus()
        if item_id and item_id in self.citation_map:
            data = self.citation_map[item_id]
            
            # New dict format only (from new engine)
            if isinstance(data, dict):
                start = data.get('start', '1.0')
                target_bbox = data.get('first_bbox')
                target_page = data.get('first_page')
                ref_id = data.get('ref_id', 0)
                end = data.get('end', f"{start}+5c")  # Use stored end position
                
                # Highlight in text
                self.txt_output.tag_remove("citation", "1.0", tk.END)
                self.txt_output.tag_add("citation", start, end)
                self.txt_output.see(start)
                
            else:
                raise RuntimeError("[CITE] Legacy ref data leaked into citation_map (should be dict from new engine).")
            
            # --- Auto-Locate in PDF ---
            if not target_bbox:
                # Try to find the span corresponding to this text pos
                for page, spans in self.span_mapping.items():
                    for span_data in spans:
                        if self.txt_output.compare(start, ">=", span_data["start"]) and \
                           self.txt_output.compare(start, "<", span_data["end"]):
                            target_bbox = span_data["bbox"]
                            target_page = page
                            break
                    if target_bbox: break
            
            if target_page and target_bbox:
                self._show_pdf_page(target_page)
                
                # Draw highlight on canvas (consistent scale: pdf_zoom)
                if target_page in self.pdf_images:
                    scale = self.pdf_zoom  # PDF points * zoom = display pixels
                    x0, top, x1, bottom = target_bbox
                    
                    c_x0 = x0 * scale
                    c_top = top * scale
                    c_x1 = x1 * scale
                    c_bottom = bottom * scale
                    
                    self.canvas_pdf.create_rectangle(c_x0, c_top, c_x1, c_bottom, outline="red", width=3, tags="ref_highlight")
                    self.status_var.set(f"Located on Page {target_page}")

    def _export_debug_report(self):
        """Export a complete debug report as TXT file"""
        import datetime
        
        # Let user choose save location
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=f"citation_debug_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not filename:
            return
        
        try:
            report_lines = []
            report_lines.append("=" * 70)
            report_lines.append("PDF CITATION EXTRACTION - DEBUG REPORT")
            report_lines.append("=" * 70)
            report_lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"PDF File: {self.recognizer.pdf_path if self.recognizer else 'N/A'}")
            report_lines.append("")
            
            # Section 1: Engine Statistics
            report_lines.append("-" * 70)
            report_lines.append("1. ENGINE STATISTICS")
            report_lines.append("-" * 70)
            
            debug_bundle = self.recognizer.get_engine_debug() if self.recognizer else None
            if debug_bundle:
                report_lines.append(f"  Bibliography IDs Count: {debug_bundle.bib_ids_count}")
                report_lines.append(f"  Bibliography Map Count: {debug_bundle.bib_map_count}")
                report_lines.append(f"  Bracket Candidates Count: {debug_bundle.bracket_candidates_count}")
                report_lines.append(f"  Superscript Candidates Count: {debug_bundle.superscript_candidates_count}")
                report_lines.append(f"  Final Entries Count: {debug_bundle.entries_count}")
                report_lines.append(f"  Total Occurrences: {debug_bundle.total_occurrences}")
                
                if debug_bundle.bib_ids_sample:
                    report_lines.append(f"  Bib IDs Sample: {debug_bundle.bib_ids_sample[:20]}")
                
                # NEW_ENGINE EXTRA section
                report_lines.append("")
                report_lines.append("  --- NEW_ENGINE EXTRA ---")
                report_lines.append(f"  global_body_size: {debug_bundle.global_body_size:.2f}")
                report_lines.append(f"  bib_hard_constraint_used: {debug_bundle.bib_hard_constraint_used}")
                report_lines.append(f"  pages_with_sup_candidates: {debug_bundle.pages_with_sup_candidates}")
                report_lines.append(f"  pages_in_entries: {sorted(debug_bundle.pages_in_entries)}")
                
                # Superscript per-page stats table
                if debug_bundle.sup_per_page_stats:
                    report_lines.append("")
                    report_lines.append("  --- SUPERSCRIPT PER-PAGE STATS ---")
                    for stat_line in debug_bundle.sup_per_page_stats:
                        report_lines.append(f"  {stat_line}")
            else:
                report_lines.append("  [Engine debug info not available]")
            report_lines.append("")
            
            # Section 2: Font Statistics
            report_lines.append("-" * 70)
            report_lines.append("2. FONT STATISTICS")
            report_lines.append("-" * 70)
            
            if self.font_stats:
                sorted_fonts = sorted(self.font_stats.items(), key=lambda x: x[1], reverse=True)
                report_lines.append(f"  Total unique font/size combinations: {len(sorted_fonts)}")
                report_lines.append("  Top 20 fonts by occurrence:")
                for i, ((font, size), count) in enumerate(sorted_fonts[:20], 1):
                    report_lines.append(f"    {i:2}. {font} @ {size}pt: {count} chars")
            else:
                report_lines.append("  [No font data available]")
            report_lines.append("")
            
            # Section 3: Citation Entries
            report_lines.append("-" * 70)
            report_lines.append("3. CITATION ENTRIES")
            report_lines.append("-" * 70)
            
            entries = self.recognizer.get_engine_entries() if self.recognizer else []
            report_lines.append(f"  Total entries: {len(entries)}")
            report_lines.append("")
            
            for entry in entries:
                report_lines.append(f"  [{entry.ref_id}]")
                report_lines.append(f"    Count: {entry.count}")
                report_lines.append(f"    Source: {entry.source_str}")
                report_lines.append(f"    Confidence: {entry.confidence:.2f}")
                report_lines.append(f"    First Page: {entry.first_page}")
                report_lines.append(f"    Bib Detail: {entry.bib_detail[:100] + '...' if entry.bib_detail and len(entry.bib_detail) > 100 else entry.bib_detail or 'None'}")
                
                # List occurrences
                if entry.occurrences:
                    report_lines.append(f"    Occurrences ({len(entry.occurrences)}):")
                    for j, occ in enumerate(entry.occurrences[:10], 1):
                        report_lines.append(f"      {j}. Page {occ.page}, Line {occ.line_id}, Source {occ.source}")
                    if len(entry.occurrences) > 10:
                        report_lines.append(f"      ... and {len(entry.occurrences) - 10} more")
                report_lines.append("")
            
            # Section 3.5: Detected Ref IDs Summary (compact)
            report_lines.append("-" * 70)
            report_lines.append("3.5. DETECTED REF IDS SUMMARY")
            report_lines.append("-" * 70)
            if entries:
                ref_ids_list = [e.ref_id for e in entries]
                report_lines.append(f"  Ref IDs: {ref_ids_list}")
                report_lines.append("")
                report_lines.append("  Quick Table:")
                report_lines.append(f"  {'RefID':<8} {'Count':<8} {'Source':<20} {'Conf':<8} {'1stPage':<8}")
                report_lines.append("  " + "-" * 52)
                for entry in entries:
                    report_lines.append(
                        f"  {entry.ref_id:<8} {entry.count:<8} {entry.source_str:<20} "
                        f"{entry.confidence:<8.2f} {entry.first_page:<8}"
                    )
            else:
                report_lines.append("  [No entries detected]")
            report_lines.append("")
            
            # Section 3.6: Coverage Check (diagnostic)
            report_lines.append("-" * 70)
            report_lines.append("3.6. COVERAGE CHECK (WHY ENTRIES MAY BE FEW)")
            report_lines.append("-" * 70)
            if debug_bundle:
                pages_in = sorted(debug_bundle.pages_in_entries)
                pages_with_sup = debug_bundle.pages_with_sup_candidates
                
                report_lines.append(f"  entries_count: {debug_bundle.entries_count}")
                report_lines.append(f"  pages_in_entries: {len(pages_in)} pages -> {pages_in}")
                report_lines.append(f"  pages_with_sup_candidates: {len(pages_with_sup)} pages -> {pages_with_sup}")
                report_lines.append(f"  bib_ids_count: {debug_bundle.bib_ids_count}")
                report_lines.append(f"  bib_hard_constraint_used: {debug_bundle.bib_hard_constraint_used}")
                report_lines.append("")
                
                # Diagnosis
                report_lines.append("  --- DIAGNOSIS ---")
                if debug_bundle.entries_count == 0:
                    report_lines.append("  ! entries_count=0: No citations detected at all.")
                    if debug_bundle.superscript_candidates_count == 0 and debug_bundle.bracket_candidates_count == 0:
                        report_lines.append("    -> Both channels produced 0 candidates. Check PDF structure.")
                    elif debug_bundle.bib_hard_constraint_used and debug_bundle.bib_ids_count > 0:
                        report_lines.append("    -> Bib hard constraint ON but may be filtering everything.")
                elif len(pages_in) <= 2 and len(pages_with_sup) > len(pages_in):
                    report_lines.append("  ! pages_in_entries covers few pages but sup_candidates found on more.")
                    report_lines.append("    -> Likely: ref_ids from sup_candidates not matching bib_ids.")
                    report_lines.append("    -> Check bib_hard_constraint_used and bib_ids_sample.")
                elif len(pages_with_sup) <= 2:
                    report_lines.append("  ! pages_with_sup_candidates covers few pages.")
                    report_lines.append("    -> Likely: superscript geometric detection failing on most pages.")
                    report_lines.append("    -> Check sup_per_page_stats for reject reasons.")
                elif debug_bundle.entries_count < 10 and debug_bundle.bib_ids_count < 10:
                    report_lines.append("  ! Both entries and bib_ids are low.")
                    report_lines.append("    -> Bibliography extraction may have failed or PDF has few refs.")
                else:
                    report_lines.append("  Coverage looks reasonable.")
            else:
                report_lines.append("  [Debug bundle not available]")
            report_lines.append("")
            
            # Section 4: Bibliography Map (from engine)
            report_lines.append("-" * 70)
            report_lines.append("4. BIBLIOGRAPHY MAP (from engine)")
            report_lines.append("-" * 70)
            
            if debug_bundle and debug_bundle.bib_map_count > 0:
                report_lines.append(f"  Total bib entries: {debug_bundle.bib_map_count}")
                report_lines.append(f"  IDs sample: {sorted(debug_bundle.bib_ids_sample[:30]) if debug_bundle.bib_ids_sample else 'N/A'}")
                # Show per-entry bib_detail from citation_map
                for item_id, data in self.citation_map.items():
                    if isinstance(data, dict):
                        rid = data.get('ref_id', '?')
                        detail = data.get('bib_detail', 'N/A')
                        if detail and detail != "No detail found.":
                            report_lines.append(f"  [{rid}]: {detail[:150]}")
            else:
                report_lines.append("  [No bibliography detected by engine]")
            report_lines.append("")
            
            # Section 5: Extraction Statistics (no raw text to avoid leaking document content)
            report_lines.append("-" * 70)
            report_lines.append("5. EXTRACTION STATISTICS")
            report_lines.append("-" * 70)
            
            if self.recognizer and self.recognizer.extracted_text:
                txt = self.recognizer.extracted_text
                report_lines.append(f"  Total chars: {len(txt)}")
                report_lines.append(f"  Total lines: {txt.count(chr(10))}")
                report_lines.append(f"  Font spans tracked: {len(self.font_spans)}")
            else:
                report_lines.append("  [No extracted text available]")
            report_lines.append("")
            
            # Section 6: Span Mapping Summary
            report_lines.append("-" * 70)
            report_lines.append("6. SPAN MAPPING SUMMARY")
            report_lines.append("-" * 70)
            
            if self.span_mapping:
                report_lines.append(f"  Pages with spans: {len(self.span_mapping)}")
                for page, spans in sorted(self.span_mapping.items()):
                    report_lines.append(f"    Page {page}: {len(spans)} spans")
            else:
                report_lines.append("  [No span mapping available]")
            report_lines.append("")
            
            report_lines.append("=" * 70)
            report_lines.append("END OF DEBUG REPORT")
            report_lines.append("=" * 70)
            
            # Write to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            messagebox.showinfo("Export", f"Debug report exported successfully!\n\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export debug report:\n{e}")

    def _refresh_font_tree(self):
        # Clear
        for item in self.tree_fonts.get_children():
            self.tree_fonts.delete(item)
        self.tree_items = []
        
        # Sort by count desc
        sorted_stats = sorted(self.font_stats.items(), key=lambda x: x[1], reverse=True)
        
        unique_fonts = set()
        unique_sizes = set()
        
        for (font, size), count in sorted_stats:
            item_id = self.tree_fonts.insert("", tk.END, values=(font, size, count))
            self.tree_items.append((item_id, font, size, count))
            unique_fonts.add(font)
            unique_sizes.add(size)
            
        # Update Filters
        font_list = ["All Fonts"] + sorted(list(unique_fonts))
        size_list = ["All Sizes"] + sorted([str(s) for s in list(unique_sizes)])
        
        self.combo_filter_name['values'] = font_list
        self.combo_filter_name.set("All Fonts")
        self.combo_filter_size['values'] = size_list
        self.combo_filter_size.set("All Sizes")

    def _filter_fonts(self, event=None):
        name_filter = self.combo_filter_name.get()
        size_filter = self.combo_filter_size.get()
        
        # Detach all
        for item in self.tree_fonts.get_children():
            self.tree_fonts.detach(item)
            
        # Re-attach matches
        for item_id, font, size, count in self.tree_items:
            match_name = (name_filter == "All Fonts" or name_filter == font)
            match_size = (size_filter == "All Sizes" or size_filter == str(size))
            
            if match_name and match_size:
                self.tree_fonts.move(item_id, "", tk.END)

    def _on_font_tree_double_click(self, event):
        self._select_font_from_tree()

    def _select_font_from_tree(self):
        selection = self.tree_fonts.selection()
        if not selection: return
        item = self.tree_fonts.item(selection[0])
        font, size, count = item['values']
        
        # Simulate local structure for _select_by_font logic
        self.click_font_info = {"font": font, "size": float(size)}
        self._select_by_font()
        
        # Switch to Text tab
        self.notebook.select(self.tab_text)

    def _on_text_click(self, event):
        if not self.span_mapping: return
        try:
            idx = self.txt_output.index(f"@{event.x},{event.y}")
            # Scan current page vicinity is faster, but simple iteration works for now
            # Improved: range check using span_mapping directly
            for page, spans in self.span_mapping.items():
                for s in spans:
                    if self.txt_output.compare(idx, ">=", s["start"]) and self.txt_output.compare(idx, "<", s["end"]):
                        self._show_pdf_page(page)
                        return
        except Exception as e:
            self.status_var.set(f"Text click error: {e}")

    def _on_right_click(self, event):
        # Text Tab Right Click
        # 1. Determine font info under cursor for "Select All"
        try:
            index = self.txt_output.index(f"@{event.x},{event.y}")
            self.context_menu_data = {'index': index, 'event': event} # Save for sync
            
            if self.font_spans:
                clicked_font = None
                for span in self.font_spans:
                    if self.txt_output.compare(index, ">=", span["start"]) and \
                       self.txt_output.compare(index, "<", span["end"]):
                        clicked_font = span
                        break
                if clicked_font:
                    self.click_font_info = clicked_font
        except: pass
        self._show_context_menu(event, 'text')

    def _sync_from_text_to_pdf(self, event):
        # Use existing logic from _on_text_click but for the right-click pos
        if 'event' in self.context_menu_data:
            self._on_text_click(self.context_menu_data['event'])

    def _sync_from_pdf_to_text(self, event):
         # Logic is in _on_pdf_click, trigger it
         self._on_pdf_click(event)

    def _sync_from_ref_to_pdf(self):
        # Trigger same logic as double click
        self._on_ref_double_click(None) # Event not used in main logic part

    def _sync_from_ref_to_text(self):
        # Just select text
        item_id = self.tree_refs.focus()
        if item_id and item_id in self.citation_map:
            data = self.citation_map[item_id]
            
            # Handle new dict format
            if isinstance(data, dict):
                start = data.get('start', '1.0')
                end = data.get('end', f"{start}+5c")  # Use stored end position
            else:
                # Legacy tuple format (should not happen with new engine)
                raise RuntimeError(f"[SYNC] Legacy tuple format detected: {data}")
            
            self.txt_output.tag_remove("citation", "1.0", tk.END)
            self.txt_output.tag_add("citation", start, end)
            self.txt_output.see(start)
            self.notebook.select(self.tab_text)

    def _select_by_font(self):
        if not self.click_font_info or not self.font_spans: return
        target_font = self.click_font_info["font"]
        target_size = self.click_font_info["size"]
        self._clear_selection()
        count = 0
        for span in self.font_spans:
            if span["font"] == target_font and abs(span["size"] - target_size) < 0.5:
                self.txt_output.tag_add("font_selection", span["start"], span["end"])
                self.match_items.append((span["start"], span["end"]))
                count += 1
        if self.match_items:
            self.current_match_index = 0
            self._highlight_current_match()
            self.lbl_search_status.config(text=f"Font: {count} matches")
            self.status_var.set(f"Selected {count} segments.")

    def _search_text(self):
        query = self.search_entry.get()
        if not query: return
        self._clear_selection()
        start = "1.0"
        while True:
            start = self.txt_output.search(query, start, stopindex=tk.END, nocase=True)
            if not start: break
            end = f"{start}+{len(query)}c"
            self.txt_output.tag_add("match", start, end)
            self.match_items.append((start, end))
            start = end
        if self.match_items:
            self.current_match_index = 0
            self._highlight_current_match()
            self.lbl_search_status.config(text=f"Found {len(self.match_items)}")

    def _highlight_current_match(self):
        if not self.match_items or self.current_match_index < 0: return
        self.txt_output.tag_remove("current_match", "1.0", tk.END)
        start, end = self.match_items[self.current_match_index]
        self.txt_output.tag_add("current_match", start, end)
        self.txt_output.see(start)
        try:
            line_num = int(start.split('.')[0])
            target_page = self.page_mapping.get(line_num, 1)
            self._show_pdf_page(target_page)
        except: pass

    def _next_match(self):
        if not self.match_items: return
        self.current_match_index += 1
        if self.current_match_index >= len(self.match_items): self.current_match_index = 0
        self._highlight_current_match()
    def _prev_match(self):
        if not self.match_items: return
        self.current_match_index -= 1
        if self.current_match_index < 0: self.current_match_index = len(self.match_items) - 1
        self._highlight_current_match()
    def _clear_selection(self):
        self.txt_output.tag_remove("match", "1.0", tk.END)
        self.txt_output.tag_remove("current_match", "1.0", tk.END)
        self.txt_output.tag_remove("font_selection", "1.0", tk.END)
        self.match_items = []
        self.current_match_index = -1
        self.lbl_search_status.config(text="")
        
    def _update_font(self, e):
        f = self.font_family_var.get()
        s = int(self.font_size_var.get())
        self.txt_output.config(font=(f, s))
    def _copy_to_clipboard(self): 
        if self.recognizer and self.recognizer.extracted_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.recognizer.extracted_text)
    def _save_text(self): 
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path and self.recognizer:
            with open(path, 'w', encoding='utf-8') as f: f.write(self.recognizer.extracted_text)

    # --- Custom Toggle Logic ---


    def _draw_toggle_switch(self):
        self.cv_switch.delete("all")
        is_on = self.var_auto_analyze.get()
        
        # Colors (iOS style)
        bg_color = "#34c759" if is_on else "#e5e5ea" # Cleaner Light Grey
        thumb_color = "#ffffff"
        
        # Draw Pill (Line with Round Cap)
        self.cv_switch.create_line(12, 12, 32, 12, width=22, capstyle=tk.ROUND, fill=bg_color, tags="bg")
        
        # Draw Thumb
        if is_on:
            x = 32
        else:
            x = 12
        self.cv_switch.create_oval(x-10, 2, x+10, 22, fill=thumb_color, outline="", tags="thumb")
        
    def _toggle_analyze_switch(self, event):
        new_val = not self.var_auto_analyze.get()
        self.var_auto_analyze.set(new_val)
        self._draw_toggle_switch()
        self._on_analyze_toggle() 

if __name__ == '__main__':
    root = tk.Tk()
    app = PDFTextRecognizerApp(root)
    
    def on_closing():
        app._close_pdf_handle()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
