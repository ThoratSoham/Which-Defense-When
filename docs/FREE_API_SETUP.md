# Free API setup — Google AI Studio (Gemini) and OpenRouter

Researched 2026-10-25 from the providers' **own documentation** (links at every number). You
told me you already have an OpenRouter key and a Google AI Studio key — so §1 and §2 are here to
verify what you have, and §3 is what matters: where the keys go and what the limits actually are.

> **Data note (please read):** every string we send is **synthetic** — invented case IDs,
> invented patients, invented tickets. Nothing real is transmitted. Even so, note the difference
> in provider terms: on Google's **free (unpaid) tier** submitted content and responses *may be
> used to improve Google's models and may be reviewed by humans*, and Google documents **no
> opt-out for the unpaid tier** (the documented opt-out is moving to a billed project). See
> [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms) and
> [Pricing](https://ai.google.dev/gemini-api/docs/pricing). OpenRouter's `:free` variants are
> free endpoints offered by third-party providers; see their
> [limits](https://openrouter.ai/docs/api_reference/limits). Since the data is synthetic and
> non-personal, this is acceptable for our study — but it is your call, and the paper will state
> that API models saw only synthetic data.

---

## 1. Google AI Studio (Gemini)

**Key page:** <https://aistudio.google.com/api-keys>
(Docs: [API key](https://ai.google.dev/gemini-api/docs/api-key) ·
[Getting started](https://ai.google.dev/gemini-api/docs/get-started))

1. Sign in at <https://aistudio.google.com>.
2. Open **Dashboard → API Keys** (direct: <https://aistudio.google.com/api-keys>).
3. Click **Create API key**, pick the default project (or **Dashboard → Projects → Import
   projects** first if your project is missing), confirm.
4. Copy the key **once** — Google warns keys are shown only at creation. Paste it into this
   project's `.env` as `GOOGLE_API_KEY=...` (never into chat, never into git).
   *Google notes that since 2026-05-28 new AI Studio keys are created as authorization keys by
   default — that is normal, it still works as the API key.*

### Free-tier models (verbatim IDs from Google's pricing page)
Verified as listed with free inference on [Pricing](https://ai.google.dev/gemini-api/docs/pricing):
`gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`,
`gemini-3-flash-preview`, plus live/audio/transcribe/TTS variants we do **not** need.

Explicitly **not** free (verified): `gemini-4-argon`, `gemini-3.1-pro-preview`,
`gemini-3.1-flash-image`, `gemini-3-pro-image`. `gemini-2.0-flash` / `gemini-2.0-flash-lite` are
listed as **shut down**. Google also states access to the `gemini-2.5-*` family is restricted to
users who have actively used them before — do **not** plan around 2.5 IDs.

**Not verifiable from the docs:** an exhaustive free/paid inventory. Confirm against your own
dashboard before pinning a model in the preregistration.

### Rate limits — Google publishes no fixed numbers here
[Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) says free-tier RPM / TPM / RPD
**vary by model, usage tier and account**, are not guaranteed, and must be read from
<https://aistudio.google.com/rate-limit>. Limits are **per project**, not per key. RPD quotas
reset at **midnight Pacific**. **Action:** open that page once, read the numbers for
`gemini-3.8-flash` (or whichever free model you choose), and write them into
`config/llm.yaml` — the rate limiter reads them from config, never hard-coded.

### Endpoint
Gemini-native: `https://generativelanguage.googleapis.com/v1beta/`.
Google also exposes an **OpenAI-compatible** endpoint at
`https://generativelanguage.googleapis.com/v1beta/openai/`
([docs](https://ai.google.dev/gemini-api/docs/openai)) — we will use this one so a single
OpenAI-style client code path serves both providers.

---

## 2. OpenRouter

**Key page:** <https://openrouter.ai/keys>
(Docs: [quick start](https://openrouter.ai/docs/cookbook/coding-agents/cursor-integration) ·
[create key](https://openrouter.ai/docs/api/api-reference/api-keys/create-a-new-api-key))

1. Sign in at <https://openrouter.ai>.
2. Open **Keys** (<https://openrouter.ai/keys>).
3. **Create key**, copy it once (it is shown only at creation).
4. Put it in `.env` as `OPENROUTER_API_KEY=...`.

### Free models
`:free` is a catalog variant: full ID is `provider/model-name:free`. The live catalog is at
`GET https://openrouter.ai/api/v1/models` — **that, not memory, is the source of truth**, and
slugs come and go. Slugs observed free at the time of writing:
`recursive/flint-v1.0:free`, `xingchen-agi/xing4.0-29b-a4b:free`. There is also a router
`openrouter/free` that picks a free model for you
([docs](https://openrouter.ai/docs/guides/routing/routers/free-router)).

**Action:** when we set up `llm_client.py`, fetch the models endpoint, filter
`pricing.prompt == "0"` (or `:free` in the id), print the list, and let you pick the largest
frontier-class free model from *today's* catalog. I will not hard-code a slug.

### Rate limits (published)
From [API Credit & Rate Limits](https://openrouter.ai/docs/api_reference/limits) and the
[FAQ](https://openrouter.ai/docs/faq):

| All-time credits purchased | Requests/minute | Requests/day (free models) |
|---|---:|---:|
| below threshold | 20 | **50** |
| ≥ **$10** | 20 | **1 000** |

No tokens-per-day quota is published for free models. Limits are **account-global**, not per
key — extra keys or accounts do not raise them. **50 requests/day without a $10 credit purchase
is the binding constraint for everything we plan**; see §4.

Quota is observable: `GET https://openrouter.ai/api/v1/key` returns
`free_model_daily_requests: {used, limit, remaining}`. Our client polls this before batches.

### Endpoint and parameters
`POST https://openrouter.ai/api/v1/chat/completions`, Bearer auth, OpenAI-compatible.
`temperature` and `seed` are accepted, but OpenRouter only **forwards** parameters the chosen
model supports and explicitly does **not** guarantee determinism
([parameters](https://openrouter.ai/docs/api_reference/parameters)).
**Record in the logs: `seed_supported = true/false` per model — API runs are "seed recorded,
determinism not guaranteed".**

### When the limit is hit
HTTP **429** with body `{"error":{"code":429,"message":"Rate limit exceeded","metadata":
{"error_type":"rate_limit_exceeded"}}}`; platform 429s carry `X-RateLimit-Limit`,
`X-RateLimit-Remaining`, `X-RateLimit-Reset` headers. A 429 can also come from the upstream
provider — check `error.metadata` to tell them apart
([error handling](https://openrouter.ai/docs/api_reference/errors-and-debugging)).
`llm_client.py` will honour `X-RateLimit-Reset`, back off exponentially, and switch to the
"quota exhausted → resume tomorrow" state instead of burning retries.

---

## 3. Where keys live

Create `.env` in the project root (I will also create `.gitignore` containing `.env`):

```
OPENROUTER_API_KEY=...
GOOGLE_API_KEY=...
```

Rules: `.env` is git-ignored, never printed, never pasted into chat, never embedded in logs or
transcripts. Transcript JSONL records only `provider`, `model`, prompt hash, temperature, seed
and response. If a key ever leaks, revoke it from the provider's key page and mint a new one.

---

## 4. Quota planning (how much we can actually run)

| Source | Realistic budget | Use for |
|---|---|---|
| **Gemini free** | unknown until you read <https://aistudio.google.com/rate-limit>; assume a few requests/min and a daily token cap | **(a)** reduced-size replication of the defense ladder + relay measurement; **(b)** the *full-note* LLM judge |
| **OpenRouter free** | 20 req/min, **50 req/day** (or 1 000/day with ≥$10 of credits) | **(b)** judge calls only, unless you choose to buy $10 of credits (your decision, not mine — it buys 20× the daily quota) |

Prioritisation (most important runs first, as instructed):
1. Gemini: defense ladder replication — 4 defenses × 2 pressures × 2 kinds × 20 episodes ×
   3 calls = **480 calls**, then relay measurement (~300 calls).
2. Gemini: LLM-judge pass over the labelled sample and the disagreement set.
3. OpenRouter: a *different-family* judge cross-check on ≤50 notes/day.
4. Anything left over.

If Gemini's dashboard shows a small quota, we fall back to: OpenRouter at 50/day for judge
calls, and the local 3–4 B models for generation. Small n with wide CIs is acceptable — the
paper will report n honestly either way.

---

## 5. Verification steps (I will run these once keys are in `.env`)

1. `python -c "from llm_client import ..."` — dry-run mode, **no request sent, no key printed**.
2. One live 1-token call per provider, logging only: HTTP status, model id, latency, and the
   returned rate-limit headers (never the key).
3. Read back `free_model_daily_requests` for OpenRouter; ask you to read the AI Studio rate
   limit page and paste the numbers (numbers only, not the key) into `config/llm.yaml`.

---

## Sources

- <https://ai.google.dev/gemini-api/docs/api-key>
- <https://ai.google.dev/gemini-api/docs/get-started>
- <https://ai.google.dev/gemini-api/docs/pricing>
- <https://ai.google.dev/gemini-api/docs/rate-limits>
- <https://ai.google.dev/gemini-api/docs/models>
- <https://ai.google.dev/gemini-api/terms>
- <https://ai.google.dev/gemini-api/docs/openai>
- <https://openrouter.ai/docs/cookbook/coding-agents/cursor-integration>
- <https://openrouter.ai/docs/api/api-reference/api-keys/create-a-new-api-key>
- <https://openrouter.ai/docs/api_reference/limits>
- <https://openrouter.ai/docs/faq>
- <https://openrouter.ai/docs/api_reference/parameters>
- <https://openrouter.ai/docs/api_reference/errors-and-debugging>
- <https://openrouter.ai/docs/guides/routing/routers/free-router>
- <https://openrouter.ai/api/v1/models> (live catalog)
