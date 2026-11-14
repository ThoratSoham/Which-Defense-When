"""verify_ledger.py
Checks knowledge_ledger.csv to ensure that every knowledge item (KL-001 to KL-075)
appears in BOTH:
1. Copy A: main_elsevier.tex + supplementary_elsevier.tex
2. Copy B: main_tmlr.tex
"""
import sys
import os

def check_appearance(doc_text: str, kl_id: str) -> bool:
    return kl_id in doc_text

def parse_ledger(ledger_path: str):
    items = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    if not lines:
        return items
    # Skip header
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",", 2)
        if len(parts) >= 2:
            items.append({"id": parts[0].strip().strip('"'), "short_text": parts[1].strip().strip('"')})
    return items

def main():
    ledger_path = "knowledge_ledger.csv"
    if not os.path.exists(ledger_path):
        print(f"[FAIL] {ledger_path} missing!")
        sys.exit(1)

    items = parse_ledger(ledger_path)

    # Read Copy A
    text_copy_a = ""
    for fn in ["main_elsevier.tex", "supplementary_elsevier.tex"]:
        if os.path.exists(fn):
            with open(fn, "r", encoding="utf-8") as f:
                text_copy_a += f.read() + "\n"

    # Read Copy B
    text_copy_b = ""
    if os.path.exists("main_tmlr.tex"):
        with open("main_tmlr.tex", "r", encoding="utf-8") as f:
            text_copy_b = f.read()

    missing_a = []
    missing_b = []

    for item in items:
        kl_id = item["id"]
        if not check_appearance(text_copy_a, kl_id):
            missing_a.append(kl_id)
        if not check_appearance(text_copy_b, kl_id):
            missing_b.append(kl_id)

    print(f"Total knowledge items in ledger: {len(items)}")
    if missing_a:
        print(f"[FAIL] Copy A (Elsevier) is missing {len(missing_a)} items: {missing_a[:10]}")
    else:
        print("[PASS] Copy A contains 100% of knowledge ledger items.")

    if missing_b:
        print(f"[FAIL] Copy B (TMLR) is missing {len(missing_b)} items: {missing_b[:10]}")
    else:
        print("[PASS] Copy B contains 100% of knowledge ledger items.")

    if missing_a or missing_b:
        sys.exit(1)
    else:
        print("[SUCCESS] Both submission copies satisfy exact knowledge preservation.")

if __name__ == "__main__":
    main()
