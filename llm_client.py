"""Provider-agnostic LLM client (Ollama + free API tiers).

Features required by the study protocol:
  * keys read from `.env` (never printed, never logged, never committed)
  * rate limiter whose limits come from `config.yaml` — nothing hard-coded
  * exponential backoff with jitter on 429/5xx/network errors
  * per-day quota tracker: when a provider's daily budget is exhausted the client
    raises QuotaExhausted so the job runner checkpoints and can resume next day
  * full caching (llm_cache.Cache) keyed by provider/model/prompt/temperature/seed
  * dry-run mode: no network, deterministic placeholder text, rows marked dry_run

Model strings:
  "llama3.2:3b"                    -> local Ollama
  "ollama:qwen2.5:7b"              -> local Ollama (explicit)
  "openrouter:provider/model:id"   -> OpenRouter (":free" variants allowed)
  "google:gemini-3.8-flash"        -> Gemini via the OpenAI-compatible endpoint

API models may not honour `seed`; the cache row records `seed_supported` per call
so transcripts can state honestly that a seed was sent but not guaranteed.
"""
import json, os, random, time
import requests
import llm_cache

API_PROVIDERS = {"openrouter", "google"}     # OpenAI-compatible HTTP APIs


class QuotaExhausted(RuntimeError):
    def __init__(self, provider, limit, reset_hint=""):
        self.provider, self.limit, self.reset_hint = provider, limit, reset_hint
        super().__init__(f"{provider}: daily quota exhausted ({limit} calls); "
                         f"checkpoint and resume {reset_hint}")


def load_dotenv(path=".env"):
    """Minimal .env loader (no dependency). Missing file -> empty dict."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_config(path="config.yaml"):
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class RateLimiter:
    """Simple token-bucket keyed by provider; limits read from config.yaml."""
    def __init__(self, config):
        self.limits = {}
        for name, p in (config.get("providers") or {}).items():
            rpm = p.get("rpm")
            if rpm:
                self.limits[name] = {"rpm": float(rpm), "min_interval": 60.0 / float(rpm),
                                     "last": 0.0}
        self.ollama_interval = 0.0   # local Ollama: serialized by the caller, no limit

    def wait(self, provider):
        lim = self.limits.get(provider)
        if not lim:
            return 0.0
        now = time.monotonic()
        gap = lim["min_interval"] - (now - lim["last"])
        if gap > 0:
            time.sleep(gap)
        lim["last"] = time.monotonic()
        return max(gap, 0.0)


class LLMClient:
    def __init__(self, config_path="config.yaml", env_path=".env", dry_run=False,
                 cache=None):
        self.cfg = load_config(config_path)
        self.env = {**load_dotenv(env_path), **os.environ}
        self.dry_run = dry_run
        self.cache = cache if cache is not None else llm_cache.Cache(self.cfg["paths"]["cache"])
        self.limiter = RateLimiter(self.cfg)
        self.rl_cfg = self.cfg.get("rate_limit", {})
        self._quota_stopped = set()

    # ---------- quota ----------
    def _daily_limit(self, provider):
        p = (self.cfg.get("providers") or {}).get(provider) or {}
        return p.get("rpd_free") or p.get("rpd")

    def check_quota(self, provider):
        limit = self._daily_limit(provider)
        if not limit:
            return
        used = self.cache.usage_today(provider)
        if used >= limit:
            self._quota_stopped.add(provider)
            raise QuotaExhausted(provider, limit,
                                 "tomorrow 00:00 Pacific (Google) / next UTC day (OpenRouter)")

    # ---------- public API ----------
    def complete(self, model, system, user, temperature=None, seed=None,
                 max_tokens=None, provider=None, refresh=False):
        st = self.cfg["study"]
        temperature = st["temperature"] if temperature is None else temperature
        max_tokens = st["num_predict"] if max_tokens is None else max_tokens
        provider, bare = self._split(model, provider)
        key = llm_cache.make_key(provider, bare, system, user, temperature, seed, max_tokens)

        if not refresh and (hit := self.cache.get(key)) is not None and not self.dry_run:
            return {"text": hit["response"], "cached": True, "provider": provider,
                    "model": bare, "latency_s": hit["latency_s"],
                    "seed_supported": hit["seed_supported"]}

        if self.dry_run:
            text = f"[DRY-RUN] model={bare} prompt_sha={key[:12]}"
            self.cache.put(key, provider, bare, system, user, temperature, seed,
                           max_tokens, text, latency_s=0.0, dry_run=True)
            return {"text": text, "cached": False, "dry_run": True,
                    "provider": provider, "model": bare, "seed_supported": bool(seed)}

        self.check_quota(provider)
        self.limiter.wait(provider)

        t0 = time.time()
        for attempt in range(int(self.rl_cfg.get("backoff_tries", 6))):
            try:
                text, usage, seed_ok = self._dispatch(provider, bare, system, user,
                                                      temperature, seed, max_tokens)
                dt = time.time() - t0
                self.cache.put(key, provider, bare, system, user, temperature, seed,
                               max_tokens, text, latency_s=dt,
                               prompt_tokens=usage.get("prompt"),
                               completion_tokens=usage.get("completion"),
                               seed_supported=seed_ok)
                return {"text": text, "cached": False, "provider": provider,
                        "model": bare, "latency_s": dt, "seed_supported": seed_ok}
            except QuotaExhausted:
                raise
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                if status in (429, 500, 502, 503, 504) or status == 0:
                    self._sleep_backoff(attempt, e, status)
                    continue
                raise
            except (requests.RequestException, ValueError) as e:
                self._sleep_backoff(attempt, e, 0)
                continue
        raise RuntimeError(f"{provider}:{bare} unresponsive after "
                           f"{self.rl_cfg.get('backoff_tries', 6)} tries")

    def embed(self, texts, model=None):
        """Local Ollama embeddings, cached per string (embeddings are model+text keyed)."""
        model = model or self.cfg["ollama"]["embed_model"]
        out, missing, keys = [], [], []
        for t in texts:
            k = llm_cache.make_key("ollama:embed", model, "", t, None, None, None)
            keys.append(k)
            hit = self.cache.get(k)
            if hit:
                out.append(json.loads(hit["response"]))
            else:
                out.append(None); missing.append((k, t))
        if missing and not self.dry_run:
            url = self.cfg["ollama"]["url"] + "/api/embed"
            batch = [t for _, t in missing]
            r = requests.post(url, json={"model": model, "input": batch,
                                         "keep_alive": self.cfg["ollama"]["keep_alive"]},
                              timeout=300)
            r.raise_for_status()
            for (k, t), vec in zip(missing, r.json()["embeddings"]):
                self.cache.put(k, "ollama:embed", model, "", t, None, None, None,
                               json.dumps(vec))
                out[keys.index(k)] = vec
        return out

    # ---------- internals ----------
    def _split(self, model, provider=None):
        if provider:
            return provider, model
        if ":" in model:
            head, tail = model.split(":", 1)
            if head in API_PROVIDERS or head == "ollama":
                return head, tail
        return "ollama", model

    def _sleep_backoff(self, attempt, err, status):
        base = float(self.rl_cfg.get("backoff_base_s", 2.0))
        cap = float(self.rl_cfg.get("backoff_max_s", 300.0))
        if status == 429:
            # Rate limit: honour the provider's reset hint, else back off hard.
            # Free tiers throttle aggressively; short retries just burn the budget.
            base = max(base, float(self.rl_cfg.get("backoff_base_429_s", 15.0)))
            hdr = None
            try:
                hdr = (err.response.headers.get("Retry-After")
                       or err.response.headers.get("X-RateLimit-Reset"))
            except Exception:
                pass
            delay = None
            if hdr:
                try:
                    v = float(hdr)
                    delay = v if v < 1000 else max(0.0, v - time.time())
                except ValueError:
                    delay = None
            delay = max(delay or 0.0, min(cap, base * (2 ** attempt)))
            print(f"    [429] sleeping {delay:.0f}s (attempt {attempt + 1})", flush=True)
        else:
            delay = min(cap, base * (2 ** attempt)) * (0.5 + random.random())
        time.sleep(delay)

    def _dispatch(self, provider, model, system, user, temperature, seed, max_tokens):
        if provider == "ollama":
            return self._ollama(model, system, user, temperature, seed, max_tokens)
        return self._openai_compatible(provider, model, system, user, temperature,
                                       seed, max_tokens)

    def _ollama(self, model, system, user, temperature, seed, max_tokens):
        url = self.cfg["ollama"]["url"] + "/api/chat"
        payload = {"model": model, "stream": False,
                   "keep_alive": self.cfg["ollama"]["keep_alive"],
                   "options": {"temperature": temperature, "seed": seed,
                               "num_predict": max_tokens,
                               "num_ctx": self.cfg["study"]["num_ctx"]},
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        r = requests.post(url, json=payload, timeout=600)
        r.raise_for_status()
        j = r.json()
        if "message" not in j:
            raise requests.HTTPError(f"ollama error: {str(j)[:200]}")
        return (j["message"]["content"] or "",
                {"prompt": j.get("prompt_eval_count"), "completion": j.get("eval_count")},
                True)                                  # Ollama honours seed

    def _openai_compatible(self, provider, model, system, user, temperature, seed,
                           max_tokens):
        p = self.cfg["providers"][provider]
        key_var = p["key_env"]
        key = self.env.get(key_var, "")
        if not key:
            raise RuntimeError(f"{key_var} missing from .env (see docs/FREE_API_SETUP.md)")
        url = p["base_url"] + "/chat/completions"
        supports_seed = p.get("supports_seed", True)
        body = {"model": model, "temperature": temperature, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        if supports_seed:
            body["seed"] = seed
        r = requests.post(url, headers={"Authorization": "Bearer " + key,
                                        "Content-Type": "application/json"},
                          json=body, timeout=180)
        if r.status_code == 429:
            raise requests.HTTPError("rate limited", response=r)
        r.raise_for_status()
        j = r.json()
        if "choices" not in j:
            raise ValueError(str(j)[:300])
        u = j.get("usage", {}) or {}
        # The parameter was sent only when the provider accepts it (config
        # supports_seed); even then determinism is not guaranteed.
        seed_ok = bool(seed) and supports_seed and j.get("seed") is not None
        return (j["choices"][0]["message"].get("content") or "",
                {"prompt": u.get("prompt_tokens"), "completion": u.get("completion_tokens")},
                seed_ok)


if __name__ == "__main__":
    import sys
    c = LLMClient(dry_run="--dry-run" in sys.argv)
    print("cache:", json.dumps(c.cache.stats(), indent=2))
    print("providers configured:", {k: v.get("key_env") for k, v in c.cfg["providers"].items()})
    print("env keys present:", sorted(k for k in ("OPENROUTER_API_KEY", "GOOGLE_API_KEY")
                                      if k in c.env and c.env[k]))
    if "--dry-run" in sys.argv:
        print(c.complete("llama3.2:3b", "sys", "user", seed=1)["text"])
