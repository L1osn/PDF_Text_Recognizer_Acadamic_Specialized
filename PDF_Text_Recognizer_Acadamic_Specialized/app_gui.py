"""
PDF Text Recognizer - Modern GUI Application
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import pyperclip
from PIL import Image, ImageTk
import pdfplumber
import re
import csv
from Pdf_to_text import AcademicPDFRecognizer


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
        
        # Navigation
        self.match_items = []
        self.current_match_index = -1
        
        # PDF Viewer State
        self.pdf_images = {}
        self.current_page = 1
        self.total_pages = 0
        self.view_swapped = False
        self.pdf_zoom = 1.0
        self.view_mode = "single"
        self.supersample = 2.0
        
        # Continuous Mode State
        self.page_offsets = []
        self.page_heights = []
        self.total_canvas_height = 0
        
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
        self.view_mode_var = tk.StringVar(value="Single Page")
        self.render_quality_var = tk.StringVar(value="Original") # High Res, Original, Low Memory
        
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
        
        ttk.Button(action_frame, text="Open PDF Document", command=self._browse_file, style="Primary.TButton").pack(fill=tk.X, pady=(0, 6), ipady=5)
        
        self.lbl_file_status = ttk.Label(action_frame, text="No file selected", style="Status.TLabel")
        self.lbl_file_status.pack(anchor=tk.W, pady=(0, 16))
        
        # --- Card 1: Display Settings ---
        card_display = ttk.Frame(self.sidebar, style="Card.TFrame", padding=15)
        card_display.pack(fill=tk.X, padx=16, pady=(0, 12))
        
        ttk.Label(card_display, text="DISPLAY SETTINGS", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        
        self.combo_quality = ttk.Combobox(card_display, textvariable=self.render_quality_var, 
                                          values=["High Res", "Original", "Low Memory"], 
                                          state="readonly")
        self.combo_quality.pack(fill=tk.X)
        self.combo_quality.bind("<<ComboboxSelected>>", self._on_quality_changed)
        
        # --- Card 2: Extraction ---
        card_extract = ttk.Frame(self.sidebar, style="Card.TFrame", padding=15)
        card_extract.pack(fill=tk.X, padx=16, pady=(0, 12))
        
        ttk.Label(card_extract, text="EXTRACTION", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        
        self.btn_extract_plain = ttk.Button(card_extract, text="Extract Plain Text", command=self._extract_text, state=tk.DISABLED)
        self.btn_extract_plain.pack(fill=tk.X, pady=4)
        
        self.btn_extract_fonts = ttk.Button(card_extract, text="Extract with Fonts", command=self._extract_with_fonts, state=tk.DISABLED)
        self.btn_extract_fonts.pack(fill=tk.X, pady=4)
        
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
                                          values=["Auto (Color+Font)", "Force Color", "Off (Scan Only)", "Legacy Regex"], 
                                          state="readonly")
        self.combo_ref_mode.pack(fill=tk.X, pady=(0, 12))
        self.combo_ref_mode.bind("<<ComboboxSelected>>", lambda e: self.root.focus())

        # Export Actions
        self.btn_export_refs = ttk.Button(card_config, text="Export Citations (CSV)", command=self._export_refs_to_csv, state=tk.DISABLED)
        self.btn_export_refs.pack(fill=tk.X)

        # Footer Actions
        footer_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)
        
        ttk.Button(footer_frame, text="Copy Text", command=self._copy_to_clipboard, state=tk.DISABLED).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        ttk.Button(footer_frame, text="Save As...", command=self._save_text, state=tk.DISABLED).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))
        
        # Swap view kept as small utility
        ttk.Button(self.sidebar, text="Swap Layout", command=self._swap_views).pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 8))
        
        # Main Split
        self.main_split = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_split.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # PDF Pane
        self.frame_pdf = ttk.Frame(self.main_split)
        
        ctrl_frame = ttk.Frame(self.frame_pdf, style="Toolbar.TFrame")
        ctrl_frame.pack(fill=tk.X, ipady=4)
        
        # View Mode
        self.combo_view = ttk.Combobox(ctrl_frame, textvariable=self.view_mode_var, values=["Single Page", "Continuous"], state="readonly", width=12)
        self.combo_view.pack(side=tk.LEFT, padx=(8, 4))
        self.combo_view.bind("<<ComboboxSelected>>", self._toggle_view_mode)
        
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
        
        self.canvas_pdf.bind("<Configure>", self._on_canvas_configure)
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
        self.txt_output.tag_config("code_font", font=("Consolas", 10))
        self.txt_output.tag_config("superscript", foreground="#d63384", font=("Segoe UI", 8, "bold"), offset=4) # Magenta + raised visually via offset if Tk support (Tk 8.6+ usually ignores offset in tag_config but we try, or just color)
        self.txt_output.tag_config("citation", background="#e0c0e0") # Light purple for citations
        self.txt_output.tag_config("font_meta", foreground="#888888", font=("Consolas", 9, "italic"))
        
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
        self.tree_fonts.bind("<Button-3>", self._on_font_tree_right_click) # Right click for context menu
        
        # -- Tab 4: Refs --
        self.tab_refs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_refs, text="Refs")
        
        # Status Label Only (Button moved to sidebar)
        self.lbl_ref_status = ttk.Label(self.tab_refs, text="Use 'Run Ref Module' in sidebar to scan.", foreground="gray")
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
        self._create_font_context_menu()

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

        # 2. Global Options Separator
        if self.context_menu.index("end") is not None:
             self.context_menu.add_separator()
             
        # 3. Global Options
        self.context_menu.add_command(label="Zoom In", command=self._zoom_in)
        self.context_menu.add_command(label="Zoom Out", command=self._zoom_out)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Reset View", command=lambda: self._show_pdf_page(1))
        
        self.context_menu.tk_popup(event.x_root, event.y_root)
        self.click_font_info = None # Context menu might set this

    def _create_font_context_menu(self):
        self.font_context_menu = tk.Menu(self.root, tearoff=0)
        self.font_context_menu.add_command(label="Select All in Text", command=self._select_font_from_tree)
        self.font_context_menu.add_separator()
        self.font_context_menu.add_command(label="Copy Font Name", command=self._copy_font_name_from_tree)
        self.font_context_menu.add_command(label="Copy Font Info", command=self._copy_font_details_from_tree)


    def _swap_views(self):
        if self.view_swapped:
            self.main_split.forget(self.frame_pdf)
            self.main_split.forget(self.frame_text)
            self.main_split.add(self.frame_pdf)
            self.main_split.add(self.frame_text)
            self.view_swapped = False
        else:
            self.main_split.forget(self.frame_pdf)
            self.main_split.forget(self.frame_text)
            self.main_split.add(self.frame_text)
            self.main_split.add(self.frame_pdf)
            self.view_swapped = True

    def _browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            self.recognizer = AcademicPDFRecognizer(path)
            self.lbl_file_status.config(text=os.path.basename(path))
            self.pdf_images = {}
            with pdfplumber.open(path) as pdf:
                self.total_pages = len(pdf.pages)
            if self.view_mode == "continuous":
                self._calculate_continuous_layout()
            self._show_pdf_page(1)
            self.btn_extract_plain.config(state=tk.NORMAL)
            self.btn_extract_fonts.config(state=tk.NORMAL)

    def _toggle_view_mode(self, event=None):
        mode = self.view_mode_var.get()
        if mode == "Continuous":
            self.view_mode = "continuous"
        else:
            self.view_mode = "single"
        self.pdf_images = {}
        self.canvas_pdf.delete("all")
        if self.view_mode == "continuous":
            self._calculate_continuous_layout()
            self._update_continuous_view()
            self._scroll_to_page(self.current_page)
        else:
            self.canvas_pdf.configure(scrollregion=(0,0,1,1))
            self._show_pdf_page(self.current_page)

    def _calculate_continuous_layout(self):
        if not self.recognizer or self.total_pages == 0: return
        self.page_offsets = []
        self.page_heights = []
        current_y = 0
        margin = 40
        scale_factor = (100 * self.pdf_zoom) / 72.0
        try:
            with pdfplumber.open(self.recognizer.pdf_path) as pdf:
                for page in pdf.pages:
                    h = page.height * scale_factor
                    self.page_offsets.append(current_y)
                    self.page_heights.append(h)
                    current_y += h + margin
            self.total_canvas_height = current_y
            self.canvas_pdf.configure(scrollregion=(0, 0, 1000, self.total_canvas_height))
        except: pass

    def _on_canvas_configure(self, event):
        if self.view_mode == "continuous":
            self._update_continuous_view()

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

    def _update_continuous_view(self):
        if not self.page_offsets: return
        y_top = self.canvas_pdf.canvasy(0)
        h = self.canvas_pdf.winfo_height()
        y_bottom = y_top + h
        
        visible_pages = []
        for i, offset in enumerate(self.page_offsets):
            height = self.page_heights[i]
            if offset + height > y_top and offset < y_bottom:
                visible_pages.append(i + 1)
        
        margin = 40
        current_center_page = self.current_page
        
        if visible_pages:
            start = max(1, min(visible_pages) - 1)
            end = min(self.total_pages, max(visible_pages) + 1)
            
            center = y_top + h/2
            for i in range(start-1, end):
                 if self.page_offsets[i] <= center <= self.page_offsets[i] + self.page_heights[i] + margin:
                     current_center_page = i + 1
                     self.lbl_page.config(text=f"Page {current_center_page}/{self.total_pages}")
                     break
            self.current_page = current_center_page
            
            # --- RENDER PRIORITIZATION Strategy ---
            # Adjust buffer based on Quality Mode
            quality = self.render_quality_var.get()
            if "Low" in quality:
                buffer = 0 # Only visible pages, aggressive memory saving
            elif "High" in quality:
                buffer = 4 # Pre-render more for smooth scrolling
            else:
                buffer = 2 # Original/Standard
            
            keep_pages = set()
            
            # Identify candidates
            range_start = max(1, visible_pages[0] - buffer)
            range_end = min(self.total_pages, visible_pages[-1] + buffer)
            render_candidates = list(range(range_start, range_end + 1))
            
            # Sort Sort candidates by distance from center page (Priority Queue effect)
            render_candidates.sort(key=lambda p: abs(p - current_center_page))
            
            for p in render_candidates:
                keep_pages.add(p)
                self._render_page_continuous(p)

            # Evict pages
            current_keys = list(self.pdf_images.keys())
            for p in current_keys:
                if p not in keep_pages:
                    self.canvas_pdf.delete(f"page_{p}")
                    del self.pdf_images[p]

    def _render_page_continuous(self, page_num):
        if page_num in self.pdf_images and self.canvas_pdf.find_withtag(f"page_{page_num}"): return
        try:
            with pdfplumber.open(self.recognizer.pdf_path) as pdf:
                page = pdf.pages[page_num - 1]
                
                # Determine Sampling Strategy based on Mode
                quality = self.render_quality_var.get()
                
                if "High" in quality:
                    # High Resolution: Force high crispness (2x to 3x)
                    ss = 2.5
                    resample_mode = Image.Resampling.LANCZOS
                elif "Low" in quality:
                    # Low Memory: Native resolution, low overhead
                    ss = 0.8 # Slightly undersample for speed/memory if needed, or 1.0
                    resample_mode = Image.Resampling.NEAREST # Fast
                else:
                    # Original (Dynamic)
                    if self.pdf_zoom >= 1.5:
                        ss = 1.2 
                    elif self.pdf_zoom >= 1.0:
                        ss = 1.5
                    else:
                        ss = 2.0
                    resample_mode = Image.Resampling.LANCZOS if ss > 1.5 else Image.Resampling.BILINEAR
                
                target_factor = 100 * self.pdf_zoom
                render_factor = target_factor * ss
                
                im_high = page.to_image(resolution=render_factor).original
                target_w = int(im_high.width / ss)
                target_h = int(im_high.height / ss)
                
                im = im_high.resize((target_w, target_h), resample_mode)
                
                photo = ImageTk.PhotoImage(im)
                self.pdf_images[page_num] = photo
                offset_y = self.page_offsets[page_num - 1]
                canvas_width = self.canvas_pdf.winfo_width()
                x = max(0, (canvas_width - photo.width()) // 2)
                self.canvas_pdf.create_image(x, offset_y, image=photo, anchor=tk.NW, tags=f"page_{page_num}")
                
                # Re-raise highlights if any
                self.canvas_pdf.tag_raise("ref_highlight")
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
        self._update_continuous_view() 

    def _on_pdf_release(self, event):
        if not self._drag_data["moved"]:
            self._on_pdf_click(event) 
            
    def _on_pdf_click(self, event):
        if not self.span_mapping: return
        try:
            x = self.canvas_pdf.canvasx(event.x)
            y = self.canvas_pdf.canvasy(event.y)
            target_page_num = self.current_page
            if self.view_mode == "continuous":
                found_page = False
                for i, offset in enumerate(self.page_offsets):
                    if offset <= y <= offset + self.page_heights[i]:
                        target_page_num = i + 1
                        y = y - offset
                        found_page = True
                        break
                if not found_page: return
            
            scale = 72 / (100 * self.pdf_zoom)
            pdf_x = x * scale
            pdf_y = y * scale
            
            page_spans = self.span_mapping.get(target_page_num, [])
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
            if found: self.status_var.set("Match found")
        except Exception: pass

    def _scroll_to_page(self, page_num):
        if self.view_mode == "single":
            self._show_pdf_page(page_num)
        else:
            if page_num <= len(self.page_offsets):
                y = self.page_offsets[page_num - 1]
                if self.total_canvas_height > 0:
                    frac = y / self.total_canvas_height
                    self.canvas_pdf.yview_moveto(frac)
                    self._update_continuous_view()

    def _zoom_in(self):
        self.pdf_zoom += 0.1 # Finer step
        self._update_zoom()
    def _zoom_out(self):
        if self.pdf_zoom > 0.1:
            self.pdf_zoom -= 0.1
            self._update_zoom()
            
    def _on_quality_changed(self, event=None):
        # Clear cache and refresh
        self.pdf_images.clear()
        self.canvas_pdf.delete("all")
        if self.view_mode == "continuous":
            self._update_continuous_view()
        else:
             self._show_pdf_page(self.current_page)

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
        self.canvas_pdf.delete("all")
        if self.view_mode == "continuous":
            self._calculate_continuous_layout()
            self._update_continuous_view()
        else:
            self._show_pdf_page(self.current_page)

    def _show_pdf_page(self, page_num):
        if self.view_mode != "single":
            self._scroll_to_page(page_num)
            return
        if not self.recognizer or page_num < 1 or page_num > self.total_pages: return
        try:
            if page_num not in self.pdf_images:
                with pdfplumber.open(self.recognizer.pdf_path) as pdf:
                    page = pdf.pages[page_num - 1]
                    
                    # --- High-DPI Rendering ---
                    # Base zoom * Screen Scale * Supersampling
                    display_zoom = self.pdf_zoom
                    # Note: pdfplumber uses 72 DPI as base. "scale_to" or explicit resolution needed.
                    # We use explicit resolution calculation.
                    
                    # Target scale considering supersampling
                    total_scale = display_zoom * self.supersample
                    
                    # Render high-res image
                    im_high = page.to_image(resolution=72 * total_scale).original
                    
                    # Resize down for antialiasing
                    target_w = int(im_high.width / self.supersample)
                    target_h = int(im_high.height / self.supersample)
                    
                    im = im_high.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    self.pdf_images[page_num] = ImageTk.PhotoImage(im)
            self.canvas_pdf.delete("all")
            self.canvas_pdf.create_image(0, 0, image=self.pdf_images[page_num], anchor=tk.NW)
            self.canvas_pdf.config(scrollregion=self.canvas_pdf.bbox(tk.ALL))
            self.current_page = page_num
            self.lbl_page.config(text=f"Page {page_num}/{self.total_pages}")
        except Exception as e: print(e)

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
        if "Legacy" in mode_str: 
            color_arg = 'off' 
            # Legacy implied standard behavior, still removes refs but without smart color
            
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

    def _extract_with_fonts(self):
        if not self.recognizer: return
        self.status_var.set("Extracting...")
        self.root.update()
        self.match_items = []
        
        # Reset GUI & Maps
        self.txt_output.delete(1.0, tk.END)
        self.span_mapping = {}
        self.page_mapping = {}
        self.font_spans = []
        self.font_stats = {} 
        
        # Initialize recognizer storage for later use (e.g. analysis)
        self.recognizer.text_spans = []
        
        # Incremental Processing
        processed_pages = 0
        total = self.total_pages
        
        try:
            for page_num, spans in self.recognizer.iter_extract_text_with_fonts():
                # Update Recognizer State
                self.recognizer.text_spans.extend(spans)
                
                # UI Feedback
                processed_pages += 1
                self.status_var.set(f"Extracting page {processed_pages}/{total}...")
                if processed_pages % 1 == 0: # Update every page
                    self.root.update()
                
                # Page header - REMOVED per user request to avoid mapping pollution
                # self.txt_output.insert(tk.END, f"\n\n--- Page {page_num} ---\n")
                
                for span in spans:
                    # 1) Trust backend: only remove \r
                    text_content = span.text.replace('\r', '')
                    if text_content == "":
                        continue

                    # 2) Pure newline span: insert directly, skip mapping/stats
                    if text_content == "\n":
                        self.txt_output.insert(tk.END, "\n")
                        continue

                    # 3) Normal text span: no extra \n added
                    start_idx = self.txt_output.index(tk.END)
                    self.txt_output.insert(tk.END, text_content)
                    end_idx = self.txt_output.index(tk.END)

                    # 4) span_mapping: only map actual content, not meta
                    if span.page not in self.span_mapping:
                        self.span_mapping[span.page] = []
                    self.span_mapping[span.page].append({
                        "bbox": span.bbox,
                        "start": start_idx,
                        "end": end_idx
                    })

                    # 5) font_spans: for font filtering/positioning
                    self.font_spans.append({
                        "text": span.text,
                        "font": span.font_name,
                        "size": span.font_size,
                        "is_bold": getattr(span, 'is_bold', False),
                        "is_italic": getattr(span, 'is_italic', False),
                        "start": start_idx,
                        "end": end_idx
                    })

                    # 6) page_mapping: map by actual text lines
                    s_line = int(start_idx.split('.')[0])
                    e_line = int(end_idx.split('.')[0])
                    for l in range(s_line, e_line + 1):
                        self.page_mapping[l] = span.page

                    # 7) stats: skip control newlines (already handled above)
                    key = (span.font_name, round(span.font_size, 1))
                    self.font_stats[key] = self.font_stats.get(key, 0) + 1

            self.status_var.set(f"Extraction complete. {len(self.font_spans)} text segments found.")
            
            # Sync extracted_text for Copy/Save consistency
            self.recognizer.extracted_text = self.txt_output.get("1.0", tk.END)
            
            # Trigger backend validation for superscripts
            self.recognizer._validate_superscripts()
            
            self._refresh_font_tree()
            
            if self.var_auto_analyze.get():
                 self._analyze_citations()
                 
        except Exception as e:
            msg = f"Extraction Failed:\n{str(e)}"
            self.status_var.set("Error during extraction")
            self.txt_output.insert(tk.END, f"\n\n!!! ERROR !!!\n{msg}\n")
            messagebox.showerror("Error", msg)

    def _on_analyze_toggle(self):
        if self.var_auto_analyze.get():
            self._analyze_citations()

    def _analyze_citations(self, verbose=False):
        """
        Two-stage citation analysis using CitationAnalyzer:
        Stage 1: Geometric superscript detection (already done in extraction)
        Stage 2: Semantic validation and deduplication
        """
        # Ensure we have font data for advanced analysis
        if not hasattr(self.recognizer, 'text_spans') or not self.recognizer.text_spans:
            if verbose or self.var_auto_analyze.get(): 
                self.status_var.set("Analyzing fonts for citations (Auto-Scan)...")
                self.root.update()
                self.recognizer.extract_text_with_fonts()  

        # 1. Parse Bibliography Section for constraint
        self.bibliography_map = self._parse_bibliography_section(verbose=False)
        
        # Clear UI
        self.tree_refs.delete(*self.tree_refs.get_children())
        self.citation_map = {} 
        
        # 2. Run backend validation (Stage 2: Semantic Analysis)
        self.recognizer._validate_superscripts()
        
        # 3. Get validated RefEntry objects
        entries = self.recognizer.get_citation_entries()
        stats = self.recognizer.get_citation_stats()
        
        # 4. Display entries in tree (Two-layer structure)
        matches_found = 0
        
        for entry in entries:
            # Try to link to Bibliography
            bib_detail = "No detail found."
            ref_key = entry.ref_id
            
            # Keys to try for bibliography lookup
            keys_to_try = [ref_key, f"[{ref_key}]", f"{ref_key}.", f"({ref_key})"]
            for k in self.bibliography_map:
                if any(key in k for key in keys_to_try):
                    bib_detail = self.bibliography_map[k]
                    break
            
            # Filter if user wants to hide entries without detail
            if self.var_hide_no_detail.get() and bib_detail == "No detail found.":
                continue
            
            # Get first occurrence for display
            if entry.occurrences:
                first_occ = entry.occurrences[0]
                page = first_occ.page
                bbox = first_occ.bbox
            else:
                page = "?"
                bbox = None
            
            # Format: [ref_id] with occurrence count if >1
            display_text = f"[{ref_key}]"
            if entry.count > 1:
                display_text += f" (×{entry.count})"
            
            # Insert into tree
            item_id = self.tree_refs.insert("", tk.END, values=(
                display_text,
                bib_detail[:100] + "..." if len(bib_detail) > 100 else bib_detail,
                page
            ))
            
            # Store full data in citation_map for selection/jumping
            # Enhanced structure: includes all occurrences
            tk_pos = self._find_citation_in_text(ref_key) or "1.0"
            self.citation_map[item_id] = {
                'ref_id': ref_key,
                'start': tk_pos,
                'end': f"{tk_pos}+{len(ref_key)}c",
                'bib_detail': bib_detail,
                'occurrences': entry.occurrences,  # List[CitationOccurrence]
                'first_bbox': bbox,
                'first_page': page
            }
            
            matches_found += 1
        
        # 5. Update status
        total_occurrences = stats.get('total_occurrences', 0)
        status_msg = f"Found {matches_found} unique refs ({total_occurrences} occurrences)"
        
        if stats.get('bib_constrained'):
            status_msg += f" | Bib: {stats.get('bib_count', 0)} IDs"
        
        if self.bibliography_map:
            status_msg += f" | Linked: {len(self.bibliography_map)}"
        
        self.status_var.set(status_msg)
        self.lbl_ref_status.config(text=status_msg, foreground=self.accent_color)
        
        if matches_found > 0:
            self.btn_export_refs.config(state=tk.NORMAL)
        else:
            self.btn_export_refs.config(state=tk.DISABLED)
    
    def _find_citation_in_text(self, ref_key: str) -> str:
        """Find citation marker position in text output"""
        patterns = [f"[{ref_key}]", ref_key, f"({ref_key})"]
        for pattern in patterns:
            pos = self.txt_output.search(pattern, "1.0", stopindex=tk.END)
            if pos:
                return pos
        return None

    def _parse_bibliography_section(self, verbose=False):
        """
        Structure-Aware Parsing:
        1. Determine Body Font Size
        2. Find 'References' Header (Larger/Bold)
        3. Parse entries [1] ...
        """
        if not hasattr(self, 'font_spans') or not self.font_spans: return {}
        
        # 1. Determine Body Font Size (Mode)
        sizes = [s['size'] for s in self.font_spans]
        if not sizes: return {}
        from collections import Counter
        body_size = Counter(sizes).most_common(1)[0][0]
        
        # 2. Find Header
        ref_start_idx = -1
        header_keywords = ["references", "bibliography", "参考文献"]
        
        for i, span in enumerate(self.font_spans):
            txt = span['text'].strip().lower()
            # Remove numbering like "10. " or "6 "
            clean_txt = re.sub(r'^[\d\.]+\s*', '', txt)
            
            if clean_txt in header_keywords:
                # Criteria 1: Font features
                is_larger = span['size'] > body_size + 0.5 # Relaxed threshold
                is_bold = span.get('is_bold', False) or "bold" in span['font'].lower()
                
                # Criteria 2: Line Isolation (It's a header if it's short)
                is_short = len(txt) < 30
                
                # If it matches keyword and is short, we tend to accept it even if font isn't perfect
                if (clean_txt in header_keywords and is_short) or (is_larger or is_bold):
                    ref_start_idx = i
                    break
        
        if ref_start_idx == -1: 
             print("Debug: Reference header not found, trying content-based scanning.")
             # Fallback: Content-Based Detection (Sequential [1], [2]...)
             # Scan last 50% of the text for a sequence of [1], [2]...
             total_len = len(self.font_spans)
             start_scan = int(total_len * 0.5)
             
             # Look for [1] at start of line
             potential_start = -1
             for i in range(start_scan, total_len):
                 txt = self.font_spans[i]['text'].strip()
                 if re.match(r'^\[1\]|1\.', txt):
                     # Check if next few lines have [2], [3]... to confirm it's a list
                     found_seq = True
                     current_num = 1
                     look_ahead = 0
                     for j in range(i + 1, min(i + 20, total_len)):
                         next_txt = self.font_spans[j]['text'].strip()
                         # Skip empty or very short lines
                         if len(next_txt) < 3: continue
                         
                         match = re.match(r'^\[(\d+)\]|(\d+)\.', next_txt)
                         if match:
                             num = int(match.group(1) or match.group(2))
                             if num == current_num + 1:
                                 current_num += 1
                                 look_ahead = 0 # reset
                             else:
                                 # Maybe it's a multi-line ref, continue looking
                                 look_ahead += 1
                                 if look_ahead > 5: break # Text gap too large
                     
                     if current_num >= 2: # We found at least 1, 2...
                         ref_start_idx = i - 1 # Start just before [1]
                         if ref_start_idx < 0: ref_start_idx = 0
                         print(f"Debug: Found inferred bibliography start at index {ref_start_idx}")
                         break
            
             if ref_start_idx == -1:
                 if verbose:
                     print("Verbose: Header parsing failed AND Content-based parsing failed.")
                 return {}
        
        # 3. Parse Entries from this point onwards
        bib_map = {}
        
        header_span = self.font_spans[ref_start_idx]
        header_pos_start = header_span['start'] # "line.char"
        
        full_text = self.txt_output.get(header_pos_start, tk.END)
        
        # Regex for bibliography items: 
        # Support [1], 1., or even just 1 (if followed by space similar to next lines)
        # Improvement: Look for "1." or "[1]" or just "1" at start of lines.
        entry_pattern = re.compile(r'(?:\n|^)\s*(?:\[(\d+)\]|(\d+)\.|(\d+)\s+[A-Z])')
        
        last_pos = 0
        current_ref_key = None
        
        for match in entry_pattern.finditer(full_text):
            if current_ref_key:
                # Capture text between last match and this match
                content = full_text[last_pos:match.start()].strip().replace('\n', ' ')
                bib_map[current_ref_key] = content
            
            # Start new entry
            num = match.group(1) or match.group(2)
            current_ref_key = f"[{num}]"
            last_pos = match.end()
            
        # Last entry
        if current_ref_key and last_pos < len(full_text):
             content = full_text[last_pos:].strip().replace('\n', ' ')
             bib_map[current_ref_key] = content
             
        # URL-to-Journal Enrichment
        return self._enrich_bibliography(bib_map)

    def _enrich_bibliography(self, bib_map):
        """Try to resolve journal names from URLs or DOIs if possible"""
        import urllib.request
        from concurrent.futures import ThreadPoolExecutor
        
        url_pattern = re.compile(r'https?://[^\s<>"]+|doi:10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.I)
        
        def resolve_journal(key, content):
            if "journal" in content.lower() or "journal" in key.lower(): return # Already has info
            
            matches = url_pattern.findall(content)
            if not matches: return
            
            url = matches[0]
            if url.lower().startswith("doi:"):
                url = "https://doi.org/" + url[4:]
            
            # Heuristic 1: Domain-based journal names
            domain_map = {
                "nature.com": "Nature",
                "science.org": "Science",
                "cell.com": "Cell",
                "sciencedirect.com": "Elsevier / ScienceDirect",
                "ieeexplore.ieee.org": "IEEE",
                "pubs.acs.org": "ACS",
                "link.springer.com": "Springer",
                "onlinelibrary.wiley.com": "Wiley",
                "lancet.com": "The Lancet",
                "nejm.org": "New England Journal of Medicine",
                "pnas.org": "PNAS",
                "arxiv.org": "arXiv"
            }
            
            for domain, name in domain_map.items():
                if domain in url:
                    bib_map[key] = f"[{name}] " + content
                    return

            # Heuristic 2: Try to fetch page title (Quick & Lazy)
            # This is done in a thread to keep UI somewhat responsive
            # Only try for the first few to avoid long waits
            ENABLE_FETCH_TITLE = False
            if ENABLE_FETCH_TITLE:
                try:
                    # Basic request with timeout
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=2) as response:
                        html = response.read(2048).decode('utf-8', errors='ignore')
                        title_match = re.search(r'<title>(.*?)</title>', html, re.I)
                        if title_match:
                            title = title_match.group(1).strip()
                            # Often title contains Journal Name after a separator
                            for sep in ["|", "-", "—", ":"]:
                                if sep in title:
                                    parts = title.split(sep)
                                    # Pick the part that looks most like a journal (usually last or first)
                                    if len(parts[-1].strip()) > 3:
                                        bib_map[key] = f"[{parts[-1].strip()}] " + content
                                        return
                except: pass

        # Process in parallel but limited to keep it snappy
        with ThreadPoolExecutor(max_workers=5) as executor:
            for k, v in bib_map.items():
                executor.submit(resolve_journal, k, v)
        
        return bib_map

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
                    occ_text += f"  {i+1}. Page {occ.page}: ...{occ.anchor_text}...\n"
                if len(occurrences) > 10:
                    occ_text += f"  ... and {len(occurrences) - 10} more\n"
                
                self.txt_ref_detail.delete("1.0", tk.END)
                self.txt_ref_detail.insert("1.0", f"REF [{ref_id}]\n\n{occ_text}\n\nBIBLIOGRAPHY:\n{bib_detail}")
            else:
                # Legacy tuple format (backwards compatibility)
                if len(data) >= 4:
                    context = data[3]
                    detail = data[2]
                else:
                    context = "N/A"
                    detail = "N/A"
                self.txt_ref_detail.delete("1.0", tk.END)
                self.txt_ref_detail.insert("1.0", f"CONTEXT:\n{context}\n\nFULL BIBLIOGRAPHY:\n{detail}")

    def _on_ref_double_click(self, event):
        item_id = self.tree_refs.focus()
        if item_id and item_id in self.citation_map:
            data = self.citation_map[item_id]
            
            # New dict format
            if isinstance(data, dict):
                start = data.get('start', '1.0')
                target_bbox = data.get('first_bbox')
                target_page = data.get('first_page')
                ref_id = data.get('ref_id', '')
                
                # Highlight in text
                self.txt_output.tag_remove("citation", "1.0", tk.END)
                end = f"{start}+{len(ref_id) + 2}c"  # +2 for brackets
                self.txt_output.tag_add("citation", start, end)
                self.txt_output.see(start)
                
            else:
                # Legacy tuple format
                if len(data) >= 6:
                    start, end, _, _, target_bbox, target_page = data
                else:
                    start, end, _, _ = data[:4]
                    target_bbox, target_page = None, None
                
                self.txt_output.tag_remove("citation", "1.0", tk.END)
                self.txt_output.tag_add("citation", start, end)
                self.txt_output.see(start)
            
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
                
                # Draw highlight on canvas
                if target_page in self.pdf_images:
                    scale = (100 * self.pdf_zoom) / 72.0
                    x0, top, x1, bottom = target_bbox
                    
                    c_x0 = x0 * scale
                    c_top = top * scale
                    c_x1 = x1 * scale
                    c_bottom = bottom * scale
                    
                    self.canvas_pdf.create_rectangle(c_x0, c_top, c_x1, c_bottom, outline="red", width=3, tags="ref_highlight")
                    self.status_var.set(f"Located on Page {target_page}")

    def _export_refs_to_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not filename: return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Reference Text", "Bibliography Detail", "Page"])
                for child in self.tree_refs.get_children():
                    values = self.tree_refs.item(child)['values']
                    writer.writerow(values)
            messagebox.showinfo("Export", "References exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

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

    def _on_font_tree_right_click(self, event):
        # Select item on right click
        iid = self.tree_fonts.identify_row(event.y)
        if iid:
            self.tree_fonts.selection_set(iid)
            self.font_context_menu.tk_popup(event.x_root, event.y_root)

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

    def _copy_font_name_from_tree(self):
        selection = self.tree_fonts.selection()
        if not selection: return
        item = self.tree_fonts.item(selection[0])
        font = item['values'][0]
        pyperclip.copy(font)

    def _copy_font_details_from_tree(self):
        selection = self.tree_fonts.selection()
        if not selection: return
        item = self.tree_fonts.item(selection[0])
        font, size, count = item['values']
        text = f"Font: {font}, Size: {size}, Occurrences: {count}"
        pyperclip.copy(text)

    def _on_text_click(self, event):
        if not self.span_mapping: return
        try:
            idx = self.txt_output.index(f"@{event.x},{event.y}")
            # Scan current page vicinity is faster, but simple iteration works for now
            # Improved: range check using span_mapping directly
            for page, spans in self.span_mapping.items():
                for s in spans:
                    if self.txt_output.compare(idx, ">=", s["start"]) and self.txt_output.compare(idx, "<", s["end"]):
                        self._scroll_to_page(page)
                        return
        except: pass

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
                ref_id = data.get('ref_id', '')
                end = f"{start}+{len(ref_id) + 2}c"
            else:
                # Legacy tuple format
                start, end, _, _ = data[:4]
            
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
            self._scroll_to_page(target_page)
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
        if self.recognizer and self.recognizer.extracted_text: pyperclip.copy(self.recognizer.extracted_text)
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
    root.mainloop()
