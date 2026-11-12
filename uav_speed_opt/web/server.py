"""UAV Flight-Speed Optimiser web app: Flask API over the uav_opt optimisers + a custom HTML/JS front end.

Run from the uav_speed_opt folder:   python -m web.server      then open http://localhost:8080
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from uav_opt.benchmark import CATEGORIES, category_uav, load_rows  # noqa: E402
from uav_opt.model import UAV, Mission, budget_from_endurance, energy_kj, evaluate  # noqa: E402
from uav_opt.optimize import grid_search, nsga2, weighted_sum_scipy  # noqa: E402

STATIC = Path(__file__).parent / "static"
app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
ROWS = load_rows()
ALGOS = {"grid": grid_search, "scipy": weighted_sum_scipy, "nsga2": nsga2}
ALGO_NAMES = {"grid": "Grid search", "scipy": "Weighted sum (SciPy)", "nsga2": "NSGA-II (pymoo)"}
SHOW_COLS = ["Company", "HQ", "Flagship model", "Airframe", "MTOW / TOW (kg)", "Max payload (kg)", "Max flight time (min)",
             "Max speed (m/s)", "Wind resistance (m/s)", "IP rating", "Robustness score (/100)", "Source link"]


def clean(x):
    """JSON-safe: numpy -> python, NaN/inf -> None."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(float(x)) else round(float(x), 5)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


@app.after_request
def no_cache(resp):
    """Always serve the latest page, script and styles (no stale copies in the browser)."""
    if not request.path.startswith("/static/vendor/"):
        resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


def build(params: dict) -> tuple[UAV, Mission]:
    f = lambda k, d: float(params.get(k, d))
    mass = f("mass", 2.04)
    uav = UAV(mass_kg=mass, v_max=f("vmax", 20), battery_kJ=budget_from_endurance(mass, f("endurance", 30)),
              lam0=f("lam0", 0.01), k=f("k", 2)).with_payload(f("payload", 0))
    return uav, Mission(distance_km=f("distance", 5), headwind_ms=f("headwind", 0), r_min=f("rmin", 0.995))


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/api/categories")
def categories():
    out = {}
    for key, title in CATEGORIES.items():
        uav, meta = category_uav(ROWS[key])
        comps = [{c: r.get(c) for c in SHOW_COLS} for r in ROWS[key]]
        for c, r in zip(comps, ROWS[key]):
            c["Source link"] = r.get("Source link")
        out[key] = dict(title=title, defaults=dict(mass=round(uav.mass_kg, 2), vmax=round(uav.v_max, 1),
                                                   endurance=meta["endurance_min"], lam0=round(uav.lam0, 4)),
                        meta=meta, companies=comps)
    return jsonify(clean(out))


@app.post("/api/optimize")
def optimize():
    p = request.get_json(force=True) or {}
    uav, mission = build(p)
    w = float(p.get("w", 0.5))
    algo = p.get("algo", "grid")
    res = ALGOS[algo](uav, mission, w)
    V = np.arange(0.5, uav.v_max + 1e-9, 0.05)
    ev = evaluate(V, uav, mission)
    out = dict(algo=ALGO_NAMES[algo], runtime_ms=res.runtime_ms, evaluations=res.evaluations,
               battery_kJ=uav.battery_kJ, total_mass=uav.mass_kg,
               curves=dict(V=V, E=ev["E_kJ"], T=ev["T_min"], R=ev["R"], feasible=ev["feasible"].astype(int)))
    if res.v_star is None:
        out.update(ok=False)
        return jsonify(clean(out))
    pt = evaluate(np.array([res.v_star]), uav, mission)
    pf = ev["feasible"] & (V >= res.v_energy - 1e-9)
    out.update(ok=True, v_star=res.v_star, v_energy=res.v_energy, v_time=res.v_time,
               E=pt["E_kJ"][0], T=pt["T_min"][0], R=pt["R"][0], energy_pct=100 * pt["E_kJ"][0] / uav.battery_kJ,
               feasible_min=V[ev["feasible"]].min(), feasible_max=V[ev["feasible"]].max(),
               pareto=dict(T=ev["T_min"][pf], E=ev["E_kJ"][pf]))
    if res.front is not None and algo == "nsga2":
        en = evaluate(res.front, uav, mission)
        out["nsga_points"] = dict(T=en["T_min"], E=en["E_kJ"])
    base = 10.0 if 10.0 <= uav.v_max else None
    if base:
        e10 = float(energy_kj(base, uav, mission)); t10 = mission.distance_km * 1000 / max(base - mission.headwind_ms, 1e-9) / 60
        out["baseline"] = dict(V=base, E=e10, T=t10, energy_saved=1 - pt["E_kJ"][0] / e10 if math.isfinite(e10) else None,
                               time_saved=1 - pt["T_min"][0] / t10 if base > mission.headwind_ms else None)
    return jsonify(clean(out))


@app.post("/api/compare")
def compare():
    p = request.get_json(force=True) or {}
    uav, mission = build(p)
    w = float(p.get("w", 0.5))
    rows = []
    for key, fn in ALGOS.items():
        r = fn(uav, mission, w)
        rows.append(dict(method=ALGO_NAMES[key], v_star=r.v_star, v_energy=r.v_energy, v_time=r.v_time,
                         evaluations=r.evaluations, runtime_ms=r.runtime_ms))
    return jsonify(clean(rows))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n  UAV Flight-Speed Optimiser running at  http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
