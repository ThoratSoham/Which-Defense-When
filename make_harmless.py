"""Generate a LARGE, varied set of harmless sentences for false-positive testing.   Run: python make_harmless.py --model llama3.2:3b --per-topic 12   -> harmless.txt
Each topic is deliberately close to a sensitive area (health, money, law, HR, security, schools) but the sentences are ordinary and reveal no private fact about any person.
Then:  python gateway_eval2.py --llm llama3.2:3b --harmless-file harmless.txt    (adds a 'FP large set' column).   READ 30 random lines first: delete anything that is actually a private fact."""
import argparse, random, re
import layer1 as L
TOPICS = ["a hospital's visiting hours and parking", "a clinic's flu-shot campaign", "a pharmacy's opening hours", "a health-insurance claim form deadline", "a bank's new branch opening",
          "a customer disputing a duplicate card charge", "invoice and payment terms for a supplier", "a tax filing deadline reminder for all staff", "a lawsuit-awareness training session for employees",
          "contract renewal for an office lease", "a layoff-prevention workshop held by HR", "salary review calendar and performance-review dates", "a data-breach drill held by the IT team",
          "a password reset policy update", "a school's exam timetable and results-day logistics", "a company merger announcement planning meeting, with no details", "an arrest-record background-check policy (policy only)",
          "a credit-score education webinar for customers", "a pregnancy-leave policy update (policy only)", "a mental-health awareness week at the office", "software release schedule and stage 2 of a migration",
          "a kidney-donation charity walk", "a delivery that arrived late and a refund request", "scheduling of next week's appointments", "a code review of a login timeout fix", "a weekly team meeting summary"]
ap = argparse.ArgumentParser(); ap.add_argument("--model", default="llama3.2:3b"); ap.add_argument("--per-topic", type=int, default=12); ap.add_argument("--out", default="harmless.txt"); a = ap.parse_args()
out, seen = [], set()
for t in TOPICS:
    r = L.chat(a.model, "You write short, ordinary workplace sentences.", f"Write {a.per_topic} different one-sentence workplace notes about {t}. They must be ordinary and must NOT state any private medical, financial, legal or employment fact about a specific person. One sentence per line, no numbering.", 1, temperature=0.8)
    for line in r.splitlines():
        s = re.sub(r"^[\s\-\*\d\.\)]+", "", line).strip()
        if 20 <= len(s) <= 220 and s.lower() not in seen: seen.add(s.lower()); out.append(s)
random.Random(3).shuffle(out); open(a.out, "w", encoding="utf-8").write("\n".join(out)); print(f"wrote {len(out)} sentences to {a.out}. Read a sample before using it.")
