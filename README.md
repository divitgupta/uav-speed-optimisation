# Minimizing Energy Consumption and Delivery Time while Ensuring High Reliability in UAVs

Experiential Learning project, RV College of Engineering (SDG 9: Industry, Innovation and Infrastructure).

Flight speed is the one setting that affects a drone's battery use, delivery time and mission reliability. We model all three as
functions of speed, then find the best feasible speed for a mission with three optimisers (grid search, SciPy weighted sum and
NSGA-II), using inputs from a benchmark of 50 commercial drones in six application categories.

## Repository layout

| Path | What it is |
|---|---|
| `uav_speed_opt/` | Simulator, optimisers, experiments, tests and the web application ([details](uav_speed_opt/README.md)) |
| `UAV_Industry_Benchmark_v2.xlsx` | Industry benchmark: 50 UAVs, 6 categories, sourced specifications and a per-category simulation sheet |
| `SDG9_Phase1_UAV.pptx`, `SDG9_Phase2_UAV.pptx` | Phase-1 and Phase-2 presentations |
| `SDG9_Synopsis_UAV.docx` / `.pdf` | Project synopsis |
| `decks/` | Scripts that build the presentations and synopsis from the results |

## Quick start

```bash
cd uav_speed_opt
pip install -r requirements.txt pytest
python -m pytest -q tests        # model verification (19 tests)
python run_phase2.py             # regenerate results/ figures and CSVs
python -m web.server             # web app at http://localhost:8080
```

## Key results (5 km mission)

- The model reproduces the Phase-1 reference energy curve with a maximum error of 0.05 kJ.
- Grid search, SciPy and NSGA-II agree on the optimal speed in all six categories.
- Flying at the optimal speed saves 18–47% energy and 16–60% time compared with a fixed 10 m/s.

The reliability parameters are illustrative assumptions, because no surveyed drone company publishes failure-rate data.

## References

- Zeng, Y., Xu, J., & Zhang, R. (2019). Energy minimization for wireless communication with rotary-wing UAV. IEEE Trans. Wireless Communications, 18(4).
- Petritoli, E., Leccese, F., & Ciani, L. (2018). Reliability and maintenance analysis of unmanned aerial vehicles. Sensors, 18(9), 3171.
- Deb, K., et al. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. IEEE Trans. Evolutionary Computation, 6(2).
