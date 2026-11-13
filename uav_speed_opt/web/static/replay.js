/* Mission replay: drone A flies at the optimal speed V*, drone B at a chosen speed, through the same scene.
   Each drone category has its own scene (city delivery, search area, crop field, site perimeter, survey
   area, power line / pipeline / wind turbine) and its own task counter. The drawn route is always
   exactly the mission distance D, and every number comes from the planner's /api/optimize response:
   P = E/T, the battery drains at P, and R(t) = exp(-λ t). */
(() => {
  const COLORS = ["#38E1FF", "#8B7CFF"];
  const NAMES = ["Drone A", "Drone B"];
  const ROLE = ["optimal speed", "comparison speed"];
  const rp = { d: null, drones: [], t: 0, end: 0, playing: false, last: null, sc: null };
  const el = (id) => document.getElementById(id);
  const f = (x, dp = 1) => (x == null || !isFinite(x) ? "–" : Number(x).toFixed(dp));
  const pct = (x) => `${Math.round(100 * Math.min(Math.max(x, 0), 1))}%`;
  const clock = (s) => { s = Math.max(0, Math.round(s)); return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; };

  /* ---------- route geometry ---------- */
  function geom(pts) {
    const seg = pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
    const cum = [0]; seg.forEach((s) => cum.push(cum[cum.length - 1] + s));
    return { pts, seg, cum, len: cum[cum.length - 1] };
  }
  function pointAt(g, frac) {
    const target = Math.min(Math.max(frac, 0), 1) * g.len;
    let i = 0;
    while (i < g.seg.length - 1 && g.cum[i + 1] < target) i++;
    const u = g.seg[i] ? (target - g.cum[i]) / g.seg[i] : 0;
    const [x0, y0] = g.pts[i], [x1, y1] = g.pts[i + 1];
    return { x: x0 + u * (x1 - x0), y: y0 + u * (y1 - y0), i, ang: Math.atan2(y1 - y0, x1 - x0) * 180 / Math.PI };
  }
  function pathUpTo(g, frac, from = 0) {
    const pos = pointAt(g, frac);
    if (frac * g.len <= g.cum[from] + 1e-6) return "";
    return g.pts.slice(from, pos.i + 1).concat([[pos.x, pos.y]]).map((q) => q.map((v) => v.toFixed(1)).join(",")).join(" ");
  }
  const workFrac = (g, frac, zs) => (g.len - g.cum[zs] > 0 ? (frac * g.len - g.cum[zs]) / (g.len - g.cum[zs]) : 0);

  /* ---------- scene artwork ---------- */
  const T = (x, y, txt, anchor = "middle", cls = "") => `<text x="${x}" y="${y}" text-anchor="${anchor}" class="${cls}">${txt}</text>`;
  function cityDecor() {
    const vs = [40, 130, 220, 310, 400, 490, 580], hs = [40, 110, 180, 262];
    let s = "";
    for (let i = 0; i < 6; i++) for (let j = 0; j < 3; j++) {
      const x = vs[i] + 11, y = hs[j] + 11, w = vs[i + 1] - vs[i] - 22, h = hs[j + 1] - hs[j] - 22, park = (i * 3 + j) % 7 === 4;
      if (park) { s += `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="6" fill="rgba(52,227,161,.07)" stroke="rgba(52,227,161,.2)"/>`
        + `<circle cx="${x + w / 2 - 12}" cy="${y + h / 2}" r="7" fill="rgba(52,227,161,.18)"/><circle cx="${x + w / 2 + 12}" cy="${y + h / 2 - 4}" r="6" fill="rgba(52,227,161,.18)"/>`; continue; }
      s += `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="4" fill="rgba(140,170,230,.05)" stroke="rgba(140,170,230,.13)"/>`;
      const n = 2 + ((i + j) % 2);
      for (let b = 0; b < n; b++) {
        const bw = (w - 8 - (n - 1) * 5) / n, bh = h - 10 - ((i * 7 + j * 5 + b * 3) % 3) * 6;
        s += `<rect x="${x + 4 + b * (bw + 5)}" y="${y + h - 4 - bh}" width="${bw}" height="${bh}" rx="2" fill="rgba(140,170,230,${0.07 + ((i + b) % 3) * 0.03})"/>`;
      }
    }
    return s;
  }
  function terrainDecor(flood) {
    let s = `<g fill="none" stroke="rgba(139,124,255,.14)" stroke-width="1.2">
      <path d="M-10 120 C 80 80, 140 160, 240 120 S 380 40, 650 90"/><path d="M-10 150 C 90 110, 150 190, 250 150 S 390 70, 650 120"/>
      <path d="M-10 285 C 120 240, 200 300, 320 262 S 500 220, 650 270"/><path d="M180 40 C 230 10, 300 30, 330 60 S 300 110, 240 90 S 150 70, 180 40 z"/></g>
      <path d="M-10 70 C 90 40, 130 120, 210 110 S 330 230, 650 250" fill="none" stroke="rgba(91,140,255,.28)" stroke-width="7" stroke-linecap="round"/>`;
    [[90, 200], [120, 180], [140, 215], [520, 230], [560, 210], [545, 250], [300, 250], [330, 270], [260, 60], [600, 170]].forEach(([x, y], i) => {
      s += `<path d="M${x} ${y - 9} L${x + 7} ${y + 5} L${x - 7} ${y + 5} z" fill="rgba(52,227,161,${0.16 + (i % 3) * 0.06})"/>`;
    });
    if (flood) s += `<path d="M370 70 C 430 40, 520 60, 525 110 S 480 175, 420 165 S 340 120, 370 70 z" fill="rgba(91,140,255,.16)" stroke="rgba(91,140,255,.35)"/>`;
    s += `<circle cx="440" cy="118" r="80" fill="rgba(255,181,71,.04)" stroke="rgba(255,181,71,.45)" stroke-dasharray="5 6"/>${T(440, 214, flood ? "FLOOD WATER" : "SEARCH AREA", "middle", "amber")}`;
    return s;
  }
  function fieldDecor() {
    let s = `<rect x="192" y="60" width="414" height="200" rx="10" fill="rgba(52,227,161,.05)" stroke="rgba(52,227,161,.25)"/>`;
    for (let y = 68; y < 256; y += 9) s += `<line x1="200" y1="${y}" x2="598" y2="${y}" stroke="rgba(52,227,161,.11)" stroke-width="3" stroke-linecap="round"/>`;
    s += `<g transform="translate(70 214)"><path d="M-14 0 L0 -12 L14 0 V14 H-14 z" fill="rgba(140,170,230,.1)" stroke="rgba(140,170,230,.35)"/></g>${T(400, 50, "CROP FIELD", "middle", "green")}`;
    return s;
  }
  function siteDecor(coast) {
    let s = coast ? `<path d="M0 0 H640 V22 C 560 34, 480 14, 400 26 S 240 36, 160 22 S 40 30, 0 22 z" fill="rgba(91,140,255,.16)"/>` : "";
    s += `<rect x="110" y="64" width="420" height="176" rx="6" fill="rgba(255,181,71,.025)" stroke="rgba(255,181,71,.5)" stroke-dasharray="7 5"/>`;
    [[150, 95, 90, 50], [270, 90, 110, 70], [410, 100, 80, 46], [160, 175, 70, 40], [300, 185, 150, 36], [470, 170, 40, 50]].forEach(([x, y, w, h]) => {
      s += `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="rgba(140,170,230,.08)" stroke="rgba(140,170,230,.16)"/>`;
    });
    [[110, 64], [530, 64], [110, 240], [530, 240]].forEach(([x, y]) => (s += `<circle cx="${x}" cy="${y}" r="4.5" fill="#FFB547" opacity=".8"/>`));
    s += T(320, 158, coast ? "SITE ON THE COAST" : "SECURED SITE", "middle", "amber");
    return s;
  }
  function surveyDecor() {
    let s = `<g fill="none" stroke="rgba(139,124,255,.12)"><path d="M-10 200 C 60 170, 120 230, 200 200 S 300 150, 650 190"/><path d="M-10 90 C 70 60, 140 120, 230 90"/></g>`;
    s += `<rect x="252" y="48" width="336" height="204" rx="8" fill="rgba(139,124,255,.05)" stroke="rgba(139,124,255,.45)" stroke-dasharray="6 5"/>`;
    [[262, 58], [578, 58], [262, 242], [578, 242], [420, 150]].forEach(([x, y]) => (s += `<path d="M${x - 5} ${y - 5} L${x + 5} ${y + 5} M${x + 5} ${y - 5} L${x - 5} ${y + 5}" stroke="#FFB547" stroke-width="1.6"/>`));
    s += T(420, 40, "SURVEY AREA", "middle", "violet");
    return s;
  }
  function pylon(x, y) {
    return `<g transform="translate(${x} ${y})" class="tower" stroke="rgba(140,170,230,.55)" stroke-width="1.4" fill="none">
      <path d="M-7 16 L0 -16 L7 16 M-9 -8 H9 M-6 2 H6 M-4 -8 L4 2 M4 -8 L-4 2"/></g>`;
  }
  function lineDecor(g) {
    const P = g.pts.slice(1).map(([x, y]) => [x, y + 22]);
    let s = "";
    for (let i = 0; i < P.length - 1; i++) {
      const [x0, y0] = P[i], [x1, y1] = P[i + 1];
      s += `<path d="M${x0} ${y0 - 14} Q ${(x0 + x1) / 2} ${(y0 + y1) / 2 - 2} ${x1} ${y1 - 14}" fill="none" stroke="rgba(255,181,71,.35)" stroke-width="1.2"/>`;
    }
    return s + P.map(([x, y], i) => pylon(x, y).replace('class="tower"', `class="tower" data-t="${i}"`)).join("");
  }
  function pipeDecor(g) {
    const P = g.pts.map(([x, y]) => `${x},${y + 18}`).join(" ");
    return `<polyline points="${P}" fill="none" stroke="rgba(255,181,71,.28)" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"/>`
      + g.pts.slice(1, -1).map(([x, y]) => `<rect x="${x - 5}" y="${y + 13}" width="10" height="10" rx="2" fill="#0B1222" stroke="rgba(255,181,71,.6)"/>`).join("");
  }
  function turbineDecor() {
    return `<line x1="555" y1="105" x2="555" y2="290" stroke="rgba(140,170,230,.45)" stroke-width="4"/>
      <g transform="translate(555 105)"><g class="blades" fill="rgba(234,240,250,.9)"><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="3s" repeatCount="indefinite"/>
        <path d="M0 0 C -7 -10, -6 -30, 0 -38 C 4 -30, 5 -10, 0 0 z"/><path d="M0 0 C -7 -10, -6 -30, 0 -38 C 4 -30, 5 -10, 0 0 z" transform="rotate(120)"/><path d="M0 0 C -7 -10, -6 -30, 0 -38 C 4 -30, 5 -10, 0 0 z" transform="rotate(240)"/></g>
        <circle r="4" fill="#EAF0FA"/></g>
      <g fill="none" stroke="rgba(139,124,255,.12)"><path d="M-10 230 C 100 200, 200 260, 320 225 S 500 190, 650 230"/></g>`;
  }

  /* ---------- scenes by category ---------- */
  function sceneFor(cat, ex) {
    const dest = ex ? ex.dest : null, p = state.p;
    if (cat === "Delivery") return {
      title: "City delivery", start: "Hub", end: dest || "Customer", zs: 0, foot: false,
      pts: [[40, 262], [40, 180], [220, 180], [220, 110], [400, 110], [400, 40], [580, 40]], decor: cityDecor,
      task: ["Parcel", (s) => p.payload > 0
        ? (s.arrived ? [`Delivered ✓ · ${f(p.payload)} kg`, "ok"] : s.empty ? ["Not delivered", "bad"] : [`${s.t > 0 ? "On board" : "Loaded"} · ${f(p.payload)} kg`, ""])
        : (s.arrived ? ["Arrived ✓ (no payload set)", "ok"] : ["No payload set", ""])],
    };
    if (cat === "SAR") {
      const flood = !!(dest && /flood/i.test(dest));
      return {
        title: flood ? "Flood rescue" : "Search area", start: "Rescue base", end: dest || "Last known location", zs: 3, foot: true,
        pts: [[60, 250], [180, 215], [300, 170], [430, 118], [450, 118], [450, 138], [410, 138], [410, 98], [470, 98], [470, 158], [390, 158], [390, 78], [490, 78]],
        decor: () => terrainDecor(flood),
        task: ["Search", (s) => s.arrived ? [flood ? "Life jacket dropped ✓" : "Target found ✓", "ok"] : s.empty ? ["Search not finished", "bad"]
          : s.wf <= 0 ? [s.t > 0 ? "Flying to the search area" : "Ready", ""] : [`Searching · ${pct(s.wf)} of pattern`, ""]],
      };
    }
    if (cat === "Agricultural") return {
      title: "Crop field", start: "Farm", end: dest || "Field", zs: 1, foot: false, spray: true,
      pts: [[50, 262], [210, 240], [590, 240], [590, 200], [210, 200], [210, 160], [590, 160], [590, 120], [210, 120], [210, 80], [590, 80]], decor: fieldDecor,
      task: [p.payload > 0 ? "Field sprayed" : "Field scouted", (s) => [`${pct(s.wf)}${s.arrived ? " ✓" : ""}${p.payload > 0 ? ` · ${f(p.payload)} kg tank` : ""}`, s.arrived ? "ok" : s.empty ? "bad" : ""]],
    };
    if (cat === "Surveillance") {
      const coast = !!(dest && /coast/i.test(dest));
      return {
        title: coast ? "Coastal site patrol" : "Perimeter patrol", start: "Dock", end: dest || "Patrol end", zs: 0, foot: true,
        pts: [[86, 262], [86, 40], [554, 40], [554, 262], [330, 262]], decor: () => siteDecor(coast),
        task: ["Perimeter covered", (s) => [`${pct(s.wf)}${s.arrived ? " ✓" : ""}`, s.arrived ? "ok" : s.empty ? "bad" : ""]],
      };
    }
    if (cat === "Mapping") {
      const pts = [[50, 250], [270, 240]];
      [270, 320, 370, 420, 470, 520, 570].forEach((x, i) => { if (i) pts.push([x, i % 2 ? 60 : 240]); pts.push([x, i % 2 ? 240 : 60]); });
      return {
        title: "Aerial survey", start: "Launch point", end: dest || "Survey area", zs: 1, foot: true, photos: true, pts, decor: surveyDecor,
        task: ["Photos taken", (s) => [`${Math.floor((s.workKm * 1000) / 40)} · ${pct(s.wf)} of area`, s.arrived ? "ok" : s.empty ? "bad" : ""]],
      };
    }
    // Inspection: power line (default), pipeline or wind turbine
    if (dest && /turbine/i.test(dest)) return {
      title: "Wind-turbine inspection", start: "Base", end: "Wind turbine", zs: 4, foot: true,
      pts: [[50, 250], [170, 215], [300, 175], [420, 140], [555, 62], [598, 105], [555, 148], [512, 105], [555, 62]], decor: turbineDecor,
      task: ["Turbine", (s) => s.arrived ? ["Blade inspection done ✓", "ok"] : s.empty ? ["Inspection not finished", "bad"]
        : s.wf <= 0 ? [s.t > 0 ? "Flying to the turbine" : "Ready", ""] : [`Inspecting blades · ${pct(s.wf)}`, ""]],
    };
    const pipe = !!(dest && /pipe/i.test(dest));
    const pts = [[50, 250], [150, 205], [255, 218], [360, 150], [465, 128], [580, 70]];
    return {
      title: pipe ? "Pipeline patrol" : "Power-line inspection", start: "Base", end: dest || "End of line", zs: 0, foot: true, line: !pipe,
      pts, decor: (g) => (pipe ? pipeDecor(g) : lineDecor(g)),
      task: pipe ? ["Pipeline checked", (s) => [`${f(s.distKm, 2)} km${s.arrived ? " ✓" : ""}`, s.arrived ? "ok" : s.empty ? "bad" : ""]]
        : ["Towers inspected", (s) => [`${s.towers} / ${pts.length - 1}${s.arrived ? " ✓" : ""}`, s.arrived ? "ok" : s.empty ? "bad" : ""]],
    };
  }

  /* ---------- panel markup ---------- */
  const STATS = [["status", "Status", true], ["task", "Task", true], ["clock", "Mission clock"], ["dist", "Distance flown"], ["air", "Airspeed"], ["ground", "Ground speed"],
    ["power", "Power draw"], ["energy", "Energy used"], ["batt", "Usable battery left", true], ["rel", "No-failure probability"], ["deliv", "Finished at"]];
  function droneSVG(k) {
    const c = COLORS[k];
    return `<g class="drone"><circle r="18" fill="${c}" opacity="0.14"/><path d="M-8 -8 L8 8 M8 -8 L-8 8" stroke="${c}" stroke-width="2.4"/>
      <g fill="#0B1120" stroke="${c}" stroke-width="1.6"><circle cx="-8" cy="-8" r="4.5"/><circle cx="8" cy="-8" r="4.5"/><circle cx="-8" cy="8" r="4.5"/><circle cx="8" cy="8" r="4.5"/></g>
      <rect x="-4" y="-4" width="8" height="8" rx="2" fill="${c}"/></g>`;
  }
  function panelHTML(k, sc) {
    const g = sc.g, c = COLORS[k], p = state.p;
    const [b, e] = [g.pts[0], g.pts[g.pts.length - 1]];
    const ex = Math.min(Math.max(e[0], 60), 580), ey = e[1] < 60 ? e[1] + 30 : e[1] - 18;
    const photos = sc.photos ? Array.from({ length: 42 }, (_, i) => {
      const fr = g.cum[sc.zs] / g.len + ((i + 0.5) / 42) * (1 - g.cum[sc.zs] / g.len), q = pointAt(g, fr);
      return `<rect class="photo" data-f="${fr.toFixed(4)}" x="${(q.x - 5).toFixed(1)}" y="${(q.y - 5).toFixed(1)}" width="10" height="10" rx="1.5" fill="none" stroke="${c}" stroke-opacity=".6" visibility="hidden"/>`;
    }).join("") : "";
    return `<h3><i></i><span>${NAMES[k]}: ${ROLE[k]}</span></h3>
      <p class="rp-sub">${f(rp.drones[k].V)} m/s (${f(rp.drones[k].V * 3.6, 0)} km/h) · ${(typeof SHORT !== "undefined" && SHORT[state.cat]) || state.cat}${p.payload ? ` · ${f(p.payload)} kg payload` : ""}</p>
      <div class="rp-scene"><span class="sc-title">${sc.title}</span><span>Route ${f(p.distance)} km</span>
        <span class="${p.headwind > 0 ? "sc-wind" : ""}">${p.headwind > 0 ? `← Headwind ${f(p.headwind)} m/s` : "Calm air"}</span></div>
      <svg class="rp-map" viewBox="0 0 640 300" role="img" aria-label="${NAMES[k]} flying the ${sc.title.toLowerCase()} scene">
        ${sc.decor(g)}
        <polyline points="${g.pts.map((q) => q.join(",")).join(" ")}" fill="none" stroke="rgba(234,240,250,.28)" stroke-width="1.6" stroke-dasharray="5 6"/>
        ${sc.spray ? `<polyline class="spray" points="" fill="none" stroke="rgba(52,227,161,.28)" stroke-width="26" stroke-linecap="round" stroke-linejoin="round"/>` : ""}
        ${photos}
        <polyline class="trail" points="" fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        <rect x="${b[0] - 9}" y="${b[1] - 9}" width="18" height="18" rx="4" fill="#0B1222" stroke="#93A1BA" stroke-width="1.5"/>
        ${T(Math.max(b[0], 40), b[1] + 26 > 296 ? b[1] - 16 : b[1] + 26, sc.start.toUpperCase(), "middle", "lbl-strong")}
        <circle cx="${e[0]}" cy="${e[1]}" r="11" fill="none" stroke="#34E3A1" stroke-width="2"/><circle cx="${e[0]}" cy="${e[1]}" r="3.5" fill="#34E3A1"/>
        ${T(ex, ey, sc.end.toUpperCase(), "middle", "lbl-strong dest")}
        <g class="dropped" visibility="hidden" transform="translate(${e[0]} ${e[1] + 2})"><rect x="-7" y="-7" width="14" height="14" rx="2" fill="#FFB547"/><path d="M-7 -1 H7 M0 -7 V7" stroke="#7A4B00" stroke-width="1.4"/></g>
        <g class="found" visibility="hidden" transform="translate(${e[0]} ${e[1]})"><circle r="16" fill="none" stroke="#34E3A1" stroke-width="2"/><circle cy="-5" r="3" fill="#EAF0FA"/><path d="M0 -2 V6 M-5 1 H5 M0 6 L-4 12 M0 6 L4 12" stroke="#EAF0FA" stroke-width="1.8"/></g>
        ${sc.foot ? `<circle class="foot" r="24" fill="${c}" fill-opacity=".07" stroke="${c}" stroke-opacity=".45" stroke-dasharray="3 4"/>` : ""}
        <g class="empty" visibility="hidden"><path d="M-7 -7 L7 7 M7 -7 L-7 7" stroke="#FF6B7A" stroke-width="3" stroke-linecap="round"/>
          ${T(0, 24, "BATTERY RESERVE", "middle", "coral")}</g>
        <g class="carry" visibility="hidden"><path d="M0 0 V10" stroke="#93A1BA" stroke-width="1"/><rect x="-6" y="10" width="12" height="11" rx="2" fill="#FFB547"/></g>
        ${droneSVG(k)}
      </svg>
      <div class="rp-stats">${STATS.map(([key, label, wide]) => key === "batt"
        ? `<div class="rp-stat wide rp-battrow" data-s="batt"><div class="rp-battline"><span>${label}</span><b>–</b></div><div class="rp-batt"><i></i></div></div>`
        : `<div class="rp-stat${wide ? " wide" : ""}${key === "task" ? " rp-taskrow" : ""}" data-s="${key}"><span>${key === "task" ? sc.task[0] : label}</span><b>–</b></div>`).join("")}</div>`;
  }

  /* ---------- drones from the planner response ---------- */
  function fromCurve(d, V) {
    const c = d.curves; let best = 0;
    c.V.forEach((v, i) => { if (Math.abs(v - V) < Math.abs(c.V[best] - V)) best = i; });
    return { V: c.V[best], E: c.E[best], T: c.T[best], R: c.R[best] };
  }
  function makeDrone(pt) {
    const p = state.p, battery = rp.d.battery_kJ, vg = pt.V - p.headwind;
    const dr = { V: pt.V, vg, stuck: vg <= 0.05 || pt.T == null || pt.E == null };
    if (dr.stuck) return Object.assign(dr, { end: 0 });
    const Ts = pt.T * 60;
    dr.P = (pt.E * 1000) / Ts;
    dr.lam = -Math.log(Math.max(pt.R, 1e-12)) / Ts;
    dr.tEmpty = (battery * 1000) / dr.P;
    dr.arrive = Ts <= dr.tEmpty + 1e-6 ? Ts : null;
    dr.end = Math.min(Ts, dr.tEmpty);
    dr.Etot = (dr.P * dr.end) / 1000; dr.Rend = Math.exp(-dr.lam * dr.end);
    return dr;
  }
  function rebuild() {
    const d = rp.d, ok = d && d.ok;
    el("rpNone").hidden = !!ok; el("rpPanels").hidden = !ok;
    document.querySelectorAll(".rp-controls button, .rp-controls select, .rp-controls input").forEach((x) => (x.disabled = !ok));
    if (!ok) { pause(); el("rpHeadline").textContent = ""; return; }
    const vb = +el("rpVb").value;
    rp.drones = [makeDrone({ V: d.v_star, E: d.E, T: d.T, R: d.R }), makeDrone(fromCurve(d, vb))];
    rp.drones[1].V = vb;
    const ends = rp.drones.filter((x) => !x.stuck).map((x) => x.end);
    rp.end = Math.max(...ends) * (rp.drones.some((x) => x.stuck) ? 1.15 : 1);
    rp.t = 0; pause();
    rp.sc = sceneFor(state.cat, state.example);
    rp.sc.g = geom(rp.sc.pts);
    document.querySelectorAll(".rp-panel").forEach((panel, k) => (panel.innerHTML = panelHTML(k, rp.sc)));
    headline();
    draw();
  }

  function headline() {
    const [a, b] = rp.drones, p = state.p, h = el("rpHeadline");
    if (Math.abs(a.V - b.V) < 0.05) { h.innerHTML = "Both drones are flying at the same speed. Move the drone B slider to compare."; return; }
    if (b.stuck) { h.innerHTML = `At ${f(b.V)} m/s drone B <b class="bad">cannot make headway</b> against the ${f(p.headwind)} m/s headwind. Drone A finishes in <b>${f(a.arrive / 60)} min</b>.`; return; }
    if (b.arrive == null) {
      h.innerHTML = `Drone B <b class="bad">runs out of usable battery after ${f((b.vg * b.end) / 1000)} km</b> of the ${f(p.distance)} km route. Drone A finishes in <b>${f(a.arrive / 60)} min</b> using <b>${f((100 * a.Etot) / rp.d.battery_kJ, 0)}%</b> of its battery.`;
      return;
    }
    const dt = (b.arrive - a.arrive) / 60, dE = 1 - a.Etot / b.Etot;
    let s = `At the optimal ${f(a.V)} m/s, drone A finishes <b class="${dt >= 0 ? "" : "bad"}">${f(Math.abs(dt))} min ${dt >= 0 ? "sooner" : "later"}</b>`
      + ` and uses <b class="${dE >= 0 ? "" : "bad"}">${pct(Math.abs(dE))} ${dE >= 0 ? "less" : "more"} energy</b> than drone B at ${f(b.V)} m/s.`;
    if (b.Rend < p.rmin) s += ` Drone B's reliability (${f(b.Rend, 4)}) <b class="bad">falls below the ${f(p.rmin, 4)} target</b>.`;
    h.innerHTML = s;
  }

  /* ---------- per-frame drawing ---------- */
  function draw() {
    const p = state.p, sc = rp.sc, g = sc && sc.g;
    if (!g) return;
    document.querySelectorAll(".rp-panel").forEach((panel, k) => {
      const dr = rp.drones[k]; if (!dr) return;
      const tt = dr.stuck ? 0 : Math.min(rp.t, dr.end);
      const done = !dr.stuck && rp.t >= dr.end - 1e-6, arrived = done && dr.arrive != null, empty = done && dr.arrive == null;
      const distKm = dr.stuck ? 0 : arrived ? p.distance : (dr.vg * tt) / 1000, frac = Math.min(distKm / p.distance, 1);
      const pos = pointAt(g, frac);
      const q = (s) => panel.querySelector(s);
      const at = (s, attr, v) => { const n = q(s); if (n) n.setAttribute(attr, v); };
      at(".drone", "transform", `translate(${pos.x.toFixed(1)} ${pos.y.toFixed(1)}) rotate(${(pos.ang + 45).toFixed(1)})`);
      at(".foot", "cx", pos.x.toFixed(1)); at(".foot", "cy", pos.y.toFixed(1));
      at(".trail", "points", pathUpTo(g, frac));
      if (sc.spray) at(".spray", "points", p.payload > 0 ? pathUpTo(g, frac, sc.zs) : "");
      if (sc.photos) panel.querySelectorAll(".photo").forEach((n) => n.setAttribute("visibility", +n.dataset.f <= frac ? "visible" : "hidden"));
      let towers = 0;
      if (sc.line) panel.querySelectorAll(".tower").forEach((n) => {
        const i = +n.dataset.t, hit = frac * g.len >= g.cum[i + 1] - 1e-6;
        if (hit) towers++;
        n.setAttribute("stroke", hit ? "#34E3A1" : "rgba(140,170,230,.55)");
      });
      const carry = state.cat === "Delivery" && p.payload > 0 && !arrived && !empty;
      at(".carry", "visibility", carry ? "visible" : "hidden"); at(".carry", "transform", `translate(${pos.x.toFixed(1)} ${(pos.y + 4).toFixed(1)})`);
      at(".dropped", "visibility", arrived && state.cat === "Delivery" && p.payload > 0 ? "visible" : "hidden");
      at(".found", "visibility", arrived && state.cat === "SAR" ? "visible" : "hidden");
      at(".empty", "visibility", empty ? "visible" : "hidden"); at(".empty", "transform", `translate(${pos.x} ${pos.y + 26})`);

      const set = (key, html, cls) => { const b = q(`[data-s="${key}"] b`); if (!b) return; b.innerHTML = html; b.className = cls || ""; };
      let status, scls;
      if (dr.stuck) { status = "Cannot make headway against the headwind"; scls = "rp-status bad"; }
      else if (rp.t <= 0) { status = "Ready at base"; scls = "rp-status"; }
      else if (!done) { status = "Flying"; scls = "rp-status fly"; }
      else if (arrived) { status = "Mission complete ✓"; scls = "rp-status ok"; }
      else { status = "Stopped: usable battery used up"; scls = "rp-status bad"; }
      set("status", status, scls);
      const wf = workFrac(g, frac, sc.zs);
      const [tv, tc] = sc.task[1]({ t: rp.t, arrived, empty, wf, workKm: Math.max(0, wf) * p.distance * (1 - g.cum[sc.zs] / g.len), distKm, towers });
      set("task", tv, `rp-status ${tc}`);
      set("clock", clock(tt));
      set("dist", `${f(distKm, 2)} / ${f(p.distance)} km`);
      set("air", `${f(dr.V)} m/s`);
      set("ground", `${f(dr.vg)} m/s`, dr.vg <= 0 ? "bad-val" : "");
      set("power", dr.stuck ? "–" : `${f(dr.P, 0)} W`);
      const E = dr.stuck ? 0 : (dr.P * tt) / 1000;
      set("energy", dr.stuck ? "–" : `${f(E, E < 100 ? 1 : 0)} kJ`);
      const left = dr.stuck ? 1 : Math.max(0, 1 - E / rp.d.battery_kJ);
      set("batt", `${f(100 * left, 0)}% of ${f(rp.d.battery_kJ, 0)} kJ`, left < 0.15 ? "bad-val" : "");
      const bar = q(".rp-batt i");
      if (bar) { bar.style.width = `${100 * left}%`; bar.style.background = left > 0.5 ? "#34E3A1" : left > 0.2 ? "#FFB547" : "#FF6B7A"; bar.style.color = bar.style.background; }
      const R = dr.stuck ? 1 : Math.exp(-dr.lam * tt);
      set("rel", f(R, 4), R < p.rmin ? "bad-val" : "");
      set("deliv", dr.arrive != null && rp.t > 0 ? (rp.t >= dr.arrive ? `${f(dr.arrive / 60)} min` : "on the way") : "–");
    });
    el("rpTime").value = rp.end ? Math.round((1000 * rp.t) / rp.end) : 0;
    if (window.fillRange) window.fillRange(el("rpTime"));
    el("rpClock").textContent = `${clock(rp.t)} / ${clock(rp.end)}`;
  }

  /* ---------- playback ---------- */
  function frame(ts) {
    if (!rp.playing) return;
    if (rp.last != null) rp.t += ((ts - rp.last) / 1000) * +el("rpSpeed").value;
    rp.last = ts;
    if (rp.t >= rp.end) { rp.t = rp.end; draw(); pause(); return; }
    draw();
    requestAnimationFrame(frame);
  }
  function play() {
    if (!rp.d || !rp.d.ok) return;
    if (rp.t >= rp.end) rp.t = 0;
    rp.playing = true; rp.last = null; el("rpPlay").textContent = "Pause";
    requestAnimationFrame(frame);
  }
  function pause() { rp.playing = false; el("rpPlay").textContent = "Play"; }
  el("rpPlay").onclick = () => (rp.playing ? pause() : play());
  el("rpRestart").onclick = () => { rp.t = 0; draw(); };
  el("rpTime").addEventListener("input", (e) => { pause(); rp.t = (+e.target.value / 1000) * rp.end; draw(); });
  el("rpVb").addEventListener("input", () => {
    el("rpVbOut").textContent = `${f(+el("rpVb").value)} m/s`;
    if (window.fillRange) window.fillRange(el("rpVb"));
    if (rp.d) rebuild();
  });

  /* called by app.js every time the planner gets a new result */
  window.updateReplay = (d) => {
    rp.d = d;
    const vb = el("rpVb"), vmax = Math.floor(state.p.vmax * 2) / 2;
    vb.max = vmax;
    if (+vb.value > vmax) vb.value = vmax;
    el("rpVbOut").textContent = `${f(+vb.value)} m/s`;
    if (window.fillRange) window.fillRange(vb);
    rebuild();
  };
})();
