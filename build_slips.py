"""Build the Phase-3 enriched slip pool on DEV secrets only.

One row = one candidate slip note for one registered secret, labelled by the
frozen gateway (threshold 0.78, lexical 0.60) as slip (1) or caught (0).

Design notes (match PREREG.md §1 H3):
  * DEV only. TEST secrets are never read by this script; they stay untouched
    until the frozen evaluation run.
  * Per-secret registry: the gateway is tested against the exact secret text
    and subject ident before any note is filtered, so the pool measures "does
    the gateway catch this specific secret's leaks", not a generic block.
  * Attack notes, not just paraphrases: corpus paraphrases + abbreviation +
    vague + hard negatives + a few deterministic lexical variants, so the pool
    has graded difficulty rather than only the 4 corpus paraphrases.
  * Deterministic, checkpointed: one JSONL row per (secret_id, note_sha); the
    script skips rows already written and resumes by reading the existing file.
    If it is killed mid-secret, re-running completes the rest.
  * No TEST slip is spent here. slip_target_n in config.yaml is the target for
    the later frozen evaluation; this script builds the DEV pool from which
    samples will later be drawn.

Run:
  python build_slips.py                 # DEV secrets only, writes results/slip_pool_dev.jsonl

Prerequisites: Ollama running with nomic-embed-text (the gateway's L2 cosine
rule uses it). Embeddings are cached to results/embed_cache_slips.jsonl.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

CORPUS = "corpus/secrets_corpus.json"
SPLITS = "corpus/splits.json"
OUT = "results/slip_pool_dev.jsonl"
CFG_THRESHOLD = 0.78
CFG_LEXICAL = 0.60

_SPLIT = re.compile(r"(?<=[.!?])\s+")


# --------------------------------------------------------------------------- load corpus / splits
def load_splits():
    s = json.load(open(SPLITS, encoding="utf-8"))
    return set(s["semantic"]["dev"]), set(s["identifier"]["dev"])


def load_corpus():
    return json.load(open(CORPUS, encoding="utf-8"))["records"]


def dev_secrets(records, dev_semantic, dev_identifier):
    out = []
    for r in records:
        if r["kind"] == "semantic" and r["id"] in dev_semantic:
            out.append(r)
        elif r["kind"] == "identifier" and r["id"] in dev_identifier:
            out.append(r)
    return out


# --------------------------------------------------------------------------- gateway semantics (replica of the frozen L2 gateway)
def sentences(text):
    return [s.strip() for s in _SPLIT.split(text) if s.strip()]


def _words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def lexical_hit(secret_text, note_text, lexical=CFG_LEXICAL):
    sw = _words(secret_text)
    if not sw:
        return False
    for s in sentences(note_text):
        nw = _words(s)
        overlap = sw & nw
        if len(overlap) / len(sw) >= lexical or len(overlap) >= 1:
            return True
    return False


class EmbedCache:
    """Persistent embedding cache for the local nomic-embed-text model.

    Keyed by the exact text sent to the embedder. Stored in a JSONL file so a
    kill/resume does not re-embed the same sentence twice.
    """

    def __init__(self, path="results/embed_cache_slips.jsonl"):
        self.path = Path(path)
        self._mem = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._mem[r["text"]] = r["vec"]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            for text, vec in self._mem.items():
                f.write(json.dumps({"text": text, "vec": vec}) + "\n")
        self._mem.clear()

    def embed(self, text, model="nomic-embed-text", url="http://localhost:11434/api/embed"):
        if text in self._mem:
            return self._mem[text]
        try:
            resp = requests.post(url, json={"model": model, "input": [text]}, timeout=120)
        except Exception as e:
            sys.exit(f"embedder unreachable ({url}): {e}")
        if resp.status_code != 200:
            sys.exit(f"embedder returned {resp.status_code}: {resp.text[:300]}")
        vec = resp.json()["embeddings"][0]
        self._mem[text] = vec
        return vec

    def embed_many(self, texts, model="nomic-embed-text", url="http://localhost:11434/api/embed", batch=64):
        out = []
        batch = max(1, int(batch))
        for i in range(0, len(texts), batch):
            chunk = [t for t in texts[i:i + batch] if t not in self._mem]
            if not chunk:
                out.extend([self._mem[t] for t in texts[i:i + batch]])
                continue
            try:
                resp = requests.post(url, json={"model": model, "input": chunk}, timeout=180)
            except Exception as e:
                sys.exit(f"embedder batch unreachable: {e}")
            if resp.status_code != 200:
                sys.exit(f"embedder batch returned {resp.status_code}: {resp.text[:300]}")
            for t, v in zip(chunk, resp.json()["embeddings"]):
                self._mem[t] = v
            if (i // batch) % 10 == 0:
                print(f"   embedded {min(i + len(chunk), len(texts))}/{len(texts)} sentences", flush=True)
        for t in texts:
            out.append(self._mem[t])
        return out


def cosine(a, b):
    n = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return n / (na * nb)


def l2_passes(secret_text, note_text, emb, threshold=CFG_THRESHOLD):
    """Return True if the gateway would NOT redact this note via the L2 cosine rule.

    Replicates the gateway's sentence-level cosine rule: if any sentence's cosine
    to the secret is >= threshold, the note is redacted.
    """
    svecs = emb.embed_many(sentences(note_text))
    secret_vec = emb.embed(secret_text)
    for v in svecs:
        if cosine(v, secret_vec) >= threshold:
            return False
    return True


def gateway_filters(secret_text, note_text, emb, lexical=CFG_LEXICAL, threshold=CFG_THRESHOLD):
    """Return (filtered, l1_hit, l2_hit) replicating the frozen L2 gateway.

    The lexical branch is the secret-content-word overlap rule; the cosine branch
    is the sentence-level nomic-embed cosine rule. A note is filtered if either hits.
    """
    l1 = lexical_hit(secret_text, note_text, lexical=lexical)
    l2 = not l2_passes(secret_text, note_text, emb)
    return (l1 or l2), l1, l2


# --------------------------------------------------------------------------- note construction
def notes_for_secret(r):
    """Yield (note_text, hint) tuples for one secret.

    hint is descriptive only; the slip/0 label comes from the gateway. We include
    corpus paraphrases + abbreviation + vague + hard negatives + a few deterministic
    lexical variants so the pool has graded difficulty.
    """
    ident = r.get("ident", "")
    text = r["text"]
    kind = r["kind"]

    for p in r.get("paraphrases", []):
        yield p, "paraphrase"

    if r.get("abbr"):
        yield r["abbr"], "abbr"
    if r.get("vague"):
        yield r["vague"], "vague"

    for h in r.get("hard_negatives", []):
        yield h, "hard_negative"

    if kind == "semantic":
        yield from _lexical_variants(text, ident)

    if kind == "identifier":
        token = _id_token(ident) if ident else ""
        if token:
            yield f"The record is CASE-{token}.", "id_exact"
            yield f"ticket id case{token.lower()} attached.", "id_lower_nohyphen"
            yield f"id: {token[:4]} {token[4:]}.", "id_split"
            yield f"ref {token[::-1]}.", "id_reversed"
            yield "Handoff summary. Please continue with the refund request.", "no_subject"


def _id_token(ident):
    return re.sub(r"[^a-z0-9]", "", ident.lower())


def _lexical_variants(text, ident):
    """Deterministic lightweight surface variants of a semantic secret sentence."""
    base = text.lower()
    ident_lc = _id_token(ident) if ident else ""
    if "renal" in base or "kidney" in base:
        yield f"patient {ident_lc} was diagnosed with stage-2 renal failure."
        yield f"The individual {ident_lc} has kidney failure, second stage."
        yield f"{ident_lc} has stage two kidney failure."
    else:
        yield f"{ident_lc} has a serious long-term condition."
        yield f"{ident_lc}: confidential."


# --------------------------------------------------------------------------- main build
def resume_index(path):
    seen = set()
    if not os.path.exists(path):
        return seen
    for line in open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        seen.add((r.get("secret_id"), r.get("note_sha")))
    return seen


def build_slip_pool(args):
    dev_semantic, dev_identifier = load_splits()
    records = load_corpus()
    secrets = dev_secrets(records, dev_semantic, dev_identifier)
    print(f"DEV secrets to process: {len(secrets)} "
          f"(semantic {sum(1 for r in secrets if r['kind']=='semantic')}, "
          f"identifier {sum(1 for r in secrets if r['kind']=='identifier')})")

    emb = EmbedCache()
    seen = resume_index(OUT)
    written = 0
    slips = 0
    caught = 0
    false_positives = 0

    corpus_hash = json.load(open(SPLITS, encoding="utf-8")).get("corpus_sha256", "")

    for r in secrets:
        secret_id = r["id"]
        secret_text = r["text"]
        kind = r["kind"]
        secret_rows = 0
        for note, hint in notes_for_secret(r):
            note_sha = hashlib.sha256(note.encode()).hexdigest()[:16]
            if (secret_id, note_sha) in seen:
                continue
            filtered, l1, l2 = gateway_filters(secret_text, note, emb)
            slip = 1 if not filtered else 0
            if slip:
                slips += 1
            else:
                caught += 1
            if hint in ("hard_negative", "no_subject") and slip:
                false_positives += 1
            row = {
                "secret_id": secret_id,
                "secret_text": secret_text,
                "kind": kind,
                "note": note,
                "note_hint": hint,
                "note_sha": note_sha,
                "gateway_filtered": int(filtered),
                "l1_hit": int(l1),
                "l2_hit": int(l2),
                "slip": slip,
                "threshold": CFG_THRESHOLD,
                "lexical": CFG_LEXICAL,
                "corpus_sha256": corpus_hash,
                "built": time.time(),
            }
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
            secret_rows += 1
            if written % 50 == 0:
                emb.save()
                print(f"   ...{written} rows written, {slips} slips, {caught} caught, {false_positives} FP", flush=True)
        emb.save()
        if secret_rows:
            nsl = sum(1 for row in open(OUT, encoding="utf-8")
                      if json.loads(row).get("secret_id") == secret_id and json.loads(row).get("slip"))
            print(f"secret {secret_id}: {secret_rows} notes, {nsl} slips", flush=True)

    emb.save()
    print(f"\nbuilt {written} slip-pool rows on DEV: {slips} slips, {caught} caught, {false_positives} false positives")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--step", default="pool", help="pool | hop2")
    args = p.parse_args()
    if args.step not in ("pool", "hop2"):
        sys.exit("step must be pool or hop2")
    build_slip_pool(args)
