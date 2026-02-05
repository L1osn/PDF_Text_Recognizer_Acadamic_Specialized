"""
PyInstaller build script
Package PDF Text Recognizer into standalone exe file
"""

import PyInstaller.__main__
import os
import sys
import shutil

def build_exe():
    """Build standalone exe"""
    
    output_dir = "dist"
    
    # Clean old build files
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    if os.path.exists("dist_exe"):
        shutil.rmtree("dist_exe")
    
    print("=" * 60)
    print("Building PDF Text Recognizer...")
    print("=" * 60)
    
    # PyInstaller arguments
    args = [
        "app_gui.py",
        "--name=PDFTextRecognizer",  # exe filename (English)
        "--onefile",  # Single file packaging
        "--windowed",  # No console window
        "--distpath=./dist_exe",  # Output directory
        "--specpath=./build_spec",  # spec file directory
        "--workpath=./build",  # Temporary build directory
        "--collect-all=pdfplumber",  # Collect pdfplumber data
        "--collect-all=pyperclip",  # Collect pyperclip
        "--hidden-import=Pdf_to_text",  # Explicitly include Pdf_to_text module
        "--hidden-import=pdfminer",  # Include pdfminer for PDF processing
    ]
    
    # Filter empty strings
    args = [arg for arg in args if arg]
    
    print(f"Build command: {' '.join(args)}")
    print()
    
    # Execute build
    try:
        PyInstaller.__main__.run(args)
        print()
        print("=" * 60)
        print("Build successful!")
        print("=" * 60)
        print(f"Exe location: {os.path.abspath('dist_exe/PDFTextRecognizer.exe')}")
        print()
    except Exception as e:
        print(f"Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_exe()
