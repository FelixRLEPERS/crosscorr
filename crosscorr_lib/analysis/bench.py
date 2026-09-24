from core import benchmark

for c in (0.30, 0.15, 0.08, 0.04):
    r = benchmark(coupling=c, n_surrogates=300, seed=42)
    print(c, r)