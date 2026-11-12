# UAV flight-speed optimiser (EL Phase 2)

Picks the flight speed that minimises energy and delivery time while keeping mission reliability above a target.

```
uav_opt/model.py      power (Zeng et al. 2019), energy, time (with headwind), reliability
uav_opt/optimize.py   grid search, weighted sum (SciPy), NSGA-II (pymoo)
uav_opt/benchmark.py  loads category medians from data/UAV_Industry_Benchmark_v2.xlsx
run_phase2.py         all experiments -> results/*.csv and results/fig*.png
web/                  Website: Flask API (web/server.py) + custom HTML/CSS/JS front end (web/static)
app.py                earlier Streamlit prototype (kept for reference)
tests/                verification against the Phase-1 reference curve (19 tests)
```

## Run

```bash
pip install -r requirements.txt pytest
python -m pytest -q tests
python run_phase2.py
python3 -m web.server        # then open http://localhost:8080
```

The reliability parameters (lambda0 = 0.01 per flight-hour, k = 2) are illustrative assumptions: no surveyed company publishes failure-rate data.
