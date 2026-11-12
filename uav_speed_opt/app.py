"""What-if dashboard for UAV flight-speed optimisation.  Run:  streamlit run app.py"""
from dataclasses import replace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from uav_opt.benchmark import CATEGORIES, category_uav, load_rows
from uav_opt.model import UAV, Mission, budget_from_endurance, evaluate
from uav_opt.optimize import grid_search, nsga2, weighted_sum_scipy

st.set_page_config(page_title="UAV Speed Optimiser", layout="wide")
NAVY, RED, TEAL = "#5B9BFF", "#FF5C5C", "#2EC4B6"  # bright accents for the dark theme
BAND, MARK, GOLD = "#33415C", "#E6E9EF", "#F2C14E"
DARK = dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")


@st.cache_data
def bench():
    return load_rows()


rows = bench()
st.title("UAV Flight-Speed Optimiser")
st.caption("Minimise energy and delivery time subject to a reliability constraint. Category defaults come from the "
           "UAV Industry Benchmark (medians of free-flight multirotors).")

with st.sidebar:
    st.header("Drone")
    cat = st.selectbox("Benchmark category", list(CATEGORIES), format_func=CATEGORIES.get, index=1)
    base, meta = category_uav(rows[cat])
    mass = st.number_input("Take-off mass (kg)", 0.3, 200.0, float(round(base.mass_kg, 2)), 0.1)
    payload = st.slider("Extra payload (kg)", 0.0, max(1.0, round(mass, 1)), 0.0, 0.1)
    vmax = st.slider("Max speed Vmax (m/s)", 5.0, 40.0, float(round(base.v_max, 1)), 0.5)
    endurance = st.slider("Published flight time (min)", 5.0, 120.0, float(meta["endurance_min"]), 1.0)
    st.header("Mission")
    dist = st.slider("Distance (km)", 0.5, 30.0, 5.0, 0.5)
    wind = st.slider("Headwind (m/s)", 0.0, 12.0, 0.0, 0.5)
    rmin = st.slider("Required reliability R_min", 0.980, 0.9995, 0.995, 0.0005, format="%.4f")
    w = st.slider("Weight on energy w (1-w on time)", 0.0, 1.0, 0.5, 0.05)
    with st.expander("Reliability model (assumption)"):
        lam0 = st.number_input("lambda0 (failures / flight-hour)", 0.0001, 0.2, float(round(base.lam0, 4)), 0.001, format="%.4f")
        k = st.slider("Speed-stress factor k", 0.0, 10.0, 2.0, 0.5)
    algo = st.radio("Optimiser", ["Grid search", "Weighted sum (SciPy)", "NSGA-II (pymoo)"], index=0)

uav = UAV(mass_kg=mass, v_max=vmax, battery_kJ=budget_from_endurance(mass, endurance), lam0=lam0, k=k).with_payload(payload)
mission = Mission(distance_km=dist, headwind_ms=wind, r_min=rmin)
res = {"Grid search": grid_search, "Weighted sum (SciPy)": weighted_sum_scipy, "NSGA-II (pymoo)": nsga2}[algo](uav, mission, w)

if res.v_star is None:
    st.error("No feasible speed: the mission violates the battery or reliability constraint. Shorten the distance, "
             "reduce payload/headwind or relax R_min.")
    st.stop()

pt = evaluate(np.array([res.v_star]), uav, mission)
c = st.columns(5)
c[0].metric("Recommended speed V*", f"{res.v_star:.1f} m/s", f"{res.v_star*3.6:.0f} km/h", delta_color="off")
c[1].metric("Energy", f"{pt['E_kJ'][0]:.1f} kJ", f"{100*pt['E_kJ'][0]/uav.battery_kJ:.0f}% of usable battery", delta_color="off")
c[2].metric("Delivery time", f"{pt['T_min'][0]:.1f} min")
c[3].metric("Mission reliability", f"{pt['R'][0]:.4f}")
c[4].metric("Pareto range V_E*–V_T*", f"{res.v_energy:.1f}–{res.v_time:.1f} m/s" if res.v_energy else "-", f"{algo}: {res.runtime_ms:.1f} ms", delta_color="off")

V = np.arange(0.5, vmax + 1e-9, 0.05)
ev = evaluate(V, uav, mission)
feas = ev["feasible"]
fig = make_subplots(rows=1, cols=3, subplot_titles=("Energy E(V) [kJ]", "Time T(V) [min]", "Reliability R(V)"))
for i, (key, col) in enumerate([("E_kJ", NAVY), ("T_min", TEAL), ("R", RED)], start=1):
    y = np.where(np.isfinite(ev[key]), ev[key], None)
    fig.add_trace(go.Scatter(x=V, y=y, mode="lines", line=dict(color=col, width=3), showlegend=False), 1, i)
    if feas.any():
        fig.add_vrect(x0=V[feas].min(), x1=V[feas].max(), fillcolor=BAND, opacity=0.45, layer="below", line_width=0, row=1, col=i)
    fig.add_vline(x=res.v_star, line_dash="dash", line_color=MARK, row=1, col=i)
fig.add_hline(y=rmin, line_dash="dot", line_color=RED, row=1, col=3)
fig.add_hline(y=uav.battery_kJ, line_dash="dot", line_color=NAVY, row=1, col=1)
fig.update_yaxes(range=[0, min(float(np.nanmax(np.where(np.isfinite(ev['E_kJ']), ev['E_kJ'], np.nan))), 4 * pt["E_kJ"][0])], row=1, col=1)
fig.update_yaxes(range=[max(0.95, float(np.nanmin(ev["R"]))), 1.0], row=1, col=3)
fig.update_xaxes(title_text="Airspeed V (m/s)")
fig.update_layout(height=360, margin=dict(t=40, b=10, l=10, r=10), **DARK)
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns([1, 1])
with left:
    st.subheader("Energy-time Pareto front")
    pf = feas & (V >= (res.v_energy or 0))
    f2 = go.Figure()
    f2.add_trace(go.Scatter(x=ev["T_min"][feas], y=ev["E_kJ"][feas], mode="lines", line=dict(color="#8A93A6"), name="feasible"))
    f2.add_trace(go.Scatter(x=ev["T_min"][pf], y=ev["E_kJ"][pf], mode="lines", line=dict(color=NAVY, width=4), name="Pareto front"))
    f2.add_trace(go.Scatter(x=pt["T_min"], y=pt["E_kJ"], mode="markers", marker=dict(symbol="star", size=16, color=GOLD), name="V*"))
    f2.update_layout(height=320, xaxis_title="Time (min)", yaxis_title="Energy (kJ)", margin=dict(t=10), **DARK)
    st.plotly_chart(f2, use_container_width=True)
with right:
    st.subheader(f"Benchmark: {CATEGORIES[cat]}")
    cols = ["Company", "Flagship model", "Airframe", "MTOW / TOW (kg)", "Max flight time (min)", "Max speed (m/s)",
            "Wind resistance (m/s)", "Robustness score (/100)"]
    st.dataframe(pd.DataFrame(rows[cat])[cols].fillna("–").astype(str), hide_index=True, height=320)

st.caption("Power model: Zeng, Xu & Zhang (2019). Reliability model is illustrative (after Petritoli et al., 2018): "
           "no surveyed company publishes failure-rate data.")
