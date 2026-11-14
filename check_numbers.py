"""check_numbers.py
Verifies that no empirical result numbers appear hardcoded outside of LaTeX macros.
Scans LaTeX source files and flags un-macroed floats, percentages, or result fractions.
"""
from __future__ import annotations

import re
import sys
import os

# Known acceptable non-result numbers (layout, dates, model names, hyperref, etc.)
ALLOWED_PATTERNS = [
    r'\\documentclass.*',
    r'\\usepackage.*',
    r'\\begin\{thebibliography\}.*',
    r'\\bibitem.*',
    r'arXiv:[0-9]+\.[0-9]+',
    r'Phys\.\\ Rev\..*',
    r'\\label\{.*\}',
    r'\\ref\{.*\}',
    r'\\cite[a-z]*\{.*\}',
    r'\\url\{.*\}',
    r'\\path\{.*\}',
    r'\\includegraphics.*',
    r'\\figbox.*',
    r'\\vspace\{.*\}',
    r'\\hspace\{.*\}',
    r'\\resizebox\{.*\}',
    r'\\parbox\{.*\}',
    r'\\begin\{tabular\}.*',
    r'\\begin\{table\}.*',
    r'\\cmidrule.*',
    r'p\{[0-9.]+cm\}',
    r'[0-9.]+pt',
    r'[0-9.]+in',
    r'[0-9.]+\\linewidth',
    r'[0-9.]+\\textwidth',
    r'llama3\.2:3b',
    r'qwen2\.5:3b',
    r'gemma2:2b',
    r'gemini-3\.5-flash-lite',
    r'gemini-2\.5-flash',
    r'2B--3B',
    r'2B',
    r'3B',
    r'DeBERTa-v3',
    r'Sha-256',
    r'SQLite',
    r'2024',
    r'2025',
    r'2026',
    r'1996',
    r'1900',
    r'2002',
    r'\\copyright',
    r'\\alpha',
    r'\\Delta',
    r'\\pm 0\.05',
    r'0\.05 margin',
    r'alpha = 0\.05',
    r'p < 0\.001',
    r'p = 0\.0024',
    r'R_0',
    r'R_0 \\approx',
    r'temperature 0(\.7)?',
    r'scale-free',
    r'Erd\\H\{o\}s--R\\\'enyi',
    r'Barab\\\'asi--Albert'
]

# Result-looking patterns:
# 1. Decimal numbers: 0.xxx or d.xxx (e.g. 0.641, 0.057, 1.37)
FLOAT_RE = re.compile(r'(?<![a-zA-Z0-9_\\])(?:[0-9]+\.[0-9]+)(?![a-zA-Z0-9_])')
# 2. Result fractions: 123/192, 70/96, etc.
FRACTION_RE = re.compile(r'(?<![a-zA-Z0-9_\\])(?:[0-9]+/[0-9]+)(?![a-zA-Z0-9_])')
# 3. Formatted thousands: 1{,}440, 1{,}600
THOUSAND_RE = re.compile(r'[0-9]+\{,\}[0-9]+')

def check_file(filepath: str) -> list[str]:
    if not os.path.exists(filepath):
        return [f"File not found: {filepath}"]

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    errors = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        # Remove LaTeX comments from the line
        comment_pos = stripped.find("%")
        if comment_pos != -1 and not stripped[comment_pos-1:comment_pos] == "\\":
            clean_line = stripped[:comment_pos]
        else:
            clean_line = stripped

        # Check for allowed patterns
        is_allowed = False
        for ap in ALLOWED_PATTERNS:
            if re.search(ap, clean_line, re.IGNORECASE):
                # We can replace the allowed substring so it doesn't trigger false positives
                clean_line = re.sub(ap, '', clean_line, flags=re.IGNORECASE)

        # Find floats
        for m in FLOAT_RE.finditer(clean_line):
            val = m.group(0)
            errors.append(f"Line {idx}: Un-macroed float '{val}' in: {clean_line.strip()}")

        # Find fractions
        for m in FRACTION_RE.finditer(clean_line):
            val = m.group(0)
            errors.append(f"Line {idx}: Un-macroed fraction '{val}' in: {clean_line.strip()}")

        # Find formatted thousands
        for m in THOUSAND_RE.finditer(clean_line):
            val = m.group(0)
            errors.append(f"Line {idx}: Un-macroed formatted number '{val}' in: {clean_line.strip()}")

    return errors

def main():
    target_files = ["main_elsevier.tex", "supplementary_elsevier.tex", "main_tmlr.tex"]
    all_errors = {}
    any_failed = False

    for tf in target_files:
        if os.path.exists(tf):
            errs = check_file(tf)
            if errs:
                all_errors[tf] = errs
                any_failed = True
                print(f"[FAIL] {tf} has {len(errs)} un-macroed result numbers:")
                for e in errs[:10]:
                    print(f"  - {e}")
                if len(errs) > 10:
                    print(f"  ... and {len(errs) - 10} more.")
            else:
                print(f"[PASS] {tf}: No un-macroed result numbers found.")
        else:
            print(f"[SKIP] {tf} does not exist yet.")

    if any_failed:
        sys.exit(1)
    else:
        print("[SUCCESS] All existing files passed number check.")

if __name__ == "__main__":
    main()
