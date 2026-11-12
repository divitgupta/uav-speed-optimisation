"""Phase-2 experiments: verification, per-category optimisation, Pareto fronts, sensitivity.

Usage:  python run_phase2.py            -> writes CSVs and PNG figures to results/
"""
from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from uav_opt.benchmark import CATEGORIES, category_uav, load_rows
from uav_opt.model import UAV, Mission, energy_kj, evaluate
from uav_opt.optimize import grid_search, nsga2, weighted_sum_scipy

OUT = Path(__file__).parent / "results"
OUT.mkdir(exist_ok=True)
NAVY, RED, GREY, TEAL, GOLD = "#002060", "#C00000", "#8C8C8C", "#1B7F79", "#C9A227"
CAT_COLORS = ["#002060", "#C00000", "#2E8B57", "#C9A227", "#6A4C93", "#E07B00"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 12})
W, V_ROT = 0.5, 10.0  # weight on energy; rule-of-thumb comparison speed
REF_UAV, REF_MISSION = UAV(v_max=25, battery_kJ=250), Mission(distance_km=5)


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", pad_inches=0.15); plt.close(fig)


def write_csv(name, rows):
    with open(OUT / name, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)


# 1. Verification against the Phase-1 reference curve ---------------------------------------
phase1 = {4: 188.3, 6: 114.5, 8: 80.6, 10: 63.0, 12: 53.3, 14: 47.8, 16: 45.1, 18: 44.2, 20: 44.6,
          22: 46.0, 24: 48.4, 26: 51.4, 28: 55.1, 30: 59.4}
ver = [dict(V=v, phase1_kJ=e, model_kJ=round(float(energy_kj(v, UAV(v_max=30), REF_MISSION)), 2)) for v, e in phase1.items()]
for r in ver: r["abs_error_kJ"] = round(abs(r["model_kJ"] - r["phase1_kJ"]), 3)
write_csv("verification.csv", ver)

# 2. Reference mission curves -----------------------------------------------------------------
V = np.arange(1, 25.01, 0.05)
ev = evaluate(V, REF_UAV, REF_MISSION)
g = grid_search(REF_UAV, REF_MISSION, W)
fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
for a, key, lab, col in zip(ax, ["E_kJ", "T_min", "R"], ["Energy E(V) [kJ]", "Delivery time T(V) [min]", "Reliability R(V)"], [NAVY, TEAL, RED]):
    a.plot(V, ev[key], color=col, lw=2.2)
    f = ev["feasible"]
    a.axvspan(V[f].min(), V[f].max(), color="#DDE6F2", alpha=0.6, label="feasible")
    for v, ls, l in [(g.v_energy, ":", "V_E*"), (g.v_star, "--", "V* (w=0.5)"), (g.v_time, "-.", "V_T*")]:
        a.axvline(v, color=GREY, ls=ls, lw=1.2, label=l)
    a.set_xlabel("Airspeed V [m/s]"); a.set_title(lab)
ax[0].set_ylim(0, 200); ax[1].set_ylim(0, 40)
ax[2].axhline(REF_MISSION.r_min, color=RED, lw=0.8, ls=":"); ax[2].set_ylim(0.990, 1.0)
ax[0].legend(fontsize=8, frameon=False)
save(fig, "fig1_reference_curves.png")

# 3. Per-category optimisation with three algorithms -------------------------------------------
rows = load_rows()
cat_res, algo_rows, fronts = [], [], {}
for sheet, title in CATEGORIES.items():
    uav, meta = category_uav(rows[sheet])
    res = {r.method: r for r in (grid_search(uav, REF_MISSION, W, step=0.05), weighted_sum_scipy(uav, REF_MISSION, W), nsga2(uav, REF_MISSION, W))}
    gr = res["Grid search"]
    e_star = float(energy_kj(gr.v_star, uav, REF_MISSION)); e_rot = float(energy_kj(V_ROT, uav, REF_MISSION))
    ev_s = evaluate(np.array([gr.v_star]), uav, REF_MISSION)
    cat_res.append(dict(category=title, companies=meta["n_companies"], multirotors=meta["n_multirotor"],
                        mass_kg=round(meta["mass_kg"], 2), v_max=round(meta["v_max"], 1), endurance_min=meta["endurance_min"],
                        robustness=round(meta["robustness"], 1), battery_kJ=round(uav.battery_kJ, 1),
                        V_E=round(gr.v_energy, 2), V_star=round(gr.v_star, 2), V_T=round(gr.v_time, 2),
                        E_star_kJ=round(e_star, 1), T_star_min=round(float(ev_s["T_min"][0]), 2), R_star=round(float(ev_s["R"][0]), 4),
                        E_at_10ms_kJ=round(e_rot, 1), energy_saved_vs_10ms=round(1 - e_star / e_rot, 3),
                        time_saved_vs_10ms=round(1 - V_ROT / gr.v_star, 3)))
    for m, r in res.items():
        algo_rows.append(dict(category=title, method=m, V_E=r.v_energy and round(r.v_energy, 2), V_star=r.v_star and round(r.v_star, 2),
                              V_T=r.v_time and round(r.v_time, 2), evaluations=r.evaluations, runtime_ms=round(r.runtime_ms, 2)))
    fronts[title] = (uav, res)
write_csv("category_results.csv", cat_res)
write_csv("algorithm_comparison.csv", algo_rows)

# 3a. bar chart of optimal speeds
fig, ax = plt.subplots(figsize=(11, 4.2))
x = np.arange(len(cat_res)); bw = 0.26
for i, (key, lab, col) in enumerate([("V_E", "Min-energy V_E*", TEAL), ("V_star", "Weighted-sum V* (w=0.5)", NAVY), ("V_T", "Min-time V_T*", RED)]):
    b = ax.bar(x + (i - 1) * bw, [r[key] for r in cat_res], bw, label=lab, color=col)
    ax.bar_label(b, fmt="%.1f", fontsize=8, padding=2)
ax.set_xticks(x, [r["category"].replace(" & ", " &\n").replace(" / ", " /\n") for r in cat_res], fontsize=9)
ax.set_ylabel("Airspeed [m/s]"); ax.set_ylim(0, 30); ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=9)
ax.set_title("Optimal feasible speed per drone category (5 km mission)")
save(fig, "fig2_category_speeds.png")

# 3b. Pareto fronts: (a) reference multirotor, grid vs NSGA-II; (b) normalised fronts per category
fig, axs = plt.subplots(1, 2, figsize=(13, 4.6))
a = axs[0]
Vg = np.arange(1, REF_UAV.v_max + 1e-9, 0.01); e = evaluate(Vg, REF_UAV, REF_MISSION); f = e["feasible"]
gref = grid_search(REF_UAV, REF_MISSION, W, step=0.01); nref = nsga2(REF_UAV, REF_MISSION, W)
pf = f & (Vg >= gref.v_energy)
a.plot(e["T_min"][f & (Vg < gref.v_energy)], e["E_kJ"][f & (Vg < gref.v_energy)], color=GREY, lw=1.2, label="dominated feasible speeds")
a.plot(e["T_min"][pf], e["E_kJ"][pf], color=NAVY, lw=3, label="Pareto front (grid search)")
en = evaluate(nref.front, REF_UAV, REF_MISSION)
a.scatter(en["T_min"], en["E_kJ"], s=22, color="white", edgecolor=RED, lw=1.2, zorder=3, label="NSGA-II solutions (pop 40, 60 gen)")
for v, lab, dx in [(gref.v_energy, "V_E* = %.1f m/s", 0.15), (gref.v_time, "V_T* = %.1f m/s", 0.15)]:
    ee = evaluate(np.array([v]), REF_UAV, REF_MISSION)
    a.annotate(lab % v, (ee["T_min"][0], ee["E_kJ"][0]), xytext=(ee["T_min"][0] + dx, ee["E_kJ"][0] + 0.8), fontsize=9)
a.set_xlim(3.0, 7.5); a.set_ylim(43, 56)
a.set_xlabel("Delivery time T [min]"); a.set_ylabel("Energy E [kJ]"); a.legend(fontsize=8, frameon=False, loc="upper right")
a.set_title("Reference 2 kg multirotor, 5 km: energy-time Pareto front")
b = axs[1]
for (title, (uav, res)), col in zip(fronts.items(), CAT_COLORS):
    Vg = np.arange(1, uav.v_max + 1e-9, 0.01); e = evaluate(Vg, uav, REF_MISSION); f = e["feasible"]
    pf = f & (Vg >= res["Grid search"].v_energy)
    Em, Tm = e["E_kJ"][f].min(), e["T_min"][f].min()
    if pf.sum() > 2:
        b.plot(e["T_min"][pf] / Tm, e["E_kJ"][pf] / Em, color=col, lw=2.5, label=title)
    else:
        b.scatter([1], [1], color=col, s=50, zorder=3, label=title + " (single point)")
b.set_xlabel("T / T_min"); b.set_ylabel("E / E_min"); b.set_xlim(0.98, 1.2); b.set_ylim(0.995, 1.08)
b.legend(fontsize=8, frameon=False, loc="upper right"); b.set_title("Benchmark categories: normalised fronts")
save(fig, "fig3_pareto_fronts.png")

# 4. Sensitivity analysis on the reference multirotor -----------------------------------------
fig, axs = plt.subplots(1, 3, figsize=(15, 4.0), gridspec_kw=dict(wspace=0.6))
pl = np.linspace(0, 2.0, 21)
vE_p = [grid_search(REF_UAV.with_payload(p), REF_MISSION, W).v_energy for p in pl]
eS_p = [float(energy_kj(grid_search(REF_UAV.with_payload(p), REF_MISSION, W).v_star, REF_UAV.with_payload(p), REF_MISSION)) for p in pl]
a = axs[0]; a.plot(pl, eS_p, color=NAVY, lw=2.2); a.set_xlabel("Payload [kg]"); a.set_ylabel("Energy at V* [kJ]", color=NAVY)
a2 = a.twinx(); a2.plot(pl, vE_p, color=RED, lw=2, ls="--"); a2.set_ylabel("V_E* [m/s]", color=RED); a.set_title("Payload")
hw = np.linspace(0, 10, 21)
vE_w = [grid_search(REF_UAV, replace(REF_MISSION, headwind_ms=h), W).v_energy for h in hw]
eS_w = [float(energy_kj(v, REF_UAV, replace(REF_MISSION, headwind_ms=h))) if v else np.nan for v, h in zip(vE_w, hw)]
a = axs[1]; a.plot(hw, vE_w, color=RED, lw=2.2, ls="--"); a.set_xlabel("Headwind [m/s]"); a.set_ylabel("V_E* [m/s]", color=RED)
a2 = a.twinx(); a2.plot(hw, eS_w, color=NAVY, lw=2); a2.set_ylabel("Min energy [kJ]", color=NAVY); a.set_title("Headwind")
dist = np.linspace(1, 30, 59)
res_d = [grid_search(REF_UAV, replace(REF_MISSION, distance_km=d), W) for d in dist]
lo = [float(r.front.min()) if r.front is not None and r.v_star else np.nan for r in res_d]
lo_feas = []
for d in dist:
    ev = evaluate(np.arange(1, 25.01, 0.05), REF_UAV, replace(REF_MISSION, distance_km=d))
    lo_feas.append(ev["V"][ev["feasible"]].min() if ev["feasible"].any() else np.nan)
vs_d = [r.v_star if r.v_star else np.nan for r in res_d]
a = axs[2]; a.plot(dist, lo_feas, color=RED, lw=2, ls="--", label="slowest feasible speed")
a.plot(dist, vs_d, color=NAVY, lw=2.2, label="V* (w=0.5)"); a.set_xlabel("Mission distance [km]"); a.set_ylabel("Speed [m/s]")
a.legend(fontsize=8, frameon=False); a.set_title("Mission distance")
save(fig, "fig4_sensitivity.png")
sens = [dict(payload_kg=round(p, 2), V_E=v, E_star_kJ=round(e, 1)) for p, v, e in zip(pl, vE_p, eS_p)]
write_csv("sensitivity_payload.csv", sens)
write_csv("sensitivity_headwind.csv", [dict(headwind_ms=round(h, 1), V_E=v, E_min_kJ=round(e, 1)) for h, v, e in zip(hw, vE_w, eS_w)])
write_csv("sensitivity_distance.csv", [dict(distance_km=round(d, 1), slowest_feasible=None if np.isnan(l) else round(l, 2),
                                            V_star=None if np.isnan(v) else round(v, 2)) for d, l, v in zip(dist, lo_feas, vs_d)])

# 5. Weight sweep: how the decision-maker's preference moves V* ---------------------------------
fig, ax = plt.subplots(figsize=(9.5, 4))
ws = np.linspace(0, 1, 21)
for (title, (uav, _)), col in zip(fronts.items(), CAT_COLORS):
    ax.plot(ws, [grid_search(uav, REF_MISSION, w, step=0.05).v_star for w in ws], color=col, lw=2, label=title)
ax.set_xlabel("Weight on energy w  (1 - w on time)"); ax.set_ylabel("Optimal speed V* [m/s]")
ax.legend(fontsize=8, frameon=False, loc="center left", bbox_to_anchor=(1.01, 0.5)); ax.set_title("Preference sweep: V* vs weight on energy")
save(fig, "fig5_weight_sweep.png")

print("verification max abs error (kJ):", max(r["abs_error_kJ"] for r in ver))
for r in cat_res: print(r)
for r in algo_rows: print(r)
print("headwind V_E:", list(zip(hw[::4], vE_w[::4])))
print("payload V_E:", list(zip(pl[::5], vE_p[::5])))
print("distance:", [(d, l, v) for d, l, v in zip(dist[::6], lo_feas[::6], vs_d[::6])])
