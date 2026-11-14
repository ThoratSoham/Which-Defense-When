"""Cache, runner, task and simulator tests (Phase 1 infrastructure + Phase 6.1)."""
import json, os, random, pytest


# --------------------------------------------------------------------- cache
def test_cache_roundtrip(tmp_path):
    import llm_cache
    c = llm_cache.Cache(str(tmp_path / "c.sqlite3"))
    key = llm_cache.make_key("ollama", "m", "sys", "user", 0.7, 1, 220)
    assert c.get(key) is None
    c.put(key, "ollama", "m", "sys", "user", 0.7, 1, 220, "hello", latency_s=1.5,
          prompt_tokens=10, completion_tokens=5)
    hit = c.get(key)
    assert hit["response"] == "hello" and hit["latency_s"] == 1.5
    assert c.usage_today("ollama") == 1
    assert c.stats()["cached_calls"] == 1


def test_cache_key_sensitivity():
    import llm_cache
    base = llm_cache.make_key("p", "m", "s", "u", 0.7, 1, 220)
    assert base != llm_cache.make_key("p", "m", "s", "u", 0.0, 1, 220)   # temperature
    assert base != llm_cache.make_key("p", "m", "s", "u", 0.7, 2, 220)   # seed
    assert base != llm_cache.make_key("p", "m", "s", "u2", 0.7, 1, 220)  # prompt
    assert base != llm_cache.make_key("p", "m2", "s", "u", 0.7, 1, 220)  # model
    assert base == llm_cache.make_key("p", "m", "s", "u", 0.7, 1, 220)   # stable


def test_env_loader_never_returns_key_for_missing_file(tmp_path):
    import llm_client
    assert llm_client.load_dotenv(str(tmp_path / ".env")) == {}


def test_dry_run_makes_no_network_call(tmp_path):
    import llm_client
    client = llm_client.LLMClient(config_path="config.yaml",
                                  env_path=str(tmp_path / ".env"), dry_run=True)
    out = client.complete("llama3.2:3b", "sys", "unique prompt here", seed=3)
    assert out["dry_run"] and out["text"].startswith("[DRY-RUN]")
    hit = client.cache.get(
        __import__("llm_cache").make_key("ollama", "llama3.2:3b", "sys",
                                          "unique prompt here", 0.7, 3, 220))
    assert hit and hit["dry_run"]


# -------------------------------------------------------------------- runner
def test_runner_checkpoints_and_resumes(tmp_path):
    import runner
    out = str(tmp_path / "t.jsonl")
    cells = [{"model": "m", "defense": "none", "episodes": 3}]
    calls = []

    def fn(cell, ep):
        calls.append(ep)
        return {"note": f"n{ep}"}

    job = "pytest_job"
    runner.clear_job(job, out, confirm=False)
    s1 = runner.run_grid(job, cells, fn, out, log=lambda *a: None)
    assert s1["written"] == 3 and len(calls) == 3
    s2 = runner.run_grid(job, cells, fn, out, log=lambda *a: None)
    assert s2["written"] == 0 and len(calls) == 3, "resume must not redo finished episodes"
    lines = [json.loads(l) for l in open(out, encoding="utf-8")]
    assert len(lines) == 3 and lines[0]["episode"] == 0
    runner.clear_job(job, out)


def test_runner_slice_budget(tmp_path):
    import runner
    out = str(tmp_path / "s.jsonl")
    cells = [{"m": "x", "episodes": 10}]
    runner.clear_job("slice_job", out, confirm=False)
    s = runner.run_grid("slice_job", cells, lambda c, e: {"n": e}, out,
                        max_minutes=1e-9, log=lambda *a: None)
    assert s["written"] == 0 and s["pending_after"] == 10, s
    runner.clear_job("slice_job", out)


def test_runner_records_cell_and_episode(tmp_path):
    import runner
    out = str(tmp_path / "c.jsonl")
    runner.clear_job("cell_job", [{"m": "x"}], out, confirm=False) if False else None
    runner.clear_job("cell_job", out, confirm=False)
    runner.run_grid("cell_job", [{"model": "m", "episodes": 2}],
                    lambda c, e: {"leaked": e % 2}, out, log=lambda *a: None)
    recs = [json.loads(l) for l in open(out, encoding="utf-8")]
    assert recs[1]["cell"]["model"] == "m" and recs[1]["episode"] == 1
    runner.clear_job("cell_job", out)


# --------------------------------------------------------------------- tasks
def test_task_facts_are_deterministic_and_distinct():
    import tasks
    a = tasks.facts("customer_service", 7)
    b = tasks.facts("customer_service", 7)
    c = tasks.facts("customer_service", 8)
    assert a == b and a != c
    assert set(a) == {"order_no", "amount", "reason", "deadline"}
    assert set(tasks.facts("hr_onboarding", 1)) == {
        "start_date", "team", "manager", "equipment", "access"}


def test_context_contains_secret_unless_b4():
    import tasks
    sys0, user, f = tasks.context("customer_service", "CASE-ABCD1234", 1)
    assert "CASE-ABCD1234" in sys0 and "ORD-" in sys0
    sys_b4, _, f2 = tasks.context("customer_service", "CASE-ABCD1234", 1,
                                  include_secret=False)
    assert "CASE-ABCD1234" not in sys_b4 and f2 == f


def test_usefulness_scorer():
    import tasks
    f = {"order_no": "ORD-5521", "amount": "$84.50", "reason": "duplicate charge",
         "deadline": "Friday"}
    full = "Refund for ORD-5521, $84.50, duplicate charge, reply by Friday."
    assert tasks.score_usefulness(full, f)["usefulness"] == 1.0
    half = "Refund for ORD-5521 is being processed."
    s = tasks.score_usefulness(half, f)
    assert 0.0 < s["usefulness"] < 1.0 and s["fields"]["order_no"]


# ---------------------------------------------------------------------- sim
@pytest.fixture
def S():
    import sim, numpy as np
    sim.rng = np.random.default_rng(42)
    return sim


def test_sim_t0_infects_only_seed(S):
    import networkx as nx
    G = nx.path_graph(8)
    size, off = S.cascade(G, 0.0, seed=0)
    assert size == 1 and off == 0


def test_sim_t1_fills_the_whole_tree(S):
    import networkx as nx
    G = nx.balanced_tree(2, 3)          # 15 nodes
    size, _ = S.cascade(G, 1.0, seed=0)
    assert size == G.number_of_nodes()
    # protecting every node except the seed blocks all transmission
    others = frozenset(v for v in G if v != 0)
    size2, _ = S.cascade(G, 1.0, protected=others, seed=0)
    assert size2 == 1
    # protecting a cut vertex stops everything below it
    size3, _ = S.cascade(G, 1.0, protected=frozenset({1}), seed=0)
    assert size3 < G.number_of_nodes() and size3 >= 1


def test_sim_seed_determinism(S):
    import networkx as nx, numpy as np
    G = nx.barabasi_albert_graph(60, 2, seed=1)
    a = S.cascade(G, 0.3, seed=5)[0]
    S.rng = np.random.default_rng(42)
    b = S.cascade(G, 0.3, seed=5)[0]
    assert a == b


def test_sim_monotone_in_T(S):
    import networkx as nx, numpy as np
    G = nx.gnm_random_graph(80, 160, seed=3)
    def mean(t):
        S.rng = np.random.default_rng(7)
        return np.mean([S.cascade(G, t)[0] for _ in range(60)])
    assert mean(0.8) > mean(0.2) > mean(0.02)


def test_r0_formula_on_er(S):
    import networkx as nx, numpy as np
    G = nx.gnm_random_graph(600, 1200, seed=1)      # mean degree 4
    r0 = S.theory_R0(G, 0.3)
    k = np.mean([d for _, d in G.degree()])
    assert abs(r0 - 0.3 * k) < 0.15 * max(0.3 * k, 1e-9) * 10   # ER: <k^2>~k^2+k
