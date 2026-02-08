"""
Test script to run PDF extraction with citation rejection debugging enabled.

Usage:
    python tests/test_pdf_with_debug.py path/to/your.pdf

This will process the PDF and print a detailed rejection report showing:
- Top 10 rejection reasons with percentages
- First 20 rejected token samples with reasons and locations
"""

import sys
import os

# Fix Unicode encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Pdf_to_text import AcademicPDFRecognizer


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/test_pdf_with_debug.py path/to/your.pdf")
        print("\nThis script processes a PDF with citation rejection debugging enabled.")
        print("It will show you why superscript tokens are being rejected/accepted.")
        return 1
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        return 1
    
    print(f"Processing: {pdf_path}")
    print("=" * 60)
    
    # Create extractor
    extractor = AcademicPDFRecognizer(pdf_path)
    
    # Extract text (progress output)
    print("\nExtracting text...")
    for page_num, spans in extractor.iter_extract_text_with_fonts():
        print(f"  Processed page {page_num} ({len(spans)} spans)")

    # Run NEW citation engine (Phase 1: bracket only)
    print("\nRunning NEW citation engine (Phase 1: bracket only)...")
    entries, debug = extractor.run_citation_engine(enable_superscript=False, debug=True)
    print(debug.summary())

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"\nEngine Results:")
    print(f"  - bib_ids_count: {debug.bib_ids_count}")
    print(f"  - bib_map_count: {debug.bib_map_count}")
    print(f"  - bracket_candidates_count: {debug.bracket_candidates_count}")
    print(f"  - superscript_candidates_count: {debug.superscript_candidates_count}")
    print(f"  - entries_count: {debug.entries_count}")
    print(f"  - total_occurrences: {debug.total_occurrences}")

    # Show accepted citations (new engine entries)
    if entries:
        print(f"\nAccepted Citation IDs ({len(entries)}):")
        ref_ids = [str(e.ref_id) for e in entries[:50]]  # Show first 50
        print(f"  {', '.join(ref_ids)}")
        if len(entries) > 50:
            print(f"  ... and {len(entries) - 50} more")
    
    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
