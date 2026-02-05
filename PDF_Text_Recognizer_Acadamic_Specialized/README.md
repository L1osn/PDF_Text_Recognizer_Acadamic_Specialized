# PDF_Text_Recognizer_Acadamic_Specialized

English_version
**PDF_Text_Recognizer_Acadamic_Specialized** is a desktop application for high-fidelity academic PDF parsing.
It focuses on **geometry-aware text extraction**, **font/style analysis**, and **in-text citation (superscript) detection**, with synchronized navigation between PDF view, extracted text, and references.

The project is designed for research papers and technical PDFs where layout, typography, and citations matter.

---

## Key Features

### 1. Geometry-Aware Text Extraction

* Character-level parsing using `pdfplumber`
* Line reconstruction based on vertical clustering
* Space and newline recovery based on geometric gaps
* Preserves reading order across complex layouts

### 2. Font & Style Analysis

* Aggregates text into spans by:

  * Font name
  * Font size
  * Color
  * Bold / Italic
* Provides font usage statistics for the entire document
* Enables span-level highlighting and inspection

### 3. Superscript Citation Detection

* Detects in-text references based on layout geometry, not text heuristics
* Handles:

  * True superscripts
  * Upper-right attached markers
  * Same-size but vertically raised citations
* Line-based token aggregation prevents fragmented references
* Robust against font changes and inline formatting

### 4. Citation Analysis Pipeline

* Separates **geometric detection** from **semantic validation**
* Supports multiple analysis presets:

  * `strict`
  * `balanced`
  * `recall`
* Optionally constrains citations using bibliography IDs
* Deduplicates occurrences across pages and lines

### 5. Synchronized GUI Navigation

* PDF view, extracted text, and reference list are linked
* Click text → jump to PDF
* Double-click reference → highlight source in PDF
* Supports:

  * Single-page view
  * Continuous scroll view
  * Zoom and pan

---

## Architecture Overview

```
PDF (pdfplumber)
   ↓
LayoutAnalyzer
   - Line clustering
   - Body text metrics
   - Superscript geometry detection
   ↓
Superscript Tokens
   ↓
CitationAnalyzer
   - Validation
   - Deduplication
   - Bibliography alignment
   ↓
GUI (Tkinter)
   - PDF rendering
   - Text spans
   - Reference table
```

Key design principle:
**The backend decides structure; the frontend only renders.**

---

## Superscript Detection Strategy

Superscripts are identified using a combination of:

* Mid-Y position relative to body text
* X-height estimation from lowercase characters
* Right-attachment heuristics (upper-right adjacency)
* Dynamic thresholds derived from body font size
* Fallback detection for small raised clusters at line ends

Detection does **not** rely on brackets (`[1]`) or regex alone.

---

## Installation

### Requirements

* Python 3.9+
* pdfplumber
* Pillow
* pyperclip

Install dependencies:

```bash
pip install pdfplumber pillow pyperclip
```

---

## Usage

Run the GUI:

```bash
python appgui.py
```

Main actions:

* Open a PDF document
* Extract plain text
* Extract text with font information
* Analyze and export citations (CSV)

---

## Limitations

* Optimized for academic PDFs (journals, proceedings)
* Does not yet fully support:

  * Author-year citations (e.g. Smith et al., 2020)
  * OCR-based PDFs
* Bibliography parsing depends on document consistency

---

## Project Goals

* Reliable academic PDF parsing without OCR
* Precise citation localization using geometry
* Research-grade text extraction suitable for analysis pipelines

--------------------------------------------------------------------------------------------------------------------------
Chinese_version

# PDF_Text_Recognizer_Acadamic_Specialized
PDF_Text_Recognizer_Acadamic_Specialized 是一个面向**学术论文**的 PDF 解析工具，专注于**版面几何解析**、**字体级文本抽取**以及**文献引用（citation）识别**。
项目目标不是“尽量多地抽字”，而是**在最大程度保留版面与语义结构的前提下，可靠地还原正文与引用关系**。
-----

### 1. 几何版面分析（Geometric Layout Analysis）

* 基于字符级坐标（pdfplumber `chars`）
* 行聚类采用纵向几何一致性，而非字符串启发
* 使用字符 **中位高度（mid-Y）** 与 **x-height** 推断正文基线

### 2. 高鲁棒性的上标（Superscript）识别

支持多种真实论文中常见但容易漏检的情况：

* 真正的右上角标（不带方括号）
* 同字号但位置上移的 superscript
* 紧贴前一字符的右上附着标记
* Unicode 上标（¹²³⁴⁵⁶⁷⁸⁹⁰ ⁱ ⁿ）

采用的策略包括：

* 基于 mid-Y 的抬升判定（而非 bottom）
* x-height 相对字号比较
* 右附着（right-attachment）几何启发
* 行尾小字符兜底扫描（fallback sweep）

### 3. 上标 token 的行内聚合

* 在字符层面标记 superscript
* 再在**行内**按动态间距合并为 superscript token
* 避免 span 级切分导致的碎片化引用

### 4. Citation 语义分析与去重

* 与 `CitationAnalyzer` 解耦
* 支持 strict / balanced / recall 三种分析预设
* 结合 bibliography section 自动约束合法引用 ID
* 自动去除同页、同行、同位置的重复引用

### 5. 字体与颜色信息保留

* 每个 `TextSpan` 保留字体名、字号、颜色、样式
* 支持字体统计，用于标题/正文/引用区分

### 6. GUI 支持（Tkinter）

* 单页 / 连续滚动视图
* PDF ↔ Text ↔ Reference 双向定位
* 引用高亮、定位与导出（CSV）

---

## 项目结构

```text
.
├── appgui.py              # Tkinter GUI
├── Pdf_to_text.py         # 核心解析与布局分析
├── citation_analyzer.py   # 引用语义分析与去重
├── README.md
```

---

## 安装依赖

```bash
pip install pdfplumber pillow pyperclip
```

Python ≥ 3.9 推荐。

---

## 使用方式

### 启动 GUI

```bash
python appgui.py
```

### 基本流程

1. 打开 PDF
2. 选择显示模式（Single / Continuous）
3. 执行：

   * Extract Plain Text
   * 或 Extract with Fonts
4. 勾选 *Auto Analyze Refs* 自动解析文献引用
5. 在 Refs 面板中查看、定位或导出引用

---

## 设计原则

* **几何优先于字符串**：不依赖正则“猜结构”
* **后端负责结构，前端负责渲染**
* **superscript ≠ citation**：几何检测与语义验证分离
* **可解释、可调参**：所有关键阈值集中且可配置

---

## 已知限制

* 目前主要针对**数字型 citation**（如 ¹²、[12]）
* Author-year（Smith 2020）风格尚未作为一等公民支持
* 对严重扫描失真或无字符层的 PDF 支持有限

---

## 适用场景

* 学术论文结构化解析
* 引用关系分析
* PDF → 文本 + 引用数据清洗
* 为下游 NLP / 检索 / 知识图谱提供高质量输入


