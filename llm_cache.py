"""SQLite cache for every LLM / embedding call.

Key = sha256(provider | model | system | user | temperature | seed | max_tokens).
The cache is the reproducibility backbone: identical requests never cost time or
quota twice, and every stored row records what was actually sent.

Run:  python -c "import llm_cache; print(llm_cache.Cache().stats())"
"""
import hashlib, json, os, sqlite3, time

DEFAULT_PATH = os.path.join("results", "llm_cache.sqlite3")

SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    cache_key   TEXT PRIMARY KEY,
    provider    TEXT NOT NULL,
    model       TEXT NOT NULL,
    system      TEXT,
    user        TEXT NOT NULL,
    temperature REAL,
    seed        INTEGER,
    max_tokens  INTEGER,
    response    TEXT,
    latency_s   REAL,
    prompt_tokens   INTEGER,
    completion_tokens INTEGER,
    seed_supported  INTEGER,
    dry_run     INTEGER DEFAULT 0,
    created_at  REAL
);
CREATE INDEX IF NOT EXISTS idx_calls_provider ON calls(provider, model);
CREATE TABLE IF NOT EXISTS usage (
    day     TEXT NOT NULL,
    provider TEXT NOT NULL,
    calls   INTEGER NOT NULL DEFAULT 0,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    PRIMARY KEY (day, provider)
);
"""


def make_key(provider: str, model: str, system: str, user: str,
             temperature, seed, max_tokens) -> str:
    blob = json.dumps([provider, model, system or "", user,
                       temperature, seed, max_tokens], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def today() -> str:
    return time.strftime("%Y-%m-%d")


class Cache:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.executescript(SCHEMA)
        self.con.commit()

    def get(self, key: str):
        row = self.con.execute(
            "SELECT response, latency_s, prompt_tokens, completion_tokens, seed_supported, dry_run "
            "FROM calls WHERE cache_key = ?", (key,)).fetchone()
        if row is None:
            return None
        return {"response": row[0], "latency_s": row[1], "prompt_tokens": row[2],
                "completion_tokens": row[3], "seed_supported": bool(row[4]),
                "dry_run": bool(row[5])}

    def put(self, key, provider, model, system, user, temperature, seed, max_tokens,
            response, latency_s=None, prompt_tokens=None, completion_tokens=None,
            seed_supported=True, dry_run=False):
        self.con.execute(
            "INSERT OR REPLACE INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (key, provider, model, system, user, temperature, seed, max_tokens,
             response, latency_s, prompt_tokens, completion_tokens,
             int(seed_supported), int(dry_run), time.time()))
        self.con.commit()
        self._bump_usage(provider, prompt_tokens or 0, completion_tokens or 0)

    def _bump_usage(self, provider, pt, ct):
        day = today()
        self.con.execute(
            "INSERT INTO usage(day, provider, calls, prompt_tokens, completion_tokens) "
            "VALUES(?,?,1,?,?) ON CONFLICT(day, provider) DO UPDATE SET "
            "calls = calls + 1, prompt_tokens = prompt_tokens + ?, completion_tokens = completion_tokens + ?",
            (day, provider, pt, ct, pt, ct))
        self.con.commit()

    def usage_today(self, provider: str) -> int:
        row = self.con.execute(
            "SELECT calls FROM usage WHERE day = ? AND provider = ?",
            (today(), provider)).fetchone()
        return row[0] if row else 0

    def usage_total(self, provider: str) -> int:
        row = self.con.execute(
            "SELECT COALESCE(SUM(calls),0) FROM usage WHERE provider = ?", (provider,)).fetchone()
        return int(row[0])

    def stats(self):
        c = self.con.execute("SELECT COUNT(*), COUNT(DISTINCT provider), COUNT(DISTINCT model) "
                             "FROM calls").fetchone()
        u = self.con.execute("SELECT COALESCE(SUM(calls),0), COALESCE(SUM(prompt_tokens),0), "
                             "COALESCE(SUM(completion_tokens),0) FROM usage").fetchone()
        return {"cached_calls": c[0], "providers": c[1], "models": c[2],
                "total_calls": u[0], "prompt_tokens": u[1], "completion_tokens": u[2]}
