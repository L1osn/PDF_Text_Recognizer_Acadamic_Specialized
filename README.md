下面是一份**精简、工程向、双语（中/英）README.md**，不走营销风，偏“可维护 / 可审计 / 可部署”，emoji 已极少化。可直接作为仓库根 README 使用。

---

# PDF Text Recognizer Pro

A desktop application for **PDF text extraction, font-aware layout analysis, and citation detection**, designed for academic and technical documents.

一个面向**学术/技术 PDF** 的桌面工具，支持文本抽取、字体与版式分析，以及高可靠的引用（citation）识别。

---

## Features | 功能概览

### Core Capabilities | 核心能力

* Text extraction with exact span-to-PDF coordinate mapping
  精确文本抽取，支持文本 ⇄ PDF 坐标双向定位
* Font-aware layout analysis (font name, size, style)
  基于字体信息的版式分析
* Superscript & bracket citation detection engine
  上标 / 方括号双通道引用识别引擎
* Bibliography parsing with false-positive suppression
  参考文献解析，并主动抑制误识别
* Modern GUI with synchronized PDF/Text views
  现代 GUI，PDF 与文本视图联动

---

## Citation Engine Design | 引用引擎设计

### Detection Channels | 识别通道

* **Superscript channel**: geometric + font-size based detection
  上标通道：基于几何关系与字号比例
* **Bracket channel**: `[n]`, `(n)` style inline citations
  方括号通道：处理常规行内引用

### Bibliography Handling | 参考文献处理

* Strict line-head ID matching (`^\s*(\[(\d+)\]|(\d+)\.)`)
  严格限制编号只在行首匹配
* Year-number filtering (1900–2099) to prevent ID pollution
  年份过滤，避免把年份当作引用编号
* `max_id_multiplier` false-citation upper bound
  基于最大 bib_id 的上限过滤，清理明显假引用

### Soft Constraint System | 软约束机制

* When bibliography is reliable (≥ N entries), unlinked citations are **penalized but not discarded**
  参考文献充足时，未链接引用会降置信度但不直接丢弃
* Small or missing bibliographies automatically disable penalties
  文献不足时自动降级，避免误伤召回

---

## Architecture | 架构概览

```
PDF (pdfplumber)
   ↓
PageData / LineData / CharData
   ↓
Citation Channels (Superscript / Bracket)
   ↓
Fusion Engine (confidence scoring + filtering)
   ↓
RefEntry / Occurrence
   ↓
GUI (PDF ↔ Text ↔ Citation sync)
```

* All GUI updates run on the main thread
  所有 UI 更新严格在主线程执行
* Background tasks are cancelable via job-id invalidation
  后台任务支持软取消，防竞态
* Image rendering uses LRU cache to cap memory usage
  PDF 渲染采用 LRU 缓存，限制内存占用

---

## Reliability & Safety | 稳定性与安全性

* Thread-safe background execution (no Tk access in workers)
  后台线程不直接访问 Tk 控件
* Job ID mechanism prevents stale callbacks from overwriting state
  Job ID 防止旧任务回调污染新文档
* PDF handle caching with guaranteed release on exit/errors
  PDF 句柄集中管理，异常/退出时强制释放
* Debug reports never include raw document text
  调试报告不泄露原文内容，适合共享

---

## Build & Run | 构建与运行

### Run from source

```bash
python app_gui.py
```

### Windows executable

* Prebuilt executable: `dist_exe/PDFTextRecognizer.exe`
* No Python environment required

---

## Testing & Verification | 测试与验证

Included test scripts:

* `test_citation_improvements.py` – citation logic validation
* `reconciliation_check.py` – configuration & import-path verification

All tests must pass before deployment.

---

## Scope & Non-Goals | 设计边界

* Not intended for OCR (scanned PDFs)
  不做 OCR
* Not a reference manager or citation formatter
  不生成或管理参考文献格式
* Focused on **structural correctness and traceability**, not heuristics-only extraction
  关注结构可靠性与可追溯性，而非纯启发式

---

## Status | 状态

Production-ready.
All features implemented, verified, and documented.

已完成实现、测试与对账，可安全部署。
