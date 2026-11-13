const ORDER = ["Delivery", "SAR", "Agricultural", "Surveillance", "Mapping", "Inspection"];
const SHORT = { Delivery: "Delivery", SAR: "Disaster & SAR", Agricultural: "Agriculture", Surveillance: "Surveillance", Mapping: "Mapping", Inspection: "Inspection" };
const C = { cyan: "#38E1FF", blue: "#5B8CFF", violet: "#8B7CFF", coral: "#FF6B7A", amber: "#FFB547", green: "#34E3A1", muted: "#93A1BA", grid: "rgba(140,170,230,0.09)", band: "rgba(139,124,255,0.12)" };
const ICONS = {
  Delivery: '<path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 7v10l9 4 9-4V7"/><path d="M12 11v10"/>',
  SAR: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M5.6 5.6l3.6 3.6M14.8 14.8l3.6 3.6M18.4 5.6l-3.6 3.6M9.2 14.8l-3.6 3.6"/>',
  Agricultural: '<path d="M12 21V11"/><path d="M12 11C12 6 8 4 4 4c0 5 3 7 8 7z"/><path d="M12 13c0-4 3-6 8-6 0 4-3 6-8 6z"/>',
  Surveillance: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  Mapping: '<path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/>',
  Inspection: '<path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/>',
};
function fill(input) { const lo = +input.min || 0, hi = +input.max || 100; input.style.setProperty("--p", `${hi > lo ? (100 * (+input.value - lo)) / (hi - lo) : 0}%`); }
window.fillRange = fill;
const state = { cat: "SAR", algo: "grid", example: null, p: { payload: 0, distance: 5, headwind: 0, rmin: 0.995, w: 0.5, k: 2 } };
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
  const show = () => { out.textContent = `${(+input.value).toFixed(dp)} ${el.dataset.unit}`.trim(); fill(input); };
  input.addEventListener("input", () => { state.p[key] = +input.value; show(); clearExample(); schedule(); });
  sliders[key] = { set(v) { input.value = v; state.p[key] = +input.value; show(); }, input };
});
function setSlider(key, v) { sliders[key].set(v); }

/* ---------- categories ---------- */
async function init() {
  CATS = await (await fetch("/api/categories")).json();
  const box = $("cats");
  ORDER.forEach((k) => {
    const b = document.createElement("button");
    b.className = "chip"; b.innerHTML = `<svg viewBox="0 0 24 24">${ICONS[k]}</svg><span>${SHORT[k]}</span>`; b.dataset.cat = k;
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
  $("hvCat").textContent = `${SHORT[k]} · benchmark median drone`;
  setSlider("mass", d.mass); setSlider("vmax", d.vmax); setSlider("endurance", d.endurance); setSlider("lam0", d.lam0);
  renderBenchmark(k);
  renderExamples(k);
  schedule(0);
}

/* ---------- example missions (3 per category; drone values stay at the benchmark defaults) ---------- */
const EXAMPLES = {
  Delivery: [
    { name: "Medicine to a rural clinic", dest: "Rural clinic", note: "2 kg of medicines over 7 km with a light headwind. Arriving quickly matters more than saving battery.", p: { payload: 2, distance: 7, headwind: 2, rmin: 0.995, w: 0.3 } },
    { name: "Last-mile parcel drop", dest: "Customer", note: "A 5 kg parcel over 3 km in calm air, with slightly more weight on saving energy.", p: { payload: 5, distance: 3, headwind: 0, rmin: 0.995, w: 0.6 } },
    { name: "Heavy cargo into wind", dest: "Cargo yard", note: "15 kg of cargo over 6 km against a 6 m/s headwind.", p: { payload: 15, distance: 6, headwind: 6, rmin: 0.995, w: 0.5 } },
  ],
  SAR: [
    { name: "Missing hiker search", dest: "Last known location", note: "Fly 6 km to the hiker's last known location as fast as possible, into a 3 m/s wind.", p: { payload: 0, distance: 6, headwind: 3, rmin: 0.995, w: 0.2 } },
    { name: "Flood life-jacket drop", dest: "Flood zone", note: "Carry a 1.5 kg life jacket 4 km in strong wind, with a stricter reliability target (0.997).", p: { payload: 1.5, distance: 4, headwind: 5, rmin: 0.997, w: 0.3 } },
    { name: "Wide-area sweep", dest: "Search grid", note: "A 9 km sweep where battery matters most, so the drone flies at its minimum-energy speed.", p: { payload: 0, distance: 9, headwind: 0, rmin: 0.995, w: 1 } },
  ],
  Agricultural: [
    { name: "Crop spraying run", dest: "Spray field", note: "A full 20 kg spray tank over a 2 km run in calm air.", p: { payload: 20, distance: 2, headwind: 0, rmin: 0.995, w: 0.7 } },
    { name: "Field scouting flight", dest: "Crop field", note: "An empty tank and a 4 km flight to check crop health.", p: { payload: 0, distance: 4, headwind: 2, rmin: 0.995, w: 0.8 } },
    { name: "Spraying in gusty wind", dest: "Spray field", note: "15 kg of spray over 1.5 km into a 5 m/s wind.", p: { payload: 15, distance: 1.5, headwind: 5, rmin: 0.995, w: 0.6 } },
  ],
  Surveillance: [
    { name: "Night perimeter patrol", dest: "Patrol complete", note: "A routine 4 km patrol of a site boundary, saving battery for a long shift.", p: { payload: 0, distance: 4, headwind: 1, rmin: 0.995, w: 0.8 } },
    { name: "Intruder alarm response", dest: "Alarm point", note: "Reach an alarm 2 km away as fast as possible, with a stricter reliability target (0.998).", p: { payload: 0, distance: 2, headwind: 0, rmin: 0.998, w: 0.1 } },
    { name: "Coastline watch in wind", dest: "Coast checkpoint", note: "A 5 km coastal patrol against a 6 m/s sea breeze.", p: { payload: 0, distance: 5, headwind: 6, rmin: 0.995, w: 0.5 } },
  ],
  Mapping: [
    { name: "Battery-saver site survey", dest: "Construction site", note: "Fly 6 km to a construction site using as little battery as possible.", p: { payload: 0, distance: 6, headwind: 0, rmin: 0.995, w: 1 } },
    { name: "Road corridor mapping", dest: "Road corridor", note: "A 10 km road corridor. The reliability target is relaxed to 0.99 so the longer flight is allowed.", p: { payload: 0, distance: 10, headwind: 0, rmin: 0.99, w: 0.6 } },
    { name: "Quarry survey in wind", dest: "Quarry", note: "A 4 km quarry survey in a 6 m/s headwind.", p: { payload: 0, distance: 4, headwind: 6, rmin: 0.995, w: 0.5 } },
  ],
  Inspection: [
    { name: "Power-line inspection", dest: "Power line", note: "Follow 10 km of power line in a light headwind.", p: { payload: 0, distance: 10, headwind: 2, rmin: 0.995, w: 0.6 } },
    { name: "Wind-turbine check", dest: "Wind turbine", note: "A 3 km flight to a wind turbine in an 8 m/s wind, with a stricter reliability target (0.998).", p: { payload: 0, distance: 3, headwind: 8, rmin: 0.998, w: 0.4 } },
    { name: "Pipeline patrol", dest: "Pipeline", note: "A 20 km pipeline patrol. The reliability target is relaxed to 0.99 to allow the long flight.", p: { payload: 0, distance: 20, headwind: 0, rmin: 0.99, w: 0.8 } },
  ],
};
function renderExamples(k) {
  const box = $("examples");
  box.innerHTML = "";
  EXAMPLES[k].forEach((ex) => {
    const b = document.createElement("button");
    b.className = "ex";
    b.innerHTML = `${ex.name}<span>${ex.p.distance} km${ex.p.payload ? ` · ${ex.p.payload} kg` : ""}</span>`;
    b.onclick = () => applyExample(k, ex, b);
    box.appendChild(b);
  });
  clearExample();
}
function applyExample(k, ex, btn) {
  const d = CATS[k].defaults;
  setSlider("mass", d.mass); setSlider("vmax", d.vmax); setSlider("endurance", d.endurance); setSlider("lam0", d.lam0); setSlider("k", 2);
  Object.entries(ex.p).forEach(([key, v]) => setSlider(key, v));
  state.example = ex;
  document.querySelectorAll(".ex").forEach((x) => x.classList.toggle("on", x === btn));
  $("exNote").textContent = ex.note; $("exNote").hidden = false;
  schedule(0);
}
function clearExample() {
  state.example = null;
  document.querySelectorAll(".ex.on").forEach((x) => x.classList.remove("on"));
  $("exNote").hidden = true;
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
  $("hvV").textContent = d.ok ? fmt(d.v_star) : "–";
  $("hvE").textContent = d.ok && d.baseline && d.baseline.energy_saved != null ? `${fmt(100 * d.baseline.energy_saved, 0)}%` : "–";
  $("hvR").textContent = d.ok ? fmt(d.R, 4) : "–";
  $("hvCat").textContent = `${SHORT[state.cat]} · ${fmt(state.p.distance)} km${state.p.headwind ? ` · ${fmt(state.p.headwind)} m/s wind` : ""}`;
  drawCurves(d); drawPareto(d);
  if (window.updateReplay) window.updateReplay(d);
}

/* ---------- charts ---------- */
const base = (title, ytitle) => ({
  title: { text: title, font: { size: 13, color: "#EAF0FA", family: "Space Grotesk, Inter, sans-serif" }, x: 0.03, y: 0.96 },
  paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { color: C.muted, size: 11, family: "Inter, -apple-system, sans-serif" }, transition: { duration: 250, easing: "cubic-in-out" },
  margin: { l: 48, r: 12, t: 34, b: 38 }, showlegend: false, hovermode: "x unified",
  hoverlabel: { bgcolor: "#0B1222", bordercolor: "#38E1FF", font: { color: "#EAF0FA", family: "JetBrains Mono, monospace" } },
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
  Plotly.react("chE", [{ x: V, y: E, mode: "lines", line: { color: C.blue, width: 3, shape: "spline" }, fill: "tozeroy", fillcolor: "rgba(91,140,255,0.10)", hovertemplate: "%{y:.1f} kJ<extra></extra>" }], L1, cfg);
  const L2 = base("Delivery time T(V)", "min"); L2.shapes = shapes;
  L2.yaxis.range = [0, Math.min(Math.max(...finite(T)), (d.ok ? d.T : 10) * 6)];
  Plotly.react("chT", [{ x: V, y: T, mode: "lines", line: { color: C.cyan, width: 3, shape: "spline" }, fill: "tozeroy", fillcolor: "rgba(56,225,255,0.08)", hovertemplate: "%{y:.1f} min<extra></extra>" }], L2, cfg);
  const L3 = base("Reliability R(V)", "R"); L3.shapes = [...shapes, { type: "line", xref: "paper", x0: 0, x1: 1, y0: state.p.rmin, y1: state.p.rmin, line: { color: C.coral, width: 1, dash: "dash" } }];
  L3.yaxis.range = [Math.max(0.95, Math.min(...finite(R)), state.p.rmin - 0.01), 1]; L3.yaxis.tickformat = ".3f";
  Plotly.react("chR", [{ x: V, y: R, mode: "lines", line: { color: C.violet, width: 3, shape: "spline" }, hovertemplate: "%{y:.4f}<extra></extra>" }], L3, cfg);
}

function drawPareto(d) {
  const { E, T, feasible } = d.curves;
  const fx = [], fy = [];
  T.forEach((t, i) => { if (feasible[i]) { fx.push(t); fy.push(E[i]); } });
  const traces = [{ x: fx, y: fy, mode: "lines", name: "feasible speeds", line: { color: C.muted, width: 1.5 }, hovertemplate: "%{x:.2f} min · %{y:.1f} kJ<extra></extra>" }];
  if (d.ok) {
    traces.push({ x: d.pareto.T, y: d.pareto.E, mode: "lines", name: "Pareto front", line: { color: C.green, width: 5 }, hovertemplate: "%{x:.2f} min · %{y:.1f} kJ<extra>Pareto</extra>" });
    if (d.nsga_points) traces.push({ x: d.nsga_points.T, y: d.nsga_points.E, mode: "markers", name: "NSGA-II solutions", marker: { color: "rgba(0,0,0,0)", size: 8, line: { color: C.coral, width: 1.5 } } });
    traces.push({ x: [d.T], y: [d.E], mode: "markers", name: "chosen V*", marker: { symbol: "star", size: 20, color: C.amber, line: { color: "#04070F", width: 1 } } });
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

/* ---------- page polish: active nav link + reveal on scroll ---------- */
(() => {
  const links = [...document.querySelectorAll(".nav nav a")];
  const secs = links.map((a) => document.querySelector(a.getAttribute("href"))).filter(Boolean);
  const spy = () => {
    const y = window.scrollY + 120; let cur = null;
    secs.forEach((s) => { if (s.offsetTop <= y) cur = s.id; });
    links.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${cur}`));
  };
  window.addEventListener("scroll", spy, { passive: true }); spy();
  if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: 0.08 });
  document.querySelectorAll(".section-head, .hero-stats, .rp-bar, .rp-panels, .two, .cards4, #benchmark .panel").forEach((n) => { n.classList.add("reveal"); io.observe(n); });
})();

init();
