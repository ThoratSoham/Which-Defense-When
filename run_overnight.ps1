# Overnight experiments. Run from E:\MAS Reference with the venv active:   .\run_overnight.ps1
# Resumable: if it stops, run it again and it skips finished cells. Keep the laptop plugged in and set Sleep to "Never".
# Order = priority. Press Ctrl+C any time; whatever finished is already saved.
$m = "llama3.2:3b","qwen2.5:3b","gemma2:2b"        # drop a model here to make it faster
$log = "run_overnight.log"

# 1) VALIDATION of the simulation: real 6-agent chain and star, no defense, low pressure (intermediate leak rates)
python network_run.py --models $m --episodes 20 --defense none --pressure low --topologies chain6 star6 --results network_results.csv 2>&1 | Tee-Object -Append $log
# 2) VALIDATION with the gateway (high pressure, semantic secret: the only setting where the gateway leaks a little)
python network_run.py --models $m --episodes 20 --defense gateway --pressure high --kinds semantic --topologies chain6 star6 --results network_results.csv 2>&1 | Tee-Object -Append $log
# 3) ADVERSARIAL exfiltration (threat model B): agent 0 is told to leak in disguise; 3-agent chain
python network_run.py --models $m --episodes 30 --defense none --topologies chain3 --attack --results attack_results.csv 2>&1 | Tee-Object -Append $log
python network_run.py --models $m --episodes 30 --defense gateway --topologies chain3 --attack --results attack_results.csv 2>&1 | Tee-Object -Append $log

python -c "import pandas as pd; [print(f, pd.read_csv(f, header=None).groupby([1,2,3,4]).size().to_string()) for f in ('network_results.csv','attack_results.csv')]"
Write-Host "Done. Next: python validate_sim.py results_v2r.csv network_results.csv"
