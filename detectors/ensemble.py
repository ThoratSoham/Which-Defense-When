"""Majority-vote ensemble over the detector stack (>=2 of 3 = leak).

Inputs are the per-note detector verdicts; missing/failed detectors are handled
explicitly: if fewer than 2 detectors produced a verdict the ensemble is marked
`undetermined` rather than silently defaulted to 0 (an absent detector is not a
vote for "no leak")."""
import json

DETECTORS = ("d1", "d2", "d3")


def ensemble_vote(verdicts: dict) -> dict:
    """verdicts: {'d1': 0/1, 'd2': 0/1, 'd3': 0/1 or None} -> vote record."""
    votes = {k: verdicts.get(k) for k in DETECTORS}
    present = [v for v in votes.values() if v in (0, 1)]
    if len(present) < 2:
        return {"ensemble": None, "reason": "fewer than 2 detectors voted",
                "votes": votes, "n_voted": len(present)}
    leak = int(sum(present) >= 2)
    return {"ensemble": leak, "votes": votes, "n_voted": len(present),
            "unanimous": int(len(set(present)) == 1)}


def load_rows(path):
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            yield json.loads(line)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        from collections import Counter
        c = Counter()
        for r in load_rows(sys.argv[1]):
            v = ensemble_vote(r.get("verdicts", r))
            c[v["ensemble"]] += 1
        print(dict(c))
