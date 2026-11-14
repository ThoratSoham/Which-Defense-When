# Phase 3 hop-2 persistence report (qwen2_5_3b)

```
pool: 1600 rows, 209 hop-1 slips (13.1%)

(a) deterministic re-pass (D1 on post-gateway text):
    survived notes still leaking: 69/69
    gate-passed incl. never-leaked, still leaking: 69/101
    caught notes still leaking : 202/1499

(b) rho (persistence | survived at hop 1): 63/69 = 0.913  95% CI [0.823, 0.960]

(b) fresh origination (control): 21/150 = 0.140  95% CI [0.093, 0.205]

```
