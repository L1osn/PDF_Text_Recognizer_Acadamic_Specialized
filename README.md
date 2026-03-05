

# PDF Text Recognizer Pro

A desktop application for **PDF text extraction, font-aware layout analysis, and citation detection**, designed for academic and technical documents.

---
## Features 

### Core Capabilities

* Text extraction with exact span-to-PDF coordinate mapping
* Font-aware layout analysis (font name, size, style)
* Superscript & bracket citation detection engine
* Bibliography parsing with false-positive suppression
* Modern GUI with synchronized PDF/Text views

---

## Citation Engine Design 

### Detection Channels 

* **Superscript channel**: geometric + font-size based detection
* **Bracket channel**: `[n]`, `(n)` style inline citations

### Bibliography Handling 

* Strict line-head ID matching (`^\s*(\[(\d+)\]|(\d+)\.)`)
* Year-number filtering (1900–2099) to prevent ID pollution
* `max_id_multiplier` false-citation upper bound

### Soft Constraint System 

* When bibliography is reliable (≥ N entries), unlinked citations are **penalized but not discarded**
* Small or missing bibliographies automatically disable penalties

---

## Architecture |

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
* Background tasks are cancelable via job-id invalidation
* Image rendering uses LRU cache to cap memory usage

---

## Reliability & Safety 

* Thread-safe background execution (no Tk access in workers)
* Job ID mechanism prevents stale callbacks from overwriting state
* PDF handle caching with guaranteed release on exit/errors
* Debug reports never include raw document text

---

## Build & Run

### Run from source

```bash
python app_gui.py
```

### Windows executable

* Prebuilt executable: `dist_exe/PDFTextRecognizer.exe`
* No Python environment required

---

## Testing & Verification

Included test scripts:

* `test_citation_improvements.py` – citation logic validation
* `reconciliation_check.py` – configuration & import-path verification

All tests must pass before deployment.

---

## Scope & Non-Goals 

* Not intended for OCR (scanned PDFs)
* Not a reference manager or citation formatter
* Focused on **structural correctness and traceability**, not heuristics-only extraction

---


## License

MIT LICENSE

