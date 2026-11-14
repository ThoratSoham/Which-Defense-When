"""Job 7 (J7): Theory Check and 500-Agent Outbreak Simulation Re-run
Pre-registered in PREREG_v2.md §5.
Compares closed-form floor P_floor = 1 - (1 - T_gw)^k with Monte Carlo simulations on 500-agent networks
under both early exploratory parameters (T_gw = 0.017) and TEST parameters (T_gw = 0.073 and J1).
"""
import json
import math
import numpy as np
import random
import networkx as nx

MASTER_SEED = 20261113

def closed_form_floor(t_gw: float, k: float) -> float:
    return 1.0 - (1.0 - t_gw) ** k

def run_simulation(n=500, runs=200, t_gw=0.073, t_src=0.346, t_slip=0.74, ps=None, seed=MASTER_SEED):
    if ps is None:
        ps = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0]
        
    rng = random.Random(seed)
    # Generate ER and BA topologies
    # ER with <k>=4: n=500, edges=1000
    er = nx.gnm_random_graph(n, 2 * n, seed=seed)
    adj_er = {u: list(er.neighbors(u)) for u in range(n)}
    
    # BA with m=2 (<k>=4)
    ba = nx.barabasi_albert_graph(n, 2, seed=seed)
    adj_ba = {u: list(ba.neighbors(u)) for u in range(n)}
    
    topologies = {"er": adj_er, "ba": adj_ba}
    results = {}
    
    for topo_name, adj in topologies.items():
        results[topo_name] = {}
        # Degrees
        degrees = [len(adj[u]) for u in range(n)]
        mean_k = np.mean(degrees)
        
        for strat in ["random", "hub-first"]:
            results[topo_name][strat] = {}
            for p in ps:
                m = int(round(p * n))
                if strat == "random":
                    # Protected set is random sample
                    prot_base = list(range(n))
                else:
                    # Hub-first: sorted by degree descending
                    prot_base = sorted(range(n), key=lambda u: len(adj[u]), reverse=True)
                    
                outbreak_counts = 0
                infected_sizes = []
                
                for r in range(runs):
                    if strat == "random":
                        prot_set = set(rng.sample(prot_base, m))
                    else:
                        prot_set = set(prot_base[:m])
                        
                    # Source agent chosen uniformly
                    s = rng.randrange(n)
                    
                    # Run epidemic spread (slip model: once a secret slips, downstream gateways pass at t_slip)
                    infected = {s: False} # node -> whether it received an unmasked slip
                    frontier = [s]
                    
                    while frontier:
                        nxt = []
                        for u in frontier:
                            u_is_slip = infected[u]
                            # Transmission probability out of u
                            if u == s:
                                p_trans = t_gw if (u in prot_set) else t_src
                                child_slip = (u in prot_set)
                            elif u in prot_set:
                                p_trans = t_slip if u_is_slip else t_gw
                                child_slip = True
                            else:
                                p_trans = t_src
                                child_slip = u_is_slip
                                
                            for v in adj[u]:
                                if v not in infected:
                                    if rng.random() < p_trans:
                                        infected[v] = child_slip
                                        nxt.append(v)
                        frontier = nxt
                        
                    # Outbreak defined as infecting >= 5% of network (25 agents)
                    inf_count = len(infected)
                    infected_sizes.append(inf_count)
                    if inf_count >= 0.05 * n:
                        outbreak_counts += 1
                        
                p_outbreak = outbreak_counts / runs
                mean_size = float(np.mean(infected_sizes))
                results[topo_name][strat][str(p)] = {
                    "p_outbreak": p_outbreak,
                    "mean_infected": mean_size
                }
                
    return results

def main():
    print("=== Running Job 7: Closed-Form Theory vs 500-Agent Simulations ===")
    
    # Compare closed-form floor across degrees and T_gw
    degrees = [2, 3, 4, 6, 8, 12]
    theory_comparison = {}
    
    t_early = 0.017
    t_test = 0.073
    t_d1 = 0.292 # From free-text / D1 range
    
    for k in degrees:
        theory_comparison[f"k={k}"] = {
            "T_early_0.017": round(closed_form_floor(t_early, k), 4),
            "T_test_0.073": round(closed_form_floor(t_test, k), 4),
            "T_d1_0.292": round(closed_form_floor(t_d1, k), 4)
        }
        
    print("Theoretical outbreak floor P_floor = 1 - (1 - T_gw)^k:")
    print(json.dumps(theory_comparison, indent=2))
    
    print("\nRunning 500-agent simulations with TEST parameters (T_gw=0.073, T_src=0.346, runs=200)...")
    sim_test = run_simulation(n=500, runs=200, t_gw=0.073, t_src=0.346, t_slip=0.74, seed=MASTER_SEED)
    
    print("\nRunning 500-agent simulations with EARLY parameters (T_gw=0.017, T_src=0.700, runs=200)...")
    sim_early = run_simulation(n=500, runs=200, t_gw=0.017, t_src=0.700, t_slip=0.95, seed=MASTER_SEED)
    
    out = {
        "closed_form_comparison": theory_comparison,
        "floor_at_k4": {
            "T_early_0.017": closed_form_floor(0.017, 4),
            "T_test_0.073": closed_form_floor(0.073, 4),
            "T_d1_0.292": closed_form_floor(0.292, 4)
        },
        "sim_test_0.073": sim_test,
        "sim_early_0.017": sim_early
    }
    
    with open("results/j7_theory_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("Saved J7 results to results/j7_theory_results.json")

if __name__ == "__main__":
    main()

