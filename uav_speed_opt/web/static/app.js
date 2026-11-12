const ORDER = ["Delivery", "SAR", "Agricultural", "Surveillance", "Mapping", "Inspection"];
const SHORT = { Delivery: "Delivery", SAR: "Disaster & SAR", Agricultural: "Agriculture", Surveillance: "Surveillance", Mapping: "Mapping", Inspection: "Inspection" };
const C = { cyan: "#3DD6F5", blue: "#5B9BFF", coral: "#FF6B6B", amber: "#F5B841", green: "#3DDC97", muted: "#8A97AD", grid: "#1E2A40", band: "rgba(91,155,255,0.13)" };
const state = { cat: "SAR", algo: "grid", p: { payload: 0, distance: 5, headwind: 0, rmin: 0.995, w: 0.5, k: 2 } };
let CATS = {}, timer = null, ctrl = null;
const $ = (id) => document.getElementById(id);
const fmt = (x, dp = 1) => (x == null || Number.isNaN(x) ? "–" : Number(x).toFixed(dp));

/* ---------- sliders ---------- */
const sliders = {};
document.querySelectorAll(".slider").forEach((el) => {
  const key = el.dataset.key, dp = +(el.dataset.dp ?? (String(el.dataset.step).split(".")[1] || "").length);
  el.innerHTML = `<div class="top"><span>${el.dataset.label}</span><output></output></div>
    <input type="range" min="${el.dataset.min}" max="${el.dataset.max}" step="${el.dataset.step}">`;
  const input = el.querySelector("input"), out = el.querySelector("output");
  const show = () => (out.textContent = `${(+input.value).toFixed(dp)} ${el.dataset.unit}`.trim());
  input.addEventListener("input", () => { state.p[key] = +input.value; show(); schedule(); });
  sliders[key] = { set(v) { input.value = v; state.p[key] = +input.value; show(); }, input };
});
function setSlider(key, v) { sliders[key].set(v); }

/* ---------- categories ---------- */
async function init() {
  CATS = await (await fetch("/api/categories")).json();
  const box = $("cats");
  ORDER.forEach((k) => {
    const b = document.createElement("button");
    b.className = "chip"; b.textContent = SHORT[k]; b.dataset.cat = k;
    b.onclick = () => selectCat(k);
    box.appendChild(b);
  });
  ["payload", "distance", "headwind", "rmin", "w", "k"].forEach((k) => setSlider(k, state.p[k]));
  selectCat(state.cat);
}
function selectCat(k) {
  state.cat = k;
  document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", c.dataset.cat === k));
  const d = CATS[k].defaults;
  sliders.mass.input.max = Math.max(120, Math.ceil(d.mass * 1.5));
  setSlider("mass", d.mass); setSlider("vmax", d.vmax); setSlider("endurance", d.endurance); setSlider("lam0", d.lam0);
  renderBenchmark(k);
  schedule(0);
}
$("reset").onclick = () => { ["payload", "distance", "headwind", "rmin", "w", "k"].forEach((k) => setSlider(k, { payload: 0, distance: 5, headwind: 0, rmin: 0.995, w: 0.5, k: 2 }[k])); selectCat(state.cat); };
document.querySelectorAll("#algos button").forEach((b) => (b.onclick = () => {
  state.algo = b.dataset.algo;
  document.querySelectorAll("#algos button").forEach((x) => x.classList.toggle("on", x === b));
  schedule(0);
}));

/* ---------- optimise ---------- */
function schedule(ms = 120) { clearTimeout(timer); timer = setTimeout(run, ms); }
async function run() {
  if (ctrl) ctrl.abort();
  ctrl = new AbortController();
  try {
    const r = await fetch("/api/optimize", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...state.p, algo: state.algo }), signal: ctrl.signal });
    render(await r.json());
  } catch (e) { if (e.name !== "AbortError") console.error(e); }
}

function render(d) {
  $("infeasible").hidden = d.ok; $("resultHero").style.opacity = d.ok ? 1 : 0.35;
  $("algoTag").textContent = `${d.algo} · ${fmt(d.runtime_ms, d.runtime_ms < 10 ? 2 : 0)} ms · ${d.evaluations} evals`;
  const vmax = state.p.vmax;
  $("sbMax").textContent = `${fmt(vmax)} m/s (Vmax)`;
  if (d.ok) {
    $("vStar").textContent = fmt(d.v_star);
    $("vStarKmh").textContent = `${fmt(d.v_star * 3.6, 0)} km/h · trade-off zone ${fmt(d.v_energy)}–${fmt(d.v_time)} m/s`;
    const pct = (v) => `${(100 * v) / vmax}%`;
    Object.assign($("sbBand").style, { left: pct(d.feasible_min), width: `${(100 * (d.feasible_max - d.feasible_min)) / vmax}%` });
    Object.assign($("sbPareto").style, { left: pct(d.v_energy), width: `max(4px, ${(100 * (d.v_time - d.v_energy)) / vmax}%)` });
    $("sbStar").style.left = pct(d.v_star);
    $("mE").textContent = `${fmt(d.E, d.E < 100 ? 1 : 0)} kJ`;
    $("mEbar").style.width = `${Math.min(100, d.energy_pct)}%`;
    $("mEsub").textContent = `${fmt(d.energy_pct, 0)}% of usable battery (${fmt(d.battery_kJ, 0)} kJ)`;
    $("mT").textContent = `${fmt(d.T, 1)} min`;
    $("mTsub").textContent = `${fmt(state.p.distance, 1)} km at ${fmt(d.v_star - state.p.headwind)} m/s ground speed`;
    $("mR").textContent = fmt(d.R, 4);
    $("mRsub").innerHTML = `target ≥ ${fmt(state.p.rmin, 4)} <span class="good">✓</span>`;
    if (d.baseline && d.baseline.energy_saved != null) {
      $("mS").textContent = `${fmt(100 * d.baseline.energy_saved, 0)}%`;
      $("mSsub").textContent = d.baseline.time_saved != null ? `and ${fmt(100 * d.baseline.time_saved, 0)}% faster than a fixed 10 m/s` : "vs a fixed 10 m/s";
    } else { $("mS").textContent = "–"; $("mSsub").textContent = "10 m/s is above Vmax or into the headwind"; }
  } else {
    ["vStar", "mE", "mT", "mR", "mS"].forEach((id) => ($(id).textContent = "–"));
    ["mEsub", "mTsub", "mRsub", "mSsub"].forEach((id) => ($(id).textContent = ""));
    $("vStarKmh").textContent = "no speed satisfies the constraints";
  }
  drawCurves(d); drawPareto(d);
}

/* ---------- charts ---------- */
const base = (title, ytitle) => ({
  title: { text: title, font: { size: 13, color: "#E6ECF5" }, x: 0.02, y: 0.97 },
  paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { color: C.muted, size: 11, family: "Inter, -apple-system, sans-serif" },
  margin: { l: 48, r: 12, t: 34, b: 38 }, showlegend: false, hovermode: "x unified",
  hoverlabel: { bgcolor: "#131C30", bordercolor: "#2A3A57", font: { color: "#E6ECF5" } },
  xaxis: { title: { text: "Airspeed V (m/s)", font: { size: 11 } }, gridcolor: C.grid, zeroline: false, linecolor: C.grid },
  yaxis: { title: { text: ytitle, font: { size: 11 } }, gridcolor: C.grid, zeroline: false, linecolor: C.grid },
});
const cfg = { displayModeBar: false, responsive: true };

function drawCurves(d) {
  const { V, E, T, R, feasible } = d.curves;
  const shapes = [];
  if (d.ok) {
    shapes.push({ type: "rect", xref: "x", yref: "paper", x0: d.feasible_min, x1: d.feasible_max, y0: 0, y1: 1, fillcolor: C.band, line: { width: 0 }, layer: "below" });
    shapes.push({ type: "line", xref: "x", yref: "paper", x0: d.v_star, x1: d.v_star, y0: 0, y1: 1, line: { color: C.amber, width: 2, dash: "dot" } });
  }
  const finite = (a) => a.filter((x) => x != null);
  const eStar = d.ok ? d.E : Math.min(...finite(E));
  const L1 = base("Energy E(V)", "kJ"); L1.shapes = [...shapes, { type: "line", xref: "paper", x0: 0, x1: 1, y0: d.battery_kJ, y1: d.battery_kJ, line: { color: C.coral, width: 1, dash: "dash" } }];
  L1.yaxis.range = [0, Math.min(Math.max(...finite(E)), eStar * 3.5)];
  Plotly.react("chE", [{ x: V, y: E, mode: "lines", line: { color: C.blue, width: 3 }, hovertemplate: "%{y:.1f} kJ<extra></extra>" }], L1, cfg);
  const L2 = base("Delivery time T(V)", "min"); L2.shapes = shapes;
  L2.yaxis.range = [0, Math.min(Math.max(...finite(T)), (d.ok ? d.T : 10) * 6)];
  Plotly.react("chT", [{ x: V, y: T, mode: "lines", line: { color: C.cyan, width: 3 }, hovertemplate: "%{y:.1f} min<extra></extra>" }], L2, cfg);
  const L3 = base("Reliability R(V)", "R"); L3.shapes = [...shapes, { type: "line", xref: "paper", x0: 0, x1: 1, y0: state.p.rmin, y1: state.p.rmin, line: { color: C.coral, width: 1, dash: "dash" } }];
  L3.yaxis.range = [Math.max(0.95, Math.min(...finite(R)), state.p.rmin - 0.01), 1]; L3.yaxis.tickformat = ".3f";
  Plotly.react("chR", [{ x: V, y: R, mode: "lines", line: { color: C.coral, width: 3 }, hovertemplate: "%{y:.4f}<extra></extra>" }], L3, cfg);
}

function drawPareto(d) {
  const { E, T, feasible } = d.curves;
  const fx = [], fy = [];
  T.forEach((t, i) => { if (feasible[i]) { fx.push(t); fy.push(E[i]); } });
  const traces = [{ x: fx, y: fy, mode: "lines", name: "feasible speeds", line: { color: C.muted, width: 1.5 }, hovertemplate: "%{x:.2f} min · %{y:.1f} kJ<extra></extra>" }];
  if (d.ok) {
    traces.push({ x: d.pareto.T, y: d.pareto.E, mode: "lines", name: "Pareto front", line: { color: C.green, width: 5 }, hovertemplate: "%{x:.2f} min · %{y:.1f} kJ<extra>Pareto</extra>" });
    if (d.nsga_points) traces.push({ x: d.nsga_points.T, y: d.nsga_points.E, mode: "markers", name: "NSGA-II solutions", marker: { color: "rgba(0,0,0,0)", size: 8, line: { color: C.coral, width: 1.5 } } });
    traces.push({ x: [d.T], y: [d.E], mode: "markers", name: "chosen V*", marker: { symbol: "star", size: 18, color: C.amber, line: { color: "#070B14", width: 1 } } });
  }
  const L = base("Energy vs delivery time", "Energy (kJ)");
  L.xaxis.title.text = "Delivery time (min)"; L.showlegend = true; L.hovermode = "closest";
  L.legend = { orientation: "h", y: -0.2, font: { color: "#C9D3E3" } }; L.margin.b = 70;
  if (d.ok) { const pe = d.pareto.E, pt = d.pareto.T;
    const xs = [...pt, d.T], ys = [...pe, d.E];
    const xr = [Math.min(...xs), Math.max(...xs)], yr = [Math.min(...ys), Math.max(...ys)];
    const padx = Math.max((xr[1] - xr[0]) * 2, 0.6), pady = Math.max((yr[1] - yr[0]) * 2, yr[0] * 0.08);
    L.xaxis.range = [xr[0] - padx * 0.4, xr[1] + padx]; L.yaxis.range = [yr[0] - pady * 0.3, yr[1] + pady];
  }
  Plotly.react("chP", traces, L, cfg);
}

/* ---------- compare ---------- */
$("compare").onclick = async () => {
  const tb = $("cmp").querySelector("tbody");
  tb.innerHTML = `<tr><td colspan="5" class="muted">Running grid search, SciPy and NSGA-II…</td></tr>`;
  const rows = await (await fetch("/api/compare", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state.p) })).json();
  tb.innerHTML = rows.map((r) => `<tr><td>${r.method}</td><td><b>${fmt(r.v_star, 2)}</b></td><td>${fmt(r.v_energy, 2)}</td>
    <td>${(r.evaluations ?? 0).toLocaleString()}</td><td>${fmt(r.runtime_ms, r.runtime_ms < 10 ? 2 : 0)} ms</td></tr>`).join("");
};

/* ---------- benchmark ---------- */
function scoreChip(s) {
  if (s == null) return "–";
  const col = s >= 60 ? C.green : s >= 30 ? C.amber : C.coral;
  return `<span class="score" style="color:${col};background:${col}1f">${Math.round(s)}</span>`;
}
function renderBenchmark(k) {
  const cat = CATS[k], m = cat.meta;
  $("bmTitle").textContent = cat.title;
  $("bmSummary").innerHTML = [
    `<b>${m.n_companies}</b> companies`, `<b>${m.n_multirotor}</b> free-flight multirotors`,
    `median mass <b>${fmt(m.mass_kg, 1)} kg</b>`, `median Vmax <b>${fmt(m.v_max, 1)} m/s</b>`,
    `median flight time <b>${fmt(m.endurance_min, 0)} min</b>`, `median robustness <b>${fmt(m.robustness, 0)}</b>/100`,
  ].map((t) => `<span class="pill">${t}</span>`).join("");
  const cols = ["Company", "Flagship model", "Airframe", "MTOW / TOW (kg)", "Max payload (kg)", "Max flight time (min)", "Max speed (m/s)", "Wind resistance (m/s)", "IP rating", "Robustness score (/100)", "Source link"];
  const head = ["Company", "Model", "Airframe", "Mass (kg)", "Payload (kg)", "Flight time (min)", "Max speed (m/s)", "Wind (m/s)", "IP", "Robustness", "Source"];
  $("bm").querySelector("thead").innerHTML = `<tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr>`;
  $("bm").querySelector("tbody").innerHTML = cat.companies.map((r) => `<tr>${cols.map((c) => {
    const v = r[c];
    if (c === "Source link") return `<td>${v && /^https?:\/\//.test(v) ? `<a href="${v}" target="_blank" rel="noopener noreferrer" title="${v}">open ↗</a>` : "–"}</td>`;
    if (c === "Robustness score (/100)") return `<td>${scoreChip(v)}</td>`;
    if (c === "Company") return `<td><b>${v}</b></td>`;
    return `<td class="${v == null ? "muted" : ""}">${v == null ? "–" : typeof v === "number" ? +v.toFixed(2) : v}</td>`;
  }).join("")}</tr>`).join("");
}

init();
