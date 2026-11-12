"""Build the EL Phase-I deck on the SDG-P1 template (Problem Definition x4, Objectives x4, Methodology x2)."""
import sys
from pathlib import Path

from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from deckkit import Deck, RED, NAVY, GREY, INK, TINT, TINT2, GREEN, AMBER, WHITE, FONT
import team

EL = Path(__file__).resolve().parents[1]
TEMPLATE = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "templates" / "SDG-P1_Template.pptx")
OUT = sys.argv[2] if len(sys.argv) > 2 else str(EL / "SDG9_Phase1_UAV.pptx")
I = Inches

d = Deck(TEMPLATE)
d.fill_title(team.TITLE, team.TEAM_NO, team.TEAM_NAME, team.MEMBERS)
d.fill_outline("EL Phase-I", [("Problem Definition", "background, problem statement, industry context, research gap"),
                              ("Objectives", "main objective and four specific objectives"),
                              ("Methodology", "models, formulation and workflow"),
                              ("References", "")])

# ======================= PROBLEM DEFINITION =======================
S = "Problem Definition"
s = d.slide("Background: UAVs and the Three-Way Trade-off", S)
d.rich(s, I(0.5), I(1.25), I(6.4), I(4.9), [
    [("UAVs are now infrastructure: ", {"bold": True, "color": NAVY}), ("parcel and medical delivery, disaster relief, agriculture, surveillance, mapping and inspection.", {})],
    [("Every mission trades off three things: ", {"bold": True, "color": NAVY}), ("battery energy, delivery time and mission reliability.", {})],
    [("Batteries are the bottleneck: ", {"bold": True, "color": NAVY}), ("small multirotors fly only tens of minutes per charge.", {})],
    [("Flight speed is the one control knob ", {"bold": True, "color": NAVY}), ("that links all three goals: too slow wastes energy hovering, too fast raises drag and risk.", {})],
    [("SDG 9 relevance: ", {"bold": True, "color": RED}), ("efficient, reliable drone operations support resilient infrastructure and industrial innovation.", {})]], size=16, space=10)
for i, (hd, sb, col) in enumerate([("Energy", "battery consumed per mission", NAVY), ("Time", "delivery / response time", GREEN), ("Reliability", "probability of mission success", RED)]):
    d.node(s, I(7.6), I(1.35 + i * 1.6), I(3.2), I(1.25), hd, sb, fill=col, size=20)
d.node(s, I(11.1), I(2.95), I(1.7), I(1.25), "Speed V", "decision variable", fill=AMBER, size=16)
for i in range(3):
    d.arrow(s, I(11.1), I(3.58), I(10.8), I(1.98 + i * 1.6), color=GREY)

s = d.slide("Problem Statement", S)
d.box(s, I(0.5), I(1.25), I(5.9), I(1.75), TINT)
d.rich(s, I(0.65), I(1.35), I(5.6), I(1.6), [
    [("For a given UAV and mission ", {"bold": True, "color": NAVY}), ("(distance, payload, battery), find the flight speed that minimises energy and delivery time while keeping mission reliability above a required threshold.", {})]],
    size=18, bullet=False)
d.rich(s, I(0.5), I(3.3), I(5.9), I(2.9), [
    [("Conflicting objectives: ", {"bold": True, "color": NAVY}), ("the energy-optimal speed is not the time-optimal speed.", {})],
    [("Hard constraints: ", {"bold": True, "color": NAVY}), ("battery capacity, maximum speed and a minimum reliability.", {})],
    [("Today: ", {"bold": True, "color": NAVY}), ("operators pick speeds by rule of thumb.", {})]], size=15)
cd = CategoryChartData()
speeds = [4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
energy = [188.3, 114.5, 80.6, 63.0, 53.3, 47.8, 45.1, 44.2, 44.6, 46.0, 48.4, 51.4, 55.1, 59.4]
cd.categories = [str(v) for v in speeds]
cd.add_series("Energy for a 5 km mission (kJ)", energy)
gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, I(6.7), I(1.2), I(6.2), I(4.4), cd)
ch = gf.chart
ch.has_title = True; ch.chart_title.text_frame.text = "Energy for a 5 km mission vs speed"
ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14); ch.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
ch.has_legend = False
ser = ch.plots[0].series[0]; ser.format.line.color.rgb = RED; ser.format.line.width = Pt(2.5); ser.smooth = True
ser.marker.format.fill.solid(); ser.marker.format.fill.fore_color.rgb = RED; ser.marker.format.line.color.rgb = RED
ca, va = ch.category_axis, ch.value_axis
ca.has_title = True; ca.axis_title.text_frame.text = "Flight speed (m/s)"
va.has_title = True; va.axis_title.text_frame.text = "Energy (kJ)"
for ax in (ca, va):
    ax.tick_labels.font.size = Pt(11); ax.tick_labels.font.color.rgb = GREY
    ax.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(11)
va.major_gridlines.format.line.color.rgb = TINT
d.text(s, I(6.7), I(5.65), I(6.2), I(0.7), "Rotary-wing power model (Zeng et al., 2019). Too slow and too fast both waste energy; the minimum is near 18 m/s, "
       "but faster flights finish sooner.", size=11, color=GREY, italic=True)

s = d.slide("Why It Matters: Consequences and Context", S)
for i, (v, l) in enumerate([("7–70 min", "published multirotor flight times (agri → surveillance)"), ("3", "objectives that conflict"), ("0", "companies publishing failure-rate data")]):
    d.stat(s, I(0.6 + i * 4.15), I(1.3), I(3.8), v, l, vsize=34)
cards = [("If speed is chosen badly", ["Mid-mission battery depletion and forced landings", "Late deliveries in time-critical missions (medical, SAR)", "Higher failure risk and lost payloads"]),
         ("Who is affected", ["Delivery and logistics operators", "Disaster-response and public-safety teams", "Agricultural and industrial drone service providers"]),
         ("Why now", ["Rapid growth of drone delivery and inspection", "Regulators demand demonstrable safety margins", "Energy efficiency = lower cost and emissions"])]
for i, (hd, lines) in enumerate(cards):
    d.card(s, I(0.5 + i * 4.15), I(2.85), I(3.95), I(3.3), hd, lines, size=14, fill=TINT if i else TINT2, head_color=RED if i == 0 else NAVY)

s = d.slide("Literature Survey and Research Gap", S)
rows = [["Authors (Year)", "Key contribution", "Relevance to our project"],
        ["Wu & Lu (2024), Sustainability", "Speed as a decision variable; ~21% energy saved vs fixed speed", "Optimising speed saves energy"],
        ["Ji & Liu (2026), Drones", "Speed control cuts makespan by up to 17.5%", "Speed drives delivery time"],
        ["Peng & Cao (2025), IEEE IoT-J", "Energy vs communication-outage trade-off", "Same energy-vs-reliability tension"],
        ["Wu & Wang (2026), IEEE TMLCN", "Weighted sum of delivery and outage time", "Weighted-sum objective we adopt"],
        ["Xiao & Qiao (2025), Drones", "Bayesian-network propulsion reliability", "Reliability as a modelled objective"],
        ["Huang & Hu (2024), Applied Sciences", "Evolutionary multi-objective UAV planner", "Supports our NSGA-II Pareto approach"]]
d.table(s, I(0.5), I(1.2), I(12.3), rows, col_w=[3.2, 5.0, 4.1], size=13, head_size=13, row_h=0.5, bold_first=True)
d.box(s, I(0.5), I(5.0), I(12.3), I(1.25), TINT2)
d.text(s, I(0.7), I(5.1), I(11.9), I(1.1), "Research gap: most work optimises energy OR time; reliability is rarely co-optimised with both, "
       "and few studies give planners an interactive tool to explore the trade-off.", size=16, bold=True, color=RED, font=FONT)

# ======================= OBJECTIVES =======================
S = "Objectives"
s = d.slide("Main Objective", S)
d.box(s, I(0.5), I(1.3), I(12.3), I(1.5), TINT)
d.text(s, I(0.7), I(1.4), I(11.9), I(1.3), "Build a simulation-and-optimisation system that recommends the optimal feasible UAV flight speed, "
       "balancing energy consumption, delivery time and mission reliability.", size=20, bold=True, color=NAVY, font=FONT)
for i, (n, hd, sb) in enumerate([("1", "Model", "energy, time and reliability vs speed"), ("2", "Formulate", "constrained multi-objective problem"),
                                 ("3", "Optimise", "compare grid, weighted sum, NSGA-II"), ("4", "Decide", "interactive what-if dashboard")]):
    cx = I(0.5 + i * 3.1)
    d.node(s, cx, I(3.2), I(2.9), I(1.3), f"Objective {n}: {hd}", sb, fill=NAVY if i < 3 else RED, size=16)
d.rich(s, I(0.5), I(4.85), I(12.3), I(1.4), [
    [("Success criteria: ", {"bold": True, "color": NAVY}), ("model reproduces published power-model values; optimisers agree; recommended speed always satisfies battery and reliability limits.", {})],
    [("Contribution: ", {"bold": True, "color": NAVY}), ("a reproducible computational tool that makes the energy–time–reliability trade-off explicit (SDG 9).", {})]], size=15)

s = d.slide("Objectives 1 and 2: Model and Formulate", S)
d.card(s, I(0.5), I(1.25), I(6.05), I(3.3), "Objective 1: Model the UAV", [
    "Energy E(V) from a published rotary-wing power model",
    "Delivery time T(V) = D / V",
    "Reliability R(V) = exp(−λ(V)·T(V)) with a speed-dependent failure rate",
    "Inputs: distance, payload, battery capacity, maximum speed"], size=15)
d.card(s, I(6.75), I(1.25), I(6.05), I(3.3), "Objective 2: Formulate the problem", [
    "Decision variable: cruise speed V",
    "Objectives: minimise E(V) and T(V)",
    "Constraints: R(V) ≥ R_min, E(V) ≤ η·E_battery, V_min ≤ V ≤ V_max",
    "Output: feasible speed range and the Pareto front"], size=15, fill=TINT2, head_color=RED)
d.box(s, I(0.5), I(4.8), I(12.3), I(1.35), WHITE, line=NAVY)
d.text(s, I(0.7), I(4.9), I(11.9), I(1.15), "min  { E(V), T(V) }    subject to    R(V) ≥ R_min,   E(V) ≤ η·E_battery,   V_min ≤ V ≤ V_max",
       size=20, bold=True, color=NAVY, font=FONT, align=PP_ALIGN.CENTER, anchor=__import__("pptx.enum.text", fromlist=["MSO_ANCHOR"]).MSO_ANCHOR.MIDDLE)

s = d.slide("Objective 3: Optimise and Compare Algorithms", S)
for i, (hd, body, use) in enumerate([("Grid search", "Evaluate every candidate speed and filter infeasible ones.", "Exact baseline"),
                                     ("Weighted sum", "Combine normalised E and T with a preference weight w; solve with SciPy.", "Single recommended speed"),
                                     ("NSGA-II", "Evolutionary multi-objective search (Deb et al., 2002) via pymoo.", "Full Pareto front")]):
    cx = I(0.5 + i * 4.15)
    d.card(s, cx, I(1.3), I(3.95), I(2.6), hd, [body], size=15)
    d.chip(s, cx + I(0.2), I(3.45), I(2.4), use, fill=NAVY, size=11)
d.rich(s, I(0.5), I(4.3), I(12.3), I(2.0), [
    [("Compare on: ", {"bold": True, "color": NAVY}), ("agreement of the recommended speed, number of evaluations and runtime.", {})],
    [("Analyse: ", {"bold": True, "color": NAVY}), ("sensitivity of the optimum to payload, distance and wind.", {})],
    [("Expected insight: ", {"bold": True, "color": NAVY}), ("how much energy is saved for each minute of extra delivery time.", {})]], size=16)

s = d.slide("Objective 4: Decision Tool and Expected Outcomes", S)
d.card(s, I(0.5), I(1.25), I(6.05), I(3.0), "Objective 4: What-if dashboard", [
    "Streamlit / Plotly interface for planners",
    "Change payload, distance, battery or reliability target and see the new optimal speed",
    "Visualise E(V), T(V), R(V) and the Pareto front",
    "Optional ML layer: learn energy / reliability from flight data"], size=15)
d.card(s, I(6.75), I(1.25), I(6.05), I(3.0), "Expected outcomes", [
    "Working simulator + optimiser with a recommended speed per mission",
    "Quantified energy-vs-time trade-off",
    "Avoids battery depletion and meets reliability targets",
    "Can plug into route-planning systems; paper draft"], size=15, fill=TINT2, head_color=RED)
for i, (wk, hd) in enumerate([("Weeks 1–2", "Literature survey"), ("Weeks 3–5", "Simulation model"), ("Weeks 6–8", "Optimisation"),
                              ("Weeks 9–11", "Dashboard & testing"), ("Weeks 12–13", "Closure")]):
    cx = I(0.5 + i * 2.5)
    d.node(s, cx, I(4.6), I(2.3), I(1.3), wk, hd, fill=NAVY if i < 4 else RED, size=15)
    if i < 4: d.arrow(s, cx + I(2.3), I(5.25), cx + I(2.5), I(5.25))
d.text(s, I(0.5), I(6.0), I(12.3), I(0.35), "Project timeline (13 weeks)", size=12, color=GREY, italic=True, align=PP_ALIGN.CENTER)

# ======================= METHODOLOGY =======================
S = "Methodology"
s = d.slide("Methodology: Models, Data and Tools", S)
d.rich(s, I(0.5), I(1.25), I(12.3), I(5.0), [
    [("Design: ", {"bold": True, "color": NAVY}), ("quantitative, simulation-based study.", {})],
    [("Data: ", {"bold": True, "color": NAVY}), ("mission inputs (distance, payload, battery); published UAV power-model coefficients; public UAV specifications and flight datasets for validation.", {})],
    [("Models: ", {"bold": True, "color": NAVY}), ("E(V) = P(V)·D / V,   T(V) = D / V,   R(V) = exp(−λ(V)·T(V))", {"font": FONT})],
    [("Optimisation: ", {"bold": True, "color": NAVY}), ("minimise {E, T}  subject to  R ≥ R_min,  E ≤ η·E_battery,  V_min ≤ V ≤ V_max", {"font": FONT})],
    [("Analysis: ", {"bold": True, "color": NAVY}), ("Pareto-front comparison, sensitivity to payload and battery, algorithm runtime.", {})],
    [("Tools: ", {"bold": True, "color": NAVY}), ("Python (NumPy, SciPy, pymoo), Streamlit / Plotly dashboard, scikit-learn for the optional ML layer.", {})]], size=19, space=16)

s = d.slide("Methodology: Workflow", S)
row1 = [("Mission inputs", "distance, payload, battery"), ("Simulation model", "UAV power & flight physics"), ("Energy / Time / Reliability", "per candidate speed")]
row2 = [("Optimal feasible speed", "recommended operating point"), ("Optimisation algorithm", "weighted sum · NSGA-II"), ("Constraint filtering", "battery, reliability, Vmax")]
wN, hN = I(3.5), I(1.15)
for i, (hd, sb) in enumerate(row1):
    x = I(0.8 + i * 4.1); d.node(s, x, I(1.45), wN, hN, hd, sb, size=16)
    if i < 2: d.arrow(s, x + wN, I(1.45) + hN / 2, x + I(4.1), I(1.45) + hN / 2)
d.arrow(s, I(0.8 + 2 * 4.1) + wN / 2, I(1.45) + hN, I(0.8 + 2 * 4.1) + wN / 2, I(3.15))
for i, (hd, sb) in enumerate(row2):
    x = I(0.8 + i * 4.1); d.node(s, x, I(3.15), wN, hN, hd, sb, fill=RED if i == 0 else NAVY, size=16)
    if i > 0: d.arrow(s, x, I(3.15) + hN / 2, x - I(0.6), I(3.15) + hN / 2)
d.node(s, I(0.8), I(4.85), I(7.6), I(1.0), "Visualisation dashboard", "Pareto front, what-if analysis", fill=TINT, color=NAVY, size=16)
d.arrow(s, I(0.8) + wN / 2, I(3.15) + hN, I(0.8) + wN / 2, I(4.85))
d.node(s, I(8.9), I(4.85), I(3.9), I(1.0), "Optional: ML extension", "learn E / R from UAV datasets", fill=TINT2, color=RED, size=15)

s = d.slide("References", None)
refs = ["Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. IEEE Trans. Evolutionary Computation, 6(2), 182–197.",
        "Huang, G., Hu, M., Yang, X., Wang, Y., & Lin, P. (2024). A two-stage co-evolution multi-objective evolutionary algorithm for UAV trajectory planning. Applied Sciences, 14(15), 6516.",
        "Ji, Y., Liu, L., Wang, Y., Wang, X. V., & Wang, L. (2026). Time-efficient routing and speed control for truck drone delivery under non-linear energy constraints. Drones, 10(6), 466.",
        "Peng, H., Cao, J., Yang, D., Li, C., Luan, T. H., & Su, Z. (2025). Balancing energy efficiency and communication quality in UAV cargo delivery systems. IEEE Internet of Things Journal, 12(16), 34019–34034.",
        "Petritoli, E., Leccese, F., & Ciani, L. (2018). Reliability and maintenance analysis of unmanned aerial vehicles. Sensors, 18(9), 3171.",
        "Wu, F., Wang, Z., Cao, J., et al. (2026). Radio map-based delivery sequence design and trajectory optimization in UAV cargo delivery systems. IEEE Trans. Machine Learning in Commun. and Networking, 4, 17–32.",
        "Wu, K., Lu, S., Chen, H., Feng, M., & Lu, Z. (2024). An energy-efficient logistic drone routing method considering dynamic drone speed and payload. Sustainability, 16(12), 4995.",
        "Xiao, N., Qiao, X., Chen, X., & Li, B. (2025). Reliability analysis of multi-rotor drone electric propulsion system considering controllability and FDEP. Drones, 9(8), 572.",
        "Zeng, Y., Xu, J., & Zhang, R. (2019). Energy minimization for wireless communication with rotary-wing UAV. IEEE Trans. Wireless Communications, 18(4), 2329–2345."]
d.rich(s, I(0.5), I(1.2), I(12.3), I(5.2), refs, size=12, space=5)

d.finalize_template()
d.save(OUT, title="EL Phase-I: " + team.TITLE)
print("saved", OUT, "slides:", len(d.prs.slides))
