"""Build the EL Phase-II deck on the SDG-P2 template."""
import csv
import sys
from pathlib import Path

from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN

from deckkit import Deck, RED, NAVY, GREY, INK, TINT, TINT2, GREEN, AMBER, WHITE, FONT
import team

EL = Path(__file__).resolve().parents[1]
RES = EL / "uav_speed_opt" / "results"
TEMPLATE = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "templates" / "SDG-P2_Template.pptx")
OUT = sys.argv[2] if len(sys.argv) > 2 else str(EL / "SDG9_Phase2_UAV.pptx")
I = Inches

cat = list(csv.DictReader(open(RES / "category_results.csv")))
algo = list(csv.DictReader(open(RES / "algorithm_comparison.csv")))
ver = list(csv.DictReader(open(RES / "verification.csv")))

d = Deck(TEMPLATE)
d.fill_title(team.TITLE, team.TEAM_NO, team.TEAM_NAME, team.MEMBERS)
d.fill_outline("EL Phase-II", [("Project Execution", "plan vs progress, methodology adherence, benchmark, verification"),
                               ("Tools and Techniques", "tool selection, models, optimisers, integration"),
                               ("Partial Results", "optimal speeds, Pareto fronts, sensitivity analysis"),
                               ("Next Steps & References", "")])

# ======================= PROJECT EXECUTION =======================
S = "Project Execution"
s = d.slide("Execution Status: Plan vs Progress", S)
rows = [["Phase-1 plan", "Weeks", "Planned deliverable", "Status", "Evidence"],
        ["Literature survey", "1–2", "Select power & reliability models", ("Done", {"color": GREEN, "bold": True}), "Zeng et al. (2019) power model; Petritoli et al. (2018) reliability"],
        ["Simulation model", "3–5", "Energy, time, reliability in Python", ("Done", {"color": GREEN, "bold": True}), "uav_opt/model.py; 19 automated tests pass"],
        ["Optimization", "6–8", "Constraints, weighted sum, NSGA-II", ("Done", {"color": GREEN, "bold": True}), "uav_opt/optimize.py; 3 optimisers agree"],
        ["Dashboard & testing", "9–11", "Sensitivity runs; optional ML", ("In progress", {"color": AMBER, "bold": True}), "Web app + sensitivity study done; ML pending"],
        ["Closure", "12–13", "Report, paper draft, review", ("Planned", {"color": GREY, "bold": True}), "—"]]
d.table(s, I(0.5), I(1.3), I(12.3), rows, col_w=[2.2, 0.9, 3.2, 1.4, 4.6], size=13, head_size=13, row_h=0.5, bold_first=True)
d.box(s, I(0.5), I(4.6), I(12.3), I(1.75), TINT)
d.rich(s, I(0.7), I(4.7), I(11.9), I(1.6), [
    [("Beyond the plan: ", {"bold": True, "color": NAVY}), ("we also built a UAV Industry Benchmark (50 companies, 6 categories), so our model inputs come from real published specifications instead of one assumed drone.", {})],
    [("Scope: ", {"bold": True, "color": NAVY}), ("all our Phase-1 objectives are on track; the only open item is the optional ML layer, which we will take up along with testing.", {})],
    [("Timeliness: ", {"bold": True, "color": NAVY}), ("we finished and verified everything planned up to week 8, and started the week 9–11 work early (the web app is already running).", {})]], size=15)
d.notes(s, "Walk through the Phase-1 timeline row by row. Emphasise that everything planned up to optimisation is finished and tested.")

s = d.slide("Adherence to the Phase-1 Methodology", S)
y0, h = I(1.55), I(1.15)
nodes = [("Mission inputs", "distance, payload, wind", "inputs"),
         ("Simulation model", "P(V), E, T, R(V)", "model.py"),
         ("Constraint filter", "R ≥ Rmin, E ≤ budget, V ≤ Vmax", "model.py"),
         ("Optimisers", "grid · weighted sum · NSGA-II", "optimize.py"),
         ("Optimal speed V*", "+ Pareto front", "run_phase2.py"),
         ("Web app", "what-if analysis", "web/server.py")]
x = I(0.45); wN = I(1.88); gap = I(0.22)
for i, (hd, sb, mod) in enumerate(nodes):
    xi = x + i * (wN + gap)
    d.node(s, xi, y0, wN, h, hd, sb, fill=RED if hd.startswith("Optimal") else NAVY, size=14)
    d.chip(s, xi + I(0.24), y0 + h + I(0.12), wN - I(0.48), "Implemented" if not hd.startswith("Web") else "Prototype", fill=GREEN if not hd.startswith("Web") else AMBER)
    d.text(s, xi, y0 + h + I(0.48), wN, I(0.3), mod, size=11, color=GREY, align=PP_ALIGN.CENTER, italic=True)
    if i < len(nodes) - 1:
        d.arrow(s, xi + wN, y0 + h / 2, xi + wN + gap, y0 + h / 2)
# benchmark feeder
d.node(s, I(2.55), I(4.0), I(3.9), I(0.9), "UAV Industry Benchmark (new)", "category medians: mass, Vmax, flight time, robustness", fill=TINT, color=NAVY, size=14)
d.arrow(s, I(3.4), I(4.0), I(3.4), y0 + h + I(0.85), color=NAVY)
d.rich(s, I(6.8), I(3.95), I(6.0), I(2.5), [
    [("Same pipeline as Phase-1: ", {"bold": True, "color": NAVY}), ("we implemented every block of our proposed flowchart as tested code.", {})],
    [("Same formulation: ", {"bold": True, "color": NAVY}), ("min {E, T} s.t. R ≥ Rmin, E ≤ η·E_batt, Vmin ≤ V ≤ Vmax.", {})],
    [("Deviation (minor): ", {"bold": True, "color": NAVY}), ("we added headwind to the time model and a benchmark data layer; the optional ML layer stays in weeks 9–11 as planned.", {})]], size=14)

s = d.slide("New Data Layer: UAV Industry Benchmark", S)
for i, (v, l) in enumerate([("50", "companies benchmarked"), ("6", "drone categories"), ("11", "spec fields per drone"), ("100%", "rows with a source link")]):
    d.stat(s, I(0.6 + i * 3.1), I(1.25), I(2.8), v, l)
rows = [["Category", "Companies", "Median mass (kg)", "Median flight time (min)", "Median max speed (m/s)", "Median wind (m/s)"],
        ["Delivery / Logistics", "10", "28.6", "54", "22.4", "15.0"],
        ["Disaster Relief & SAR", "9", "4.6", "42", "19.1", "9.7"],
        ["Agricultural", "9", "67.0", "17.5", "13.8", "8.0"],
        ["Surveillance & Security", "8", "1.9", "52", "19.0", "12.1"],
        ["Mapping & Surveying", "7", "1.6", "54", "21.3", "12.4"],
        ["Industrial Inspection", "7", "3.2", "43", "16.0", "12.0"]]
d.table(s, I(0.5), I(2.75), I(8.2), rows, col_w=[2.6, 1.2, 1.4, 1.6, 1.6, 1.3], size=12, head_size=11, row_h=0.42, bold_first=True)
d.card(s, I(8.95), I(2.75), I(3.85), I(2.95), "Quality rules", [
    "Official spec sheets / reputable sources only",
    "Blank = not disclosed, never guessed",
    "Conflicting figures logged in notes",
    "Defunct firms excluded (e.g. Swoop Aero, Guardian Agriculture)"], size=12)
d.text(s, I(0.5), I(5.85), I(12.3), I(0.6), "Key finding: none of the 50 companies publishes MTBF or failure-rate data, so the reliability model stays an "
       "explicit assumption, now scaled by each category's disclosed robustness score.", size=13, color=RED, italic=True)

s = d.slide("Quality: Model Verification & Testing", S)
rows = [["Speed V (m/s)", "Phase-1 value (kJ)", "Phase-2 code (kJ)", "Error (kJ)"]]
for r in ver:
    if int(r["V"]) in (4, 8, 12, 18, 24, 30):
        rows.append([r["V"], r["phase1_kJ"], r["model_kJ"], r["abs_error_kJ"]])
d.text(s, I(0.5), I(1.2), I(6), I(0.4), "Reproduces the Phase-1 reference curve (5 km, 2 kg drone)", size=15, bold=True, color=NAVY, font=FONT)
d.table(s, I(0.5), I(1.7), I(6.0), rows, size=13, head_size=12, row_h=0.42)
d.stat(s, I(0.5), I(4.85), I(3.0), "0.05 kJ", "max error over 14 speeds")
d.stat(s, I(3.5), I(4.85), I(3.0), "19 / 19", "automated tests pass (pytest)", color=GREEN)
d.card(s, I(6.9), I(1.2), I(5.9), I(4.9), "What we test", [
    "Energy curve matches the Phase-1 chart at all 14 speeds",
    "Hover power equals P0 + Pi (Zeng et al., 2019)",
    "Time model: 5 km at 10 m/s = 500 s; headwind halves ground speed correctly; infeasible when wind ≥ airspeed",
    "Reliability decreases with distance and stays in (0, 1)",
    "Grid search, SciPy and NSGA-II agree on V* within 0.15–0.5 m/s",
    "Optimiser reports 'no feasible speed' when the battery is too small"], size=13)

# ======================= TOOLS & TECHNIQUES =======================
S = "Tools and Techniques"
s = d.slide("Tool Selection and Justification", S)
rows = [["Tool", "Used for", "Why this tool"],
        ["Python 3.13 + NumPy", "Vectorised physics model (E, T, R over speed grids)", "Fast array maths; standard in scientific computing"],
        ["SciPy (optimize)", "Weighted-sum optimiser (bounded Brent search)", "Robust, well-tested 1-D optimisation"],
        ["pymoo", "NSGA-II multi-objective optimiser with constraints", "Reference implementation of Deb et al. (2002)"],
        ["Matplotlib", "Publication-quality result figures", "Reproducible plots straight from the scripts"],
        ["Flask + HTML/CSS/JS + Plotly.js", "Web app: REST API over the optimisers + custom UI", "Full control of the interface; runs offline in any browser"],
        ["Excel + openpyxl", "Industry benchmark with live formulas; loaded into Python", "Auditable data source that non-programmers can read"],
        ["pytest", "Automated verification against Phase-1 values", "Catches regressions as the model grows"]]
d.table(s, I(0.5), I(1.25), I(12.3), rows, col_w=[2.3, 5.0, 5.0], size=13, head_size=13, row_h=0.56, bold_first=True)

s = d.slide("Techniques I: Mathematical Models Applied", S)
cards = [("Power (Zeng et al., 2019)", ["P(V) = P0(1 + 3V²/U²tip) + Pi·√(√(1 + V⁴/4v0⁴) − V²/2v0²) + ½·d0·ρ·s·A·V³",
                                          "Scaled to each category's median mass (constant disc loading; drag ∝ m^2/3)"]),
         ("Energy and time", ["T(V) = D / (V − w)   (w = headwind)", "E(V) = P(V) · T(V)",
                              "Battery budget = η · P_hover · published flight time (η = 0.8)"]),
         ("Reliability (assumption)", ["R(V) = exp(−λ(V) · T(V))", "λ(V) = λ0 (1 + k (V/Vmax)²),  λ0 = 0.01 /h, k = 2",
                                       "λ0 scaled by category robustness score: λ0·(1.5 − score/100)"]),
         ("Optimisation problem", ["min {E(V), T(V)}", "s.t.  R(V) ≥ 0.995,  E(V) ≤ budget,  1 ≤ V ≤ Vmax",
                                   "Weighted sum: J = w·E/E_min + (1 − w)·T/T_min"])]
for i, (hd, lines) in enumerate(cards):
    cx = I(0.5 + (i % 2) * 6.25); cy = I(1.25 + (i // 2) * 2.6)
    d.card(s, cx, cy, I(6.05), I(2.4), hd, lines, size=14, fill=TINT if i != 2 else TINT2, head_color=NAVY if i != 2 else RED)

s = d.slide("Techniques II: Optimisation Algorithms", S)
desc = [("Grid search", "Evaluates every speed on a 0.05 m/s grid, filters infeasible points, reads off V_E*, V_T* and V*.", "Baseline / ground truth"),
        ("Weighted sum (SciPy)", "Bounded Brent search on a penalised objective; bisection finds the fastest feasible speed.", "Fastest per evaluation"),
        ("NSGA-II (pymoo)", "Population 40, 60 generations, constraint-dominance; returns the whole Pareto set.", "Scales to multi-variable problems")]
for i, (hd, body, tag) in enumerate(desc):
    cx = I(0.5 + i * 4.15)
    d.card(s, cx, I(1.25), I(3.95), I(2.05), hd, [body], size=13)
    d.chip(s, cx + I(0.15), I(2.95), I(2.6), tag, fill=NAVY, size=10)
import statistics as st
agg = {}
for r in algo:
    agg.setdefault(r["method"], []).append(r)
rows = [["Method", "Avg evaluations", "Avg runtime (ms)", "V* agrees with grid (6/6 categories)"]]
for m, rs in agg.items():
    same = sum(1 for r, g in zip(rs, agg["Grid search"]) if abs(float(r["V_star"]) - float(g["V_star"])) <= 0.1)
    rows.append([m, f"{st.mean(int(r['evaluations']) for r in rs):,.0f}", f"{st.mean(float(r['runtime_ms']) for r in rs):.2f}", f"{same}/6"])
d.table(s, I(0.5), I(3.6), I(12.3), rows, col_w=[3, 2.2, 2.2, 4.9], size=14, head_size=13, row_h=0.48, bold_first=True)
d.text(s, I(0.5), I(5.75), I(12.3), I(0.7), "What we learned: with only one decision variable, grid search is the cheapest and is exact. NSGA-II needs about 2,400 evaluations "
       "but gives the whole trade-off curve, and it is the method we will need for route-level (multi-variable) optimisation in Phase-3.",
       size=13, color=INK, italic=True)

s = d.slide("Integration: Pipeline and Web App", S)
d.image(s, RES / "fig7_website.png", I(0.45), I(1.2), I(7.6), I(5.0))
flow = [("Benchmark (Excel)", "50 companies → category medians"), ("benchmark.py", "loads specs, builds UAV objects"),
        ("model.py", "P, E, T, R for any speed"), ("optimize.py", "grid · SciPy · NSGA-II"), ("web/server.py (Flask API)", "/api/optimize · /api/compare → web UI")]
for i, (hd, sb) in enumerate(flow):
    yy = I(1.25 + i * 1.02)
    d.node(s, I(8.45), yy, I(4.4), I(0.78), hd, sb, fill=NAVY if i < 4 else RED, size=13)
    if i < len(flow) - 1:
        d.arrow(s, I(10.65), yy + I(0.78), I(10.65), yy + I(1.02))
d.text(s, I(0.45), I(6.4) - I(0.05), I(7.6), I(0.3), "Web app (prototype): pick a drone category, move the mission sliders, and the optimal speed V* updates live.",
       size=11, color=GREY, italic=True)

# ======================= PARTIAL RESULTS =======================
S = "Partial Results"
s = d.slide("Result 1: Optimal Speed per Drone Category", S)
d.image(s, RES / "fig2_category_speeds.png", I(0.4), I(1.15), I(8.0), I(3.1))
rows = [["Category", "V* (m/s)", "Energy saved vs 10 m/s", "Time saved"]]
for r in cat:
    rows.append([r["category"].replace(" & Security", "").replace(" & Surveying", "").replace("Disaster Relief & ", "").replace(" / Logistics", ""),
                 f"{float(r['V_star']):.1f}", f"{100*float(r['energy_saved_vs_10ms']):.0f}%", f"{100*float(r['time_saved_vs_10ms']):.0f}%"])
d.table(s, I(8.6), I(1.2), I(4.3), rows, col_w=[1.7, 0.9, 1.2, 0.9], size=12, head_size=10, row_h=0.42, bold_first=True)
d.rich(s, I(0.5), I(4.35), I(12.3), I(2.0), [
    [("Clear: ", {"bold": True, "color": NAVY}), ("for a 5 km mission every category's optimum is well above a rule-of-thumb 10 m/s.", {})],
    [("Benefit: ", {"bold": True, "color": NAVY}), ("flying at V* saves 18–47% energy and 16–60% time versus 10 m/s, because hover-like flight at low speed burns induced power.", {})],
    [("Constraint that binds: ", {"bold": True, "color": NAVY}), ("in Delivery, Agricultural and Surveillance the energy-optimal speed sits at or beyond the published Vmax, so V_E* = V* = V_T* = Vmax.", {})]], size=14)

s = d.slide("Result 2: Energy–Time Pareto Front", S)
d.image(s, RES / "fig3_pareto_fronts.png", I(0.4), I(1.15), I(12.5), I(3.65))
d.rich(s, I(0.5), I(4.95), I(12.3), I(1.5), [
    [("Trade-off quantified: ", {"bold": True, "color": NAVY}), ("for the reference 2 kg drone, going from V_E* = 18.3 m/s to 25 m/s costs +12% energy but cuts delivery time by 27%.", {})],
    [("Algorithms agree: ", {"bold": True, "color": NAVY}), ("NSGA-II's 40 solutions lie exactly on the grid-search front.", {})],
    [("Category view: ", {"bold": True, "color": NAVY}), ("SAR, Mapping and Inspection drones have a real trade-off; the other three collapse to a single point at Vmax.", {})]], size=14)

s = d.slide("Result 3: Sensitivity Analysis", S)
d.image(s, RES / "fig4_sensitivity.png", I(0.4), I(1.15), I(12.5), I(3.45))
for i, (hd, lines) in enumerate([
        ("Payload", ["+2 kg payload → +75% energy at V* (49.8 → 87.0 kJ)", "V_E* rises only 18.3 → 19.5 m/s"]),
        ("Headwind", ["10 m/s headwind → V_E* 18.3 → 24.3 m/s", "Fly faster into wind; min energy ×1.9"]),
        ("Distance", ["Slowest feasible speed rises with distance (reliability + battery)", "Reference drone infeasible beyond ≈15.5 km"])]):
    d.card(s, I(0.5 + i * 4.15), I(4.75), I(3.95), I(1.6), hd, lines, size=12, head_size=15)

s = d.slide("Analysis and Interpretation", S)
d.image(s, RES / "fig5_weight_sweep.png", I(0.4), I(1.3), I(7.0), I(4.8))
d.rich(s, I(7.5), I(1.25), I(5.4), I(5.0), [
    [("Preference matters only near Vmax: ", {"bold": True, "color": NAVY}), ("V* moves below Vmax only when w > 0.7 (energy-focused planner).", {})],
    [("Reliability binds at low speed: ", {"bold": True, "color": NAVY}), ("long, slow flights accumulate failure exposure; the speed-stress term is weaker than the exposure-time effect.", {})],
    [("Wind is the biggest lever: ", {"bold": True, "color": NAVY}), ("a 10 m/s headwind shifts the energy optimum by 6 m/s, so a wind-aware speed schedule is worth more than tuning w.", {})],
    [("Limitations: ", {"bold": True, "color": RED}), ("reliability parameters are assumed (no public failure data); power model is rotary-wing only; not yet validated on real flight logs.", {})]], size=14, space=8)

s = d.slide("Next Steps (Phase-3)", S)
steps = [("Validate", "Compare E(V) with a public multirotor flight-energy dataset; calibrate model coefficients."),
         ("Wind-aware schedule", "Optimise speed per route segment using forecast wind."),
         ("ML surrogate (optional)", "Learn energy / reliability from flight data and compare with the physics model."),
         ("Web app & report", "Usability polish, export of recommendations, paper draft and final review.")]
for i, (hd, body) in enumerate(steps):
    cx = I(0.5 + i * 3.1)
    d.node(s, cx, I(1.5), I(2.85), I(0.9), f"{i+1}. {hd}", "", fill=NAVY if i < 3 else RED, size=14)
    d.text(s, cx, I(2.55), I(2.85), I(1.8), body, size=14, color=INK)
d.box(s, I(0.5), I(4.6), I(12.3), I(1.6), TINT)
d.rich(s, I(0.7), I(4.7), I(11.9), I(1.4), [
    [("SDG 9 link: ", {"bold": True, "color": NAVY}), ("energy-aware, reliable UAV operations support resilient logistics and disaster-response infrastructure (target 9.1) and industrial innovation (target 9.5).", {})],
    [("Reproducible: ", {"bold": True, "color": NAVY}), ("all results regenerate with one command (python run_phase2.py); the web app runs with python -m web.server.", {})]], size=14)

s = d.slide("References", None)
refs = ["Zeng, Y., Xu, J., & Zhang, R. (2019). Energy minimization for wireless communication with rotary-wing UAV. IEEE Trans. Wireless Communications, 18(4), 2329–2345.",
        "Petritoli, E., Leccese, F., & Ciani, L. (2018). Reliability and maintenance analysis of unmanned aerial vehicles. Sensors, 18(9), 3171. https://doi.org/10.3390/s18093171",
        "Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. IEEE Trans. Evolutionary Computation, 6(2), 182–197.",
        "Blank, J., & Deb, K. (2020). pymoo: Multi-objective optimization in Python. IEEE Access, 8, 89497–89509.",
        "Virtanen, P., et al. (2020). SciPy 1.0: Fundamental algorithms for scientific computing in Python. Nature Methods, 17, 261–272.",
        "Wu, K., Lu, S., Chen, H., Feng, M., & Lu, Z. (2024). An energy-efficient logistic drone routing method considering dynamic drone speed and payload. Sustainability, 16(12), 4995.",
        "Ji, Y., Liu, L., Wang, Y., Wang, X. V., & Wang, L. (2026). Time-efficient routing and speed control for truck drone delivery under non-linear energy constraints. Drones, 10(6), 466.",
        "UAV Industry Benchmark (2026). Team-compiled dataset of 50 UAV products from official specification sheets (UAV_Industry_Benchmark_v2.xlsx)."]
d.rich(s, I(0.5), I(1.2), I(12.3), I(5.2), refs, size=13, space=6)

d.finalize_template()
d.save(OUT, title="EL Phase-II: " + team.TITLE)
print("saved", OUT, "slides:", len(d.prs.slides))
