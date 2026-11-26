/* EpiCare — application mobile (PWA), sans dépendance.
 *
 * Données : data/app_data.json (schéma "epicare.app/1", écrit par `python -m epicare_b1 export-app`).
 * Fusion des branches : chaque branche remplit son bloc dans `branches`. Un fichier
 * data/branch2.json (même schéma, ou directement le bloc branch2) est fusionné s'il existe,
 * ainsi que tout fichier importé depuis les Réglages.
 */
"use strict";

/* ============================================================ icônes (trait 24×24) */
const ICONS = {
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  settings: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  gauge: '<path d="M3.5 18a9.5 9.5 0 1 1 17 0"/><path d="m12 14 4-5"/><circle cx="12" cy="14" r="1.2"/>',
  trend: '<path d="M3 17l5-6 4 3 4-6 5 5"/><path d="M3 21h18"/>',
  orbit: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
  shield: '<path d="M12 21s7-3.5 7-9.5V5.5L12 3 5 5.5v6C5 17.5 12 21 12 21z"/><path d="m9 12 2 2 4-4"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.8 2.8L16 10"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5M12 16.5h.01"/>',
  warning: '<path d="M10.3 4.2 2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/><path d="M12 9.5v4M12 17h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  hourglass: '<path d="M6 3h12M6 21h12M7 3c0 5 10 5 10 9s-10 4-10 9M17 3c0 5-10 5-10 9"/>',
  baseline: '<path d="M3 12h18"/><path d="M3 6h4M3 18h4"/>',
  medal: '<circle cx="12" cy="9" r="6"/><path d="m8.5 14-1.5 7 5-3 5 3-1.5-7"/>',
  wave: '<path d="M2 12h3l2-6 4 12 3-9 2 3h6"/>',
  heart: '<path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7z"/>',
  drop: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
  move: '<path d="M5 12h14M12 5v14"/><path d="m8 8-3 4 3 4M16 8l3 4-3 4"/>',
  thermo: '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/>',
  bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  repeat: '<path d="M4 12a8 8 0 0 1 14-5.3L20 9"/><path d="M20 4v5h-5"/><path d="M20 12a8 8 0 0 1-14 5.3L4 15"/><path d="M4 20v-5h5"/>',
  watch: '<rect x="6.5" y="6" width="11" height="12" rx="3"/><path d="M9 6l.7-3h4.6L15 6M9 18l.7 3h4.6l.7-3"/>',
  bell: '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  reset: '<path d="M4 12a8 8 0 1 0 2.3-5.6L4 8.7"/><path d="M4 4v4.7h4.7"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
  auto: '<circle cx="12" cy="12" r="9"/><path d="M12 3v18" /><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor"/>',
  database: '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.8"/><path d="M4.5 5.5v13c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8v-13"/><path d="M4.5 12c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8"/>',
  brain: '<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a2 2 0 0 0-3-1z"/><path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1"/>',
  sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
};
const ico = (name, cls = "") => `<span class="ico ${cls}">${svgIco(name)}</span>`;
const svgIco = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;
function hydrateIcons(root = document) {
  root.querySelectorAll("[data-ico]").forEach((el) => { el.innerHTML = svgIco(el.dataset.ico); });
}

/* ============================================================ formatage (fr-FR) */
const nf = (d) => new Intl.NumberFormat("fr-FR", { maximumFractionDigits: d, minimumFractionDigits: d });
function pct(p, digits) {
  if (p == null || isNaN(p)) return "—";
  const v = p * 100;
  const d = digits ?? (v >= 10 ? 0 : v >= 1 ? 1 : 2);
  return `${nf(d).format(v)} %`;
}
const num = (x, d = 2) => (x == null || isNaN(x) ? "—" : nf(d).format(x));
const signed = (x, d = 2) => (x == null ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + nf(d).format(Math.abs(x)));
const MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
const DAYS = ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."];
/** "2020-03-19T07:00" -> Date (heure locale du patient, sans conversion de fuseau) */
function parseLocal(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(s || "");
  return m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) : null;
}
const fmtDate = (d) => `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
const fmtDay = (d) => `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
const fmtTime = (d) => `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
const addHours = (d, h) => new Date(d.getTime() + h * 3600e3);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ============================================================ textes métier */
const LEVELS = {
  low: { label: "Faible", cls: "good", color: "var(--good)", icon: "checkCircle" },
  medium: { label: "Modéré", cls: "warn", color: "var(--warn)", icon: "alert" },
  high: { label: "Élevé", cls: "crit", color: "var(--crit)", icon: "warning" },
};
const CONF = { low: "Faible", medium: "Moyenne", high: "Élevée" };
const MODELS = {
  base: { name: "Référence", sub: "taux moyen du patient" },
  cycle: { name: "Cycles", sub: "rythmes des crises seuls" },
  wear: { name: "Capteurs", sub: "signaux de la montre seuls" },
  prior_shift: { name: "Cycles + capteurs", sub: "méthode SeFEF (décalage a priori)" },
  epicare: { name: "EpiCare", sub: "fusion apprise et calibrée" },
};
const MODEL_ORDER = ["epicare", "prior_shift", "wear", "cycle", "base"];
const MODALITY = {
  acc: ["Mouvement", "move", false], bvp: ["Pouls (BVP)", "heart", false], hr: ["Fréquence cardiaque", "heart", true],
  eda: ["Activité électrodermale", "drop", true], temp: ["Température cutanée", "thermo", true],
};

/** Traduit un facteur produit par la branche 1 en (titre, sous-titre, icône). */
function driverInfo(s) {
  let m = /^([\d.]+) (h|d) cycle phase \(x([\d.]+)\)/.exec(s);
  if (m) {
    const daily = m[2] === "h";
    const period = daily ? `${m[1]} h` : `${num(+m[1], 1)} jours`;
    return { title: daily && +m[1] === 24 ? "Moment de la journée" : `Cycle de ${period}`,
      sub: `Phase à risque du cycle personnel · risque ×${num(+m[3], 1)}`, icon: "repeat" };
  }
  if (/seizure in the last 24 h/.test(s)) return { title: "Crise récente", sub: "Une crise dans les dernières 24 h", icon: "clock" };
  m = /^(\w+?)[ _](.+) unusual \(last (\d+) h\)/.exec(s);
  if (m) {
    const [label, icon, fem] = MODALITY[m[1]] || [m[1].toUpperCase(), "wave", false];
    return { title: `${label} inhabituel${fem ? "le" : ""}`,
      sub: `${featureFr(m[2])} · ${m[3]} dernières heures`, icon };
  }
  return { title: s, sub: "", icon: "info" };
}
const STAT_FR = {
  mean: "niveau moyen", power: "puissance du signal", std: "variabilité", kurtosis: "pics brusques",
  skewness: "asymétrie du signal", d1: "variations rapides", d2: "changements brusques",
  "hjorth activity": "activité (Hjorth)", "hjorth mobility": "mobilité (Hjorth)", "hjorth complexity": "complexité (Hjorth)",
  "n peaks": "nombre de réponses", "peak amp mean": "amplitude des réponses", "peak amp sum": "réponses cumulées",
  "rise time mean": "temps de montée des réponses", "rise time sum": "temps de montée cumulé",
};
function featureFr(stat) {
  const k = stat.replace(/_/g, " ").trim();
  return `Écart à l'habitude (${STAT_FR[k] || k})`;
}
function messageFr(p24) {
  if (p24 == null) return "";
  if (p24 >= 0.25) return `Environ ${Math.max(1, Math.round(p24 * 10))} jours sur 10 comme aujourd'hui comportent une crise`;
  return `Environ 1 jour sur ${Math.round(1 / Math.max(p24, 1e-9))} comme aujourd'hui comporte une crise`;
}

/* ============================================================ état */
const state = {
  doc: null, source: "", patientIdx: 0, view: "home",
  trendH: "24", perfH: "1h", perfScope: "all",
};
const LS_DOC = "epicare.importedDoc", LS_THEME = "epicare.theme", LS_PATIENT = "epicare.patient";
/** localStorage protégé : dans certaines WebView il est absent ou refuse l'accès. */
const store = (() => {
  const mem = {};
  let ls = null;
  try { ls = window.localStorage; ls.setItem("epicare.t", "1"); ls.removeItem("epicare.t"); } catch { ls = null; }
  return {
    getItem: (k) => (ls ? ls.getItem(k) : (k in mem ? mem[k] : null)),
    setItem: (k, v) => { if (ls) ls.setItem(k, v); else mem[k] = String(v); },
    removeItem: (k) => { if (ls) ls.removeItem(k); else delete mem[k]; },
  };
})();

function mergeDocs(base, extra) {
  if (!extra) return base;
  if (!base) return extra;
  const out = { ...base, branches: { ...(base.branches || {}) } };
  const eb = extra.branches || (extra.patients ? { branch2: extra } : {});
  for (const [k, v] of Object.entries(eb)) if (v) out.branches[k] = v;
  return out;
}
async function fetchJson(url) {
  try { const r = await fetch(url, { cache: "no-cache" }); return r.ok ? await r.json() : null; } catch { return null; }
}
async function loadData() {
  let doc = null;
  const imported = store.getItem(LS_DOC);
  if (imported) { try { doc = JSON.parse(imported); state.source = "Fichier importé"; } catch { store.removeItem(LS_DOC); } }
  if (!doc && window.EPICARE_DATA) { doc = window.EPICARE_DATA; state.source = "Données intégrées à l'application"; }
  if (!doc) { doc = await fetchJson("data/app_data.json"); state.source = "Fichier intégré"; }
  doc = mergeDocs(doc, window.EPICARE_BRANCH2 || await fetchJson("data/branch2.json"));
  return doc;
}
const b1 = () => state.doc?.branches?.branch1 || null;
const b2 = () => state.doc?.branches?.branch2 || null;
const patients = () => b1()?.patients || [];
const patient = () => patients()[state.patientIdx] || null;
const b2patient = () => (b2()?.patients || []).find((p) => String(p.id) === String(patient()?.id)) || null;

/* ============================================================ outils SVG */
const NS = "http://www.w3.org/2000/svg";
function arcPath(cx, cy, r, a0, a1) {
  const p = (a) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const [x0, y0] = p(a0), [x1, y1] = p(a1);
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M${x0.toFixed(2)} ${y0.toFixed(2)} A${r} ${r} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
}
function niceMax(v) {
  if (!(v > 0)) return 1;
  const e = Math.pow(10, Math.floor(Math.log10(v))), f = v / e;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * e;
}
function ticks(max, n = 4) { const s = max / n; return Array.from({ length: n + 1 }, (_, i) => i * s); }
const W = (el) => Math.max(260, Math.round(el.clientWidth || 320));

/* tooltip partagé (toucher + souris) */
const tip = document.getElementById("tooltip");
function showTip(x, y, html) {
  tip.innerHTML = html; tip.hidden = false;
  const w = tip.offsetWidth, vw = window.innerWidth;
  tip.style.left = `${Math.min(Math.max(x, w / 2 + 8), vw - w / 2 - 8)}px`;
  tip.style.top = `${Math.max(y, tip.offsetHeight + 20)}px`;
}
function hideTip() { tip.hidden = true; }

/** Ajoute une couche d'interaction : f(index) -> {x, html}. */
function attachHover(wrap, svg, n, xOf, render, onMove) {
  const hit = document.createElementNS(NS, "rect");
  const vb = svg.viewBox.baseVal;
  hit.setAttribute("x", 0); hit.setAttribute("y", 0);
  hit.setAttribute("width", vb.width); hit.setAttribute("height", vb.height);
  hit.setAttribute("fill", "transparent");
  svg.appendChild(hit);
  const pick = (ev) => {
    const r = svg.getBoundingClientRect();
    const sx = ((ev.clientX - r.left) / r.width) * vb.width;
    let best = 0, bd = Infinity;
    for (let i = 0; i < n; i++) { const d = Math.abs(xOf(i) - sx); if (d < bd) { bd = d; best = i; } }
    return { i: best, r };
  };
  const move = (ev) => {
    const { i, r } = pick(ev);
    onMove && onMove(i);
    showTip(r.left + (xOf(i) / vb.width) * r.width, r.top + 8, render(i));
  };
  const end = () => { hideTip(); onMove && onMove(null); };
  wrap.addEventListener("pointerdown", move);
  wrap.addEventListener("pointermove", (e) => { if (e.pointerType === "mouse" || e.buttons) move(e); });
  wrap.addEventListener("pointerleave", end);
  wrap.addEventListener("pointerup", (e) => { if (e.pointerType !== "mouse") setTimeout(end, 1400); });
  wrap.addEventListener("pointercancel", end);
}

/* ============================================================ graphiques */

/** Jauge du risque 24 h (carte principale). */
function gaugeSVG(p, levels, levelKey) {
  const cx = 115, cy = 112, r = 92, a0 = Math.PI * 0.75, a1 = Math.PI * 2.25;
  // échelle non linéaire douce : la plupart des probabilités sont faibles
  const scale = (v) => Math.sqrt(Math.min(Math.max(v, 0), 1));
  const at = (v) => a0 + (a1 - a0) * scale(v);
  const lv = LEVELS[levelKey] || LEVELS.low;
  const marks = [];
  for (const [k, v] of Object.entries(levels || {})) {
    if (v == null) continue;
    const a = at(v), x0 = cx + (r - 13) * Math.cos(a), y0 = cy + (r - 13) * Math.sin(a), x1 = cx + (r + 13) * Math.cos(a), y1 = cy + (r + 13) * Math.sin(a);
    marks.push(`<line x1="${x0}" y1="${y0}" x2="${x1}" y2="${y1}" stroke="rgba(255,255,255,.55)" stroke-width="2" stroke-linecap="round"><title>${k === "high_above" ? "Seuil élevé" : "Seuil faible"} : ${pct(v)}</title></line>`);
  }
  const end = at(p);
  const ex = cx + r * Math.cos(end), ey = cy + r * Math.sin(end);
  return `<svg viewBox="0 0 230 190" role="img" aria-label="Probabilité ${pct(p)}">
    <path d="${arcPath(cx, cy, r, a0, a1)}" stroke="rgba(255,255,255,.16)" stroke-width="14" fill="none" stroke-linecap="round"/>
    <path d="${arcPath(cx, cy, r, a0, Math.max(end, a0 + 0.001))}" stroke="${lv.color}" stroke-width="14" fill="none" stroke-linecap="round"/>
    ${marks.join("")}
    <circle cx="${ex}" cy="${ey}" r="9" fill="${lv.color}" stroke="#0c3d63" stroke-width="3"/>
    <text x="${cx + (r + 2) * Math.cos(a0)}" y="${cy + (r + 2) * Math.sin(a0) + 22}" fill="rgba(255,255,255,.6)" font-size="11" text-anchor="middle">0 %</text>
    <text x="${cx + (r + 2) * Math.cos(a1)}" y="${cy + (r + 2) * Math.sin(a1) + 22}" fill="rgba(255,255,255,.6)" font-size="11" text-anchor="middle">100 %</text>
  </svg>`;
}

/** Colonnes (profil 24 h, histogramme). */
function columnChart(el, values, opts) {
  const w = W(el), h = opts.height || 150, padL = 34, padR = 6, padT = 10, padB = 24;
  const n = values.length, iw = w - padL - padR, ih = h - padT - padB;
  const max = niceMax(Math.max(...values.map((v) => v || 0)) * 1.05);
  const band = iw / n, bw = Math.min(24, Math.max(3, band - 2));
  const xOf = (i) => padL + band * i + band / 2;
  const y = (v) => padT + ih - (v / max) * ih;
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(opts.label)}">`;
  for (const t of ticks(max, 3)) s += `<line class="grid" x1="${padL}" x2="${w - padR}" y1="${y(t)}" y2="${y(t)}"/><text class="tick" x="${padL - 6}" y="${y(t) + 4}" text-anchor="end">${opts.fmtTick(t)}</text>`;
  values.forEach((v, i) => {
    const x = xOf(i) - bw / 2, top = y(v || 0), bh = Math.max(0, padT + ih - top), rr = Math.min(4, bw / 2, bh);
    const fill = opts.colorOf ? opts.colorOf(i) : "var(--series-1)";
    s += `<path data-i="${i}" d="M${x} ${padT + ih} V${top + rr} Q${x} ${top} ${x + rr} ${top} H${x + bw - rr} Q${x + bw} ${top} ${x + bw} ${top + rr} V${padT + ih} Z" fill="${fill}"/>`;
  });
  s += `<line class="axis" x1="${padL}" x2="${w - padR}" y1="${padT + ih}" y2="${padT + ih}"/>`;
  values.forEach((_, i) => { const l = opts.xLabel(i); if (l) s += `<text class="tick" x="${xOf(i)}" y="${h - 6}" text-anchor="middle">${l}</text>`; });
  s += "</svg>";
  el.innerHTML = s;
  const svg = el.querySelector("svg");
  const bars = svg.querySelectorAll("path[data-i]");
  attachHover(el, svg, n, xOf, opts.tip, (i) => bars.forEach((b, k) => b.setAttribute("opacity", i == null || k === i ? 1 : 0.45)));
}

/** Courbe temporelle avec seuils, crises et heures sans montre. */
function lineChart(el, series, opts) {
  const w = W(el), h = opts.height || 210, padL = 40, padR = 10, padT = 16, padB = 26;
  const n = series.length, iw = w - padL - padR, ih = h - padT - padB;
  const vmax = Math.max(...series.filter((v) => v != null), ...(opts.refs || []).map((r) => r.v));
  const max = opts.max ?? Math.min(1, niceMax(vmax * 1.08));
  const xOf = (i) => padL + (iw * i) / Math.max(1, n - 1);
  const y = (v) => padT + ih - (Math.min(v, max) / max) * ih;
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(opts.label)}">`;
  for (const t of ticks(max, 4)) s += `<line class="grid" x1="${padL}" x2="${w - padR}" y1="${y(t)}" y2="${y(t)}"/><text class="tick" x="${padL - 6}" y="${y(t) + 4}" text-anchor="end">${opts.fmtTick(t)}</text>`;
  // heures sans montre : bande grise en pied de graphique
  if (opts.worn) {
    let a = null;
    for (let i = 0; i <= n; i++) {
      const off = i < n && !opts.worn[i];
      if (off && a == null) a = i;
      if (!off && a != null) { s += `<rect x="${xOf(a)}" y="${padT + ih - 4}" width="${Math.max(1, xOf(i - 1) - xOf(a))}" height="4" fill="var(--series-muted)"/>`; a = null; }
    }
  }
  // seuils
  for (const r of opts.refs || []) {
    if (r.v == null || r.v > max) continue;
    s += `<line x1="${padL}" x2="${w - padR}" y1="${y(r.v)}" y2="${y(r.v)}" stroke="${r.color}" stroke-width="1" opacity=".9"/>`;
  }
  // aire + ligne
  let d = "", started = false;
  series.forEach((v, i) => { if (v == null) { started = false; return; } d += `${started ? "L" : "M"}${xOf(i).toFixed(1)} ${y(v).toFixed(1)}`; started = true; });
  const first = series.findIndex((v) => v != null), last = series.length - 1 - [...series].reverse().findIndex((v) => v != null);
  if (first >= 0) s += `<path d="${d} L${xOf(last)} ${padT + ih} L${xOf(first)} ${padT + ih} Z" fill="var(--series-1-wash)"/>`;
  s += `<path d="${d}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
  // crises réelles
  for (const k of opts.marks || []) {
    if (k < 0 || k >= n) continue;
    s += `<line x1="${xOf(k)}" x2="${xOf(k)}" y1="${padT}" y2="${padT + ih}" stroke="var(--crit)" stroke-width="1" opacity=".35"/>`;
    s += `<circle cx="${xOf(k)}" cy="${padT}" r="4.5" fill="var(--crit)" stroke="var(--surface)" stroke-width="2"/>`;
  }
  s += `<line class="axis" x1="${padL}" x2="${w - padR}" y1="${padT + ih}" y2="${padT + ih}"/>`;
  for (const [i, l] of opts.xTicks || []) s += `<text class="tick" x="${xOf(i)}" y="${h - 7}" text-anchor="middle">${l}</text>`;
  s += `<line class="cross" id="cross" x1="0" x2="0" y1="${padT}" y2="${padT + ih}" visibility="hidden"/><circle id="crossDot" r="4.5" fill="var(--series-1)" stroke="var(--surface)" stroke-width="2" visibility="hidden"/>`;
  s += "</svg>";
  el.innerHTML = s;
  const svg = el.querySelector("svg"), cross = svg.querySelector("#cross"), dot = svg.querySelector("#crossDot");
  attachHover(el, svg, n, xOf, opts.tip, (i) => {
    const vis = i == null || series[i] == null ? "hidden" : "visible";
    cross.setAttribute("visibility", vis); dot.setAttribute("visibility", vis);
    if (vis === "visible") { cross.setAttribute("x1", xOf(i)); cross.setAttribute("x2", xOf(i)); dot.setAttribute("cx", xOf(i)); dot.setAttribute("cy", y(series[i])); }
  });
}

/** Courbe divergente autour de 0 (décalage transmis à la branche 2). */
function shiftChart(el, values, start, cap) {
  const w = W(el), h = 150, padL = 34, padR = 8, padT = 12, padB = 24;
  const n = values.length, iw = w - padL - padR, ih = h - padT - padB;
  const xOf = (i) => padL + (iw * i) / Math.max(1, n - 1);
  const y = (v) => padT + ih / 2 - (v / cap) * (ih / 2);
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Décalage a priori sur 7 jours">`;
  for (const t of [-cap, 0, cap]) s += `<line class="${t === 0 ? "axis" : "grid"}" x1="${padL}" x2="${w - padR}" y1="${y(t)}" y2="${y(t)}"/><text class="tick" x="${padL - 6}" y="${y(t) + 4}" text-anchor="end">${signed(t, 0)}</text>`;
  let d = "";
  values.forEach((v, i) => { d += `${i ? "L" : "M"}${xOf(i).toFixed(1)} ${y(v ?? 0).toFixed(1)}`; });
  s += `<clipPath id="cpUp"><rect x="0" y="0" width="${w}" height="${y(0)}"/></clipPath><clipPath id="cpDn"><rect x="0" y="${y(0)}" width="${w}" height="${h}"/></clipPath>`;
  const area = `${d} L${xOf(n - 1)} ${y(0)} L${xOf(0)} ${y(0)} Z`;
  s += `<path d="${area}" fill="var(--crit)" opacity=".14" clip-path="url(#cpUp)"/><path d="${area}" fill="var(--series-1)" opacity=".16" clip-path="url(#cpDn)"/>`;
  s += `<path d="${d}" fill="none" stroke="var(--ink-2)" stroke-width="2" stroke-linejoin="round"/>`;
  const days = [];
  for (let i = 0; i < n; i++) { const t = addHours(start, i); if (t.getHours() === 0) days.push(i); }
  for (const i of days) s += `<text class="tick" x="${xOf(i)}" y="${h - 7}" text-anchor="middle">${DAYS[addHours(start, i).getDay()]}</text>`;
  s += "</svg>";
  el.innerHTML = s;
  attachHover(el, el.querySelector("svg"), n, xOf, (i) => {
    const t = addHours(start, i), v = values[i];
    return `<b>${signed(v)}</b><span class="t-sub">${fmtDay(t)} · ${fmtTime(t)}</span><br>${v > 0.05 ? "Détecteur plus sensible" : v < -0.05 ? "Détecteur moins sensible" : "Sans effet"}`;
  });
}

/** Horloge des crises (histogramme polaire 24 h). */
function clockChart(el, hist) {
  const size = Math.min(W(el), 300), c = size / 2, r0 = size * 0.17, r1 = size * 0.42;
  const max = Math.max(1, ...hist);
  let s = `<svg viewBox="0 0 ${size} ${size}" role="img" aria-label="Heures des crises" style="max-width:${size}px;margin:0 auto">`;
  for (const f of [0.5, 1]) s += `<circle cx="${c}" cy="${c}" r="${r0 + (r1 - r0) * f}" fill="none" class="grid"/>`;
  s += `<circle cx="${c}" cy="${c}" r="${r0}" fill="none" class="axis"/>`;
  const step = (Math.PI * 2) / 24;
  hist.forEach((v, hh) => {
    if (!v) return;
    const a0 = -Math.PI / 2 + hh * step + 0.03, a1 = a0 + step - 0.06, rr = r0 + ((r1 - r0) * v) / max;
    const p = (a, r) => `${(c + r * Math.cos(a)).toFixed(2)} ${(c + r * Math.sin(a)).toFixed(2)}`;
    s += `<path data-i="${hh}" d="M${p(a0, r0)} L${p(a0, rr)} A${rr} ${rr} 0 0 1 ${p(a1, rr)} L${p(a1, r0)} A${r0} ${r0} 0 0 0 ${p(a0, r0)} Z" fill="var(--series-1)"/>`;
  });
  for (const [hh, l] of [[0, "0 h"], [6, "6 h"], [12, "12 h"], [18, "18 h"]]) {
    const a = -Math.PI / 2 + hh * step, rr = r1 + 14;
    s += `<text class="tick" x="${c + rr * Math.cos(a)}" y="${c + rr * Math.sin(a) + 4}" text-anchor="middle">${l}</text>`;
  }
  const total = hist.reduce((a, b) => a + b, 0);
  s += `<text x="${c}" y="${c - 2}" text-anchor="middle" font-size="22" font-weight="700" fill="var(--ink)">${total}</text><text x="${c}" y="${c + 15}" text-anchor="middle" class="tick">épisodes</text></svg>`;
  el.innerHTML = s;
  const svg = el.querySelector("svg");
  const wedges = svg.querySelectorAll("path[data-i]");
  wedges.forEach((wd) => {
    const hh = +wd.dataset.i;
    const show = (e) => { const b = wd.getBoundingClientRect(); wedges.forEach((x) => x.setAttribute("opacity", x === wd ? 1 : 0.45));
      showTip(b.left + b.width / 2, b.top, `<b>${hist[hh]} épisode${hist[hh] > 1 ? "s" : ""}</b><span class="t-sub">entre ${hh} h et ${hh + 1} h</span>`); e.stopPropagation(); };
    wd.addEventListener("pointerdown", show); wd.addEventListener("pointerenter", show);
  });
  el.addEventListener("pointerleave", () => { hideTip(); wedges.forEach((x) => x.setAttribute("opacity", 1)); });
}

/** Barres horizontales : AUC par modèle, avec repères hasard et SeFEF. */
function aucBars(el, rows, sefef) {
  const w = W(el), rowH = 46, padL = 4, padR = 46, padT = 6, h = padT + rows.length * rowH + 26;
  const iw = w - padL - padR;
  const x = (v) => padL + iw * Math.min(Math.max(v, 0), 1);
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="AUC par modèle">`;
  for (const t of [0, 0.25, 0.5, 0.75, 1]) s += `<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${padT}" y2="${h - 22}"/><text class="tick" x="${x(t)}" y="${h - 6}" text-anchor="middle">${nf(2).format(t)}</text>`;
  rows.forEach((r, k) => {
    const y0 = padT + k * rowH;
    s += `<text x="${padL}" y="${y0 + 13}" font-size="13" font-weight="${r.key === "epicare" ? 700 : 600}" fill="var(--ink)">${esc(MODELS[r.key]?.name || r.key)}</text>`;
    const bw = Math.max(0, x(r.auc ?? 0) - padL), by = y0 + 20, bh = 14, rr = Math.min(4, bw);
    if (r.auc != null) s += `<path data-i="${k}" d="M${padL} ${by} H${padL + bw - rr} Q${padL + bw} ${by} ${padL + bw} ${by + rr} V${by + bh - rr} Q${padL + bw} ${by + bh} ${padL + bw - rr} ${by + bh} H${padL} Z" fill="${r.key === "epicare" ? "var(--series-1)" : "var(--series-muted)"}"/>`;
    s += `<text x="${x(r.auc ?? 0) + 6}" y="${by + 11}" font-size="12" font-weight="650" fill="var(--ink)">${r.auc == null ? "—" : nf(2).format(r.auc)}</text>`;
  });
  s += `<line x1="${x(0.5)}" x2="${x(0.5)}" y1="${padT}" y2="${h - 22}" stroke="var(--ink-3)" stroke-width="1.5"/>`;
  if (sefef != null) s += `<line x1="${x(sefef)}" x2="${x(sefef)}" y1="${padT}" y2="${h - 22}" stroke="var(--brand-2)" stroke-width="1.5"/>`;
  s += "</svg>";
  el.innerHTML = s;
  const svg = el.querySelector("svg");
  svg.querySelectorAll("path[data-i]").forEach((b) => {
    const r = rows[+b.dataset.i];
    const show = () => { const bb = b.getBoundingClientRect();
      showTip(bb.right, bb.top, `<b>AUC ${nf(3).format(r.auc)}</b><span class="t-sub">${esc(MODELS[r.key]?.sub || "")}</span><br>BSS ${signed(r.bss, 3)} · ${num(r.fa, 2)} fausse(s) alerte(s)/j`); };
    b.addEventListener("pointerdown", show); b.addEventListener("pointerenter", show); b.addEventListener("pointerleave", hideTip);
  });
}

/** Diagramme de fiabilité (calibration). */
function reliabilityChart(el, pts) {
  const w = W(el), h = Math.min(260, w * 0.75), pad = 40, padR = 12, padT = 10;
  const max = niceMax(Math.max(...pts.flatMap((p) => [p.p, p.obs])) * 1.1);
  const x = (v) => pad + ((w - pad - padR) * v) / max, y = (v) => padT + (h - padT - pad + 12) * (1 - v / max);
  const y0 = y(0);
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Diagramme de fiabilité">`;
  for (const t of ticks(max, 4)) {
    s += `<line class="grid" x1="${pad}" x2="${w - padR}" y1="${y(t)}" y2="${y(t)}"/><text class="tick" x="${pad - 6}" y="${y(t) + 4}" text-anchor="end">${pct(t, 1)}</text>`;
    s += `<text class="tick" x="${x(t)}" y="${y0 + 16}" text-anchor="middle">${pct(t, 1)}</text>`;
  }
  s += `<line x1="${x(0)}" y1="${y(0)}" x2="${x(max)}" y2="${y(max)}" stroke="var(--ink-3)" stroke-width="1"/>`;
  s += `<text class="lbl" x="${x(max * 0.98)}" y="${y(max * 0.98) + 14}" text-anchor="end">idéal</text>`;
  let d = ""; pts.forEach((p, i) => { d += `${i ? "L" : "M"}${x(p.p)} ${y(p.obs)}`; });
  s += `<path d="${d}" fill="none" stroke="var(--series-1)" stroke-width="2"/>`;
  pts.forEach((p, i) => { s += `<circle data-i="${i}" cx="${x(p.p)}" cy="${y(p.obs)}" r="5" fill="var(--series-1)" stroke="var(--surface)" stroke-width="2"/>`; });
  s += "</svg>";
  el.innerHTML = s;
  el.querySelectorAll("circle[data-i]").forEach((c) => {
    const p = pts[+c.dataset.i];
    const show = () => { const b = c.getBoundingClientRect(); showTip(b.left + b.width / 2, b.top, `<b>Prévu ${pct(p.p)} · observé ${pct(p.obs)}</b><span class="t-sub">${p.n} heures</span>`); };
    c.addEventListener("pointerdown", show); c.addEventListener("pointerenter", show); c.addEventListener("pointerleave", hideTip);
  });
}

/* table de données (accessibilité : chaque graphique a sa vue tableau) */
function tableToggle(card, headers, rows) {
  const btn = document.createElement("button");
  btn.className = "table-toggle"; btn.textContent = "Afficher le tableau";
  const box = document.createElement("div"); box.hidden = true;
  box.innerHTML = `<table class="data"><thead><tr>${headers.map((h, i) => `<th class="${i ? "n" : ""}">${h}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c, i) => `<td class="${i ? "n" : ""}">${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  btn.onclick = () => { box.hidden = !box.hidden; btn.textContent = box.hidden ? "Afficher le tableau" : "Masquer le tableau"; };
  card.append(btn, box);
}

/* ============================================================ vues */
const $ = (id) => document.getElementById(id);
function card(html, cls = "") { const d = document.createElement("div"); d.className = `card ${cls}`; d.innerHTML = html; return d; }
function badge(levelKey) { const l = LEVELS[levelKey] || LEVELS.low; return `<span class="badge ${l.cls}">${ico(l.icon)}${l.label}</span>`; }

function renderHome() {
  const v = $("view-home"); v.innerHTML = "";
  const p = patient(); if (!p) return emptyData(v);
  const c = p.current || {};
  const t = parseLocal(c.time);
  const lv = LEVELS[c.level] || LEVELS.low;
  const hero = document.createElement("div");
  hero.className = "hero";
  hero.innerHTML = `
    <div class="hero-top"><span>Risque · 24 prochaines heures</span><span>${t ? `${fmtDay(t)} · ${fmtTime(t)}` : ""}</span></div>
    <div class="hero-gauge">${gaugeSVG(c.probability, p.timeline?.levels, c.level)}
      <div class="hero-value"><div class="num">${nf(c.probability >= 0.1 ? 0 : 1).format((c.probability || 0) * 100)}<small>%</small></div><div class="cap">probabilité calibrée</div></div>
    </div>
    <div class="hero-center">
      <div class="level-pill"><span class="dot" style="background:${lv.color}">${ico(lv.icon)}</span>Risque ${lv.label.toLowerCase()}</div>
      <p class="hero-msg" style="margin-top:10px">${esc(messageFr(c.probability))}</p>
    </div>`;
  v.appendChild(hero);

  const tiles = document.createElement("div"); tiles.className = "tiles";
  tiles.innerHTML = `
    <div class="tile"><div class="k">${ico("hourglass")}Dans 1 h</div><div class="v">${pct(c.probability_next_hour)}</div><div class="s">probabilité</div></div>
    <div class="tile"><div class="k">${ico("baseline")}Habituel</div><div class="v">${pct(c.baseline_probability)}</div><div class="s">en moyenne</div></div>
    <div class="tile"><div class="k">${ico("medal")}Confiance</div><div class="v">${CONF[c.confidence] || "—"}</div><div class="s">${p.model?.n_training_events ?? "?"} épisodes</div></div>`;
  v.appendChild(tiles);

  // profil 24 h
  if (Array.isArray(c.profile_24h) && t) {
    const cc = card(`<div class="card-head"><div><div class="card-title">Heure par heure</div><div class="card-sub">Probabilité d'une crise dans chacune des 24 prochaines heures</div></div></div><div class="chart" id="profileChart"></div>`);
    v.appendChild(cc);
    const vals = c.profile_24h, peak = vals.indexOf(Math.max(...vals));
    columnChart(cc.querySelector("#profileChart"), vals, {
      label: "Profil des 24 prochaines heures", height: 150,
      fmtTick: (x) => pct(x, x === 0 ? 0 : 1),
      xLabel: (i) => { const d = addHours(t, i); return i % 6 === 0 ? `${d.getHours()} h` : ""; },
      colorOf: (i) => (i === peak ? "var(--series-1)" : "color-mix(in srgb, var(--series-1) 55%, var(--surface))"),
      tip: (i) => { const d = addHours(t, i); return `<b>${pct(vals[i])}</b><span class="t-sub">${fmtTime(d)} – ${fmtTime(addHours(d, 1))}</span>`; },
    });
    const pk = addHours(t, peak);
    cc.insertAdjacentHTML("beforeend", `<div class="legend">${ico("info", "sm")}<span>Heure la plus à risque : <b style="color:var(--ink)">${fmtTime(pk)}–${fmtTime(addHours(pk, 1))}</b> (${pct(vals[peak])})</span></div>`);
  }

  // facteurs
  const drivers = (c.drivers || []).map(driverInfo);
  v.appendChild(card(`<div class="card-head"><div class="card-title">Pourquoi ce niveau ?</div></div>
    <div class="list">${drivers.length ? drivers.map((d) => `<div class="row"><div class="row-ico">${ico(d.icon)}</div><div class="row-main"><div class="row-title">${esc(d.title)}</div><div class="row-sub">${esc(d.sub)}</div></div></div>`).join("")
      : `<div class="empty-line">Aucun facteur ne s'écarte de l'habitude en ce moment.</div>`}</div>`));

  // lien avec la branche 2
  v.appendChild(shiftCard(c.prior_shift_for_detector, p.prior_shift?.cap || 1));
  v.insertAdjacentHTML("beforeend", `<p class="fine" style="margin:2px 4px">EpiCare est un outil de recherche. Il ne remplace pas l'avis d'un médecin et ne doit pas modifier un traitement.</p>`);
}

function shiftCard(shift, cap) {
  const d2 = b2patient();
  const pos = ((shift ?? 0) + cap) / (2 * cap) * 100;
  const color = shift > 0.05 ? "var(--crit)" : shift < -0.05 ? "var(--series-1)" : "var(--ink-3)";
  const left = Math.min(50, pos), width = Math.abs(pos - 50);
  const text = shift > 0.05 ? "Le détecteur de crises sera <b>plus sensible</b> pendant cette période."
    : shift < -0.05 ? "Le détecteur de crises sera <b>moins sensible</b> : moins de fausses alertes."
    : "Le détecteur garde sa sensibilité habituelle.";
  const status = d2 ? `<span class="badge good">${ico("link")}Connecté</span>` : `<span class="badge neutral">${ico("clock")}Branche 2 à venir</span>`;
  return card(`<div class="card-head"><div><div class="card-title">Ajustement du détecteur</div><div class="card-sub">Valeur transmise à la branche 2</div></div>${status}</div>
    <div style="display:flex;align-items:baseline;gap:8px"><span style="font-size:28px;font-weight:700;letter-spacing:-.02em">${signed(shift)}</span><span class="row-sub">log(r / r̄), borné à ±${num(cap, 0)}</span></div>
    <div class="shift-bar"><div class="fill" style="left:${left}%;width:${width}%;background:${color};opacity:.35"></div><div class="mid"></div><div class="knob" style="left:${pos}%;background:${color}"></div></div>
    <div class="shift-scale"><span>moins sensible</span><span>habituel</span><span>plus sensible</span></div>
    <p class="row-sub" style="margin-top:10px">${text}</p>`);
}

function renderTrends() {
  const v = $("view-trends"); v.innerHTML = "";
  const p = patient(); if (!p) return emptyData(v);
  v.insertAdjacentHTML("beforeend", `<h1 class="page-title">Tendances</h1><p class="page-sub">Prévisions sur des jours que le modèle n'avait jamais vus, comparées aux crises réellement survenues.</p>`);
  const tl = p.timeline;
  if (tl && tl.start) {
    const start = parseLocal(tl.start), key = state.trendH;
    const series = key === "24" ? tl.p24 : tl.p1;
    const marks = (tl.seizures || []).map((s) => Math.round((parseLocal(s) - start) / 3600e3));
    const xt = []; for (let i = 0; i < series.length; i++) { const d = addHours(start, i); if (d.getHours() === 0 && d.getDate() % 3 === 0) xt.push([i, `${d.getDate()} ${MONTHS[d.getMonth()]}`]); }
    const cc = card(`<div class="card-head"><div><div class="card-title">Risque prévu</div><div class="card-sub">${Math.round(series.length / 24)} derniers jours de test</div></div>
      <div class="seg" id="segH"><button data-h="24" class="${key === "24" ? "on" : ""}">24 h</button><button data-h="1" class="${key === "1" ? "on" : ""}">1 h</button></div></div>
      <div class="chart" id="tlChart"></div>
      <div class="legend"><span><i class="ln"></i>Prévision EpiCare</span><span><i class="dt"></i>Crise réelle</span>${key === "24" ? `<span><i class="sq" style="background:var(--crit);height:2px;border-radius:0"></i>Seuil élevé</span><span><i class="sq" style="background:var(--good);height:2px;border-radius:0"></i>Seuil faible</span>` : ""}<span><i class="sq" style="background:var(--series-muted);height:4px;border-radius:0"></i>Montre non portée</span></div>`);
    v.appendChild(cc);
    cc.querySelectorAll("#segH button").forEach((b) => (b.onclick = () => { state.trendH = b.dataset.h; renderTrends(); }));
    const refs = key === "24" ? [{ v: tl.levels?.high_above, color: "var(--crit)", label: "élevé" }, { v: tl.levels?.low_below, color: "var(--good)", label: "faible" }] : [];
    lineChart(cc.querySelector("#tlChart"), series, {
      label: "Risque prévu", refs, worn: tl.worn, marks, xTicks: xt,
      fmtTick: (x) => pct(x, key === "24" ? 0 : x === 0 ? 0 : 1),
      tip: (i) => { const d = addHours(start, i); const sz = marks.filter((k) => Math.abs(k - i) <= 1).length;
        return `<b>${pct(series[i])}</b><span class="t-sub">${fmtDay(d)} · ${fmtTime(d)}</span>${sz ? `<br>● Crise à cette heure` : ""}${tl.worn && !tl.worn[i] ? "<br>Montre non portée" : ""}`; },
    });
    // résumé de la période
    const n24 = tl.p24.filter((x) => x != null);
    const hi = tl.levels?.high_above, timeHigh = hi != null ? n24.filter((x) => x >= hi).length / n24.length : null;
    const caught = hi != null ? marks.filter((k) => k >= 0 && k < tl.p24.length && tl.p24[Math.max(0, k - 1)] >= hi).length : null;
    const worn = tl.worn ? tl.worn.filter(Boolean).length / tl.worn.length : null;
    const tiles = document.createElement("div"); tiles.className = "tiles four";
    tiles.innerHTML = `
      <div class="tile"><div class="k">${ico("bolt")}Crises</div><div class="v">${marks.length}</div><div class="s">sur la période</div></div>
      <div class="tile"><div class="k">${ico("warning")}En risque élevé</div><div class="v">${pct(timeHigh, 0)}</div><div class="s">du temps</div></div>
      <div class="tile"><div class="k">${ico("target")}Anticipées</div><div class="v">${caught == null ? "—" : `${caught}/${marks.length}`}</div><div class="s">en risque élevé</div></div>
      <div class="tile"><div class="k">${ico("watch")}Port</div><div class="v">${pct(worn, 0)}</div><div class="s">des heures</div></div>`;
    v.appendChild(tiles);
  }
  if (p.prior_shift?.values?.length) {
    const ps = p.prior_shift, cc = card(`<div class="card-head"><div><div class="card-title">Signal envoyé au détecteur</div><div class="card-sub">7 derniers jours · au-dessus de 0 : détecteur plus sensible</div></div></div><div class="chart" id="shChart"></div>`);
    v.appendChild(cc);
    shiftChart(cc.querySelector("#shChart"), ps.values, parseLocal(ps.start), ps.cap || 1);
  }
}

function renderCycles() {
  const v = $("view-cycles"); v.innerHTML = "";
  const p = patient(); if (!p) return emptyData(v);
  const s = p.summary || {};
  v.insertAdjacentHTML("beforeend", `<h1 class="page-title">Cycles</h1><p class="page-sub">Les rythmes propres à ce patient, appris à partir de l'heure des crises seulement.</p>`);
  const tiles = document.createElement("div"); tiles.className = "tiles four";
  tiles.innerHTML = `
    <div class="tile"><div class="k">${ico("calendar")}Suivi</div><div class="v">${num(s.days, 0)} j</div><div class="s">enregistrés</div></div>
    <div class="tile"><div class="k">${ico("watch")}Port</div><div class="v">${pct(s.worn_fraction, 0)}</div><div class="s">des heures</div></div>
    <div class="tile"><div class="k">${ico("bolt")}Crises</div><div class="v">${s.n_seizures ?? "—"}</div><div class="s">${s.n_events ?? "—"} épisodes</div></div>
    <div class="tile"><div class="k">${ico("repeat")}Fréquence</div><div class="v">${num(p.cycles?.base_rate_per_day, 2)}</div><div class="s">épisode / jour</div></div>`;
  v.appendChild(tiles);

  const cyc = p.cycles?.cycles || [];
  v.appendChild(card(`<div class="card-head"><div><div class="card-title">Cycles détectés</div><div class="card-sub">Test de Rayleigh, correction de Bonferroni</div></div><span class="badge ${cyc.length ? "good" : "neutral"}">${ico(cyc.length ? "checkCircle" : "info")}${cyc.length} trouvé${cyc.length > 1 ? "s" : ""}</span></div>
    <div class="list">${cyc.length ? cyc.map((c) => {
      const daily = /h$/.test(c.period);
      const per = daily ? c.period.replace(" h", " heures") : c.period.replace(" d", " jours").replace(".", ",");
      const peak = (c.peak || "").replace(/daily cycle, peak around (\d+):00 local time/, "pic vers $1 h (heure locale)").replace(/.* cycle, peak at phase ([\d.]+)/, (_, f) => `pic à ${Math.round(+f * 100)} % du cycle`);
      const strength = c.R >= 0.5 ? "fort" : c.R >= 0.3 ? "modéré" : "faible";
      return `<div class="row"><div class="row-ico">${ico(daily ? "clock" : "repeat")}</div><div class="row-main"><div class="row-title">Cycle de ${esc(per)}</div><div class="row-sub">${esc(peak)} · rythme ${strength}</div></div><div class="row-end">R = ${num(c.R, 2)}<small>p = ${c.p < 0.001 ? c.p.toExponential(1).replace(".", ",") : num(c.p, 3)}</small></div></div>`;
    }).join("") : `<div class="empty-line">Aucun cycle significatif : la prévision s'appuie sur la fréquence moyenne et les capteurs.</div>`}</div>`));

  if (Array.isArray(p.event_hour_hist)) {
    const cc = card(`<div class="card-head"><div><div class="card-title">Horloge des crises</div><div class="card-sub">Nombre d'épisodes selon l'heure de la journée</div></div></div><div class="chart" id="clock"></div>`);
    v.appendChild(cc);
    clockChart(cc.querySelector("#clock"), p.event_hour_hist);
    tableToggle(cc, ["Heure", "Épisodes"], p.event_hour_hist.map((n, h) => [`${h} h – ${h + 1} h`, n]));
  }
}

function renderPerf() {
  const v = $("view-perf"); v.innerHTML = "";
  const B = b1(), p = patient(); if (!B || !p) return emptyData(v);
  v.insertAdjacentHTML("beforeend", `<h1 class="page-title">Fiabilité</h1><p class="page-sub">Validation croisée temporelle : chaque modèle est testé uniquement sur des données futures.</p>`);
  const H = state.perfH, scope = state.perfScope;
  const M = (scope === "all" ? B.metrics : p.metrics)?.[H] || {};
  const rows = MODEL_ORDER.filter((k) => M[k]).map((k) => ({ key: k, auc: M[k].auc, bss: M[k].bss, fa: M[k].fa_per_day, folds: M[k].folds }));
  const sefef = B.sefef_baseline_auc?.[H === "1h" ? "hourly" : "daily"]?.vMe;
  const nP = (B.patients || []).length;
  const cc = card(`<div class="card-head" style="flex-wrap:wrap"><div class="seg" id="segScope"><button data-s="all" class="${scope === "all" ? "on" : ""}">${nP} patient${nP > 1 ? "s" : ""}</button><button data-s="one" class="${scope === "one" ? "on" : ""}">Patient ${esc(p.id)}</button></div>
    <div class="seg" id="segPH"><button data-h="1h" class="${H === "1h" ? "on" : ""}">1 h</button><button data-h="24h" class="${H === "24h" ? "on" : ""}">24 h</button></div></div>
    <div class="card-title">Capacité à anticiper (AUC)</div><div class="card-sub" style="margin-bottom:8px">0,5 = hasard · 1 = parfait</div>
    <div class="chart" id="aucChart"></div>
    <div class="legend"><span><i class="sq" style="background:var(--series-1)"></i>EpiCare</span><span><i class="sq" style="background:var(--series-muted)"></i>Autres modèles</span><span><i class="sq" style="width:2px;height:12px;background:var(--ink-3);border-radius:0"></i>Hasard</span>${sefef != null ? `<span><i class="sq" style="width:2px;height:12px;background:var(--brand-2);border-radius:0"></i>Meilleur résultat publié SeFEF (${nf(2).format(sefef)})</span>` : ""}</div>`);
  v.appendChild(cc);
  cc.querySelectorAll("#segScope button").forEach((b) => (b.onclick = () => { state.perfScope = b.dataset.s; renderPerf(); }));
  cc.querySelectorAll("#segPH button").forEach((b) => (b.onclick = () => { state.perfH = b.dataset.h; renderPerf(); }));
  if (rows.length) {
    aucBars(cc.querySelector("#aucChart"), rows, sefef);
    tableToggle(cc, ["Modèle", "AUC", "BSS", "FA/j"], rows.map((r) => [esc(MODELS[r.key].name), num(r.auc, 3), signed(r.bss, 3), num(r.fa, 2)]));
  } else cc.querySelector("#aucChart").innerHTML = `<div class="empty-line">Pas de résultat pour cet horizon.</div>`;

  const ep = M.epicare;
  if (ep) {
    const st = ep.bss > 0.05 ? ["good", "checkCircle", "Mieux que la moyenne"] : ep.bss >= 0 ? ["neutral", "info", "Proche de la moyenne"] : ["warn", "alert", "Moins juste que la moyenne"];
    v.appendChild(card(`<div class="card-head"><div class="card-title">EpiCare en bref</div><span class="badge ${st[0]}">${ico(st[1])}${st[2]}</span></div>
      <div class="list">
        <div class="row"><div class="row-ico">${ico("target")}</div><div class="row-main"><div class="row-title">Discrimination</div><div class="row-sub">Classe les périodes à risque avant les autres</div></div><div class="row-end">${num(ep.auc, 2)}<small>AUC</small></div></div>
        <div class="row"><div class="row-ico">${ico("sliders")}</div><div class="row-main"><div class="row-title">Justesse des probabilités</div><div class="row-sub">Gain sur la prévision « toujours la moyenne »</div></div><div class="row-end">${signed(ep.bss, 3)}<small>BSS</small></div></div>
        <div class="row"><div class="row-ico">${ico("bell")}</div><div class="row-main"><div class="row-title">Fausses alertes</div><div class="row-sub">Au seuil choisi sur l'entraînement</div></div><div class="row-end">${num(ep.fa_per_day, 2)}<small>par jour</small></div></div>
        <div class="row"><div class="row-ico">${ico("repeat")}</div><div class="row-main"><div class="row-title">Évaluation</div><div class="row-sub">Nombre de plis de validation</div></div><div class="row-end">${ep.folds}<small>plis</small></div></div>
      </div>`));
  }

  if (scope === "one" && p.reliability_1h?.length) {
    const rc = card(`<div class="card-head"><div><div class="card-title">Calibration (1 h)</div><div class="card-sub">Quand EpiCare annonce x %, une crise survient-elle x % du temps ?</div></div></div><div class="chart" id="relChart"></div>`);
    v.appendChild(rc);
    reliabilityChart(rc.querySelector("#relChart"), p.reliability_1h);
    tableToggle(rc, ["Prévu", "Observé", "Heures"], p.reliability_1h.map((r) => [pct(r.p), pct(r.obs), r.n]));
  }

  if (B.events_seen?.length) {
    const hN = H === "1h" ? 1 : 24, es = B.events_seen.filter((r) => r.horizon_h === hN && r.model === "epicare");
    if (es.length) {
      const ec = card(`<div class="card-head"><div><div class="card-title">Apprentissage progressif</div><div class="card-sub">AUC selon le nombre d'épisodes déjà vus</div></div></div><div class="list">${es.map((r) => `<div class="row"><div class="row-ico">${ico("trend")}</div><div class="row-main"><div class="row-title">${r.events === "all" ? "Tout l'historique" : `${r.events} épisode${+r.events > 1 ? "s" : ""}`}</div><div class="row-sub">BSS ${signed(r.bss, 3)}</div></div><div class="row-end">${num(r.auc, 2)}<small>AUC</small></div></div>`).join("")}</div>`);
      v.appendChild(ec);
    }
  }
}

function renderDetect() {
  const v = $("view-detect"); v.innerHTML = "";
  const B2 = b2(), d2 = b2patient();
  v.insertAdjacentHTML("beforeend", `<h1 class="page-title">Détection</h1><p class="page-sub">Branche 2 : détection des crises convulsives par l'accéléromètre et alerte des aidants.</p>`);
  if (!B2) {
    v.appendChild(card(`<div class="empty-hero"><div class="big-ico">${ico("shield")}</div><h3>Branche 2 en préparation</h3><p>Dès que ses résultats seront exportés dans le même fichier, ils apparaîtront ici et seront fusionnés avec la prévision.</p></div>`));
  } else {
    const row = (ic, title, sub, end, endSmall = "") => `<div class="row"><div class="row-ico">${ico(ic)}</div><div class="row-main"><div class="row-title">${title}</div>${sub ? `<div class="row-sub">${sub}</div>` : ""}</div><div class="row-end">${end}${endSmall ? `<small>${endSmall}</small>` : ""}</div></div>`;
    const ok = (good) => (good == null ? "" : good ? `<span class="badge good">${ico("check")}objectif atteint</span>` : `<span class="badge warn">${ico("warning")}objectif non atteint</span>`);
    // ---- ce patient : détecteur sur son poignet, avec la prévision de la branche 1
    if (d2) {
      const al = d2.detections || d2.alerts || [];
      const m = d2.metrics || {};
      const tiles = document.createElement("div"); tiles.className = "tiles";
      tiles.innerHTML = `
        <div class="tile"><div class="k">${ico("bell")}Alertes</div><div class="v">${al.length}</div><div class="s">sur ${num(d2.hours_worn, 0)} h portées</div></div>
        <div class="tile"><div class="k">${ico("warning")}Fausses</div><div class="v">${num(m.fa_per_day ?? m.false_alarms_per_day, 1)}</div><div class="s">par jour</div></div>
        <div class="tile"><div class="k">${ico("target")}Près d'une crise</div><div class="v">${m.n_alarms_near_seizure ?? "—"}</div><div class="s">${m.n_seizures_in_period != null ? `${m.n_seizures_in_period} crise${m.n_seizures_in_period > 1 ? "s" : ""} sur la période` : "alertes"}</div></div>`;
      v.appendChild(tiles);
      if (m.fa_per_day_no_prior != null) {
        const gain = m.fa_per_day_no_prior > 0 ? 1 - (m.fa_per_day ?? 0) / m.fa_per_day_no_prior : null;
        v.appendChild(card(`<div class="card-head"><div><div class="card-title">Apport de la prévision</div><div class="card-sub">Fausses alertes par jour au poignet, pour ce patient</div></div></div><div class="list">
          ${row("watch", "Détecteur seul", "Seuil fixe", num(m.fa_per_day_no_prior, 1), "/ jour")}
          ${row("sliders", "Détecteur + branche 1", "Logit décalé de log(r / r̄), borné à ±1", num(m.fa_per_day, 1), "/ jour")}
          </div>${gain != null ? `<p class="row-sub" style="margin-top:8px">${gain >= 0 ? `${pct(gain, 0)} de fausses alertes en moins avec la prévision.` : `${pct(-gain, 0)} de fausses alertes en plus avec la prévision.`}</p>` : ""}`));
      }
      v.appendChild(card(`<div class="card-head"><div><div class="card-title">Dernières alertes</div><div class="card-sub">${al.length > 10 ? `10 plus récentes sur ${al.length} · ` : ""}${esc(d2.source || "")}</div></div></div><div class="list">${al.length ? al.slice(-10).reverse().map((a) => {
        const t = parseLocal(a.time), near = a.true_seizure ?? a.confirmed;
        return `<div class="row"><div class="row-ico">${ico("bell")}</div><div class="row-main"><div class="row-title">${t ? `${fmtDay(t)} · ${fmtTime(t)}` : esc(a.time)}</div><div class="row-sub">Confiance ${pct(a.confidence ?? a.probability, 0)}${a.prior_shift_applied != null ? ` · ajustement ${signed(a.prior_shift_applied)}` : ""}${a.still_after ? " · immobilité ensuite" : ""}</div></div>${near == null ? "" : near ? `<span class="badge crit">${ico("bolt")}Près d'une crise</span>` : `<span class="badge neutral">${ico("info")}Fausse alerte</span>`}</div>`;
      }).join("") : `<div class="empty-line">Aucune alerte.</div>`}</div>`));
    } else {
      v.appendChild(card(`<div class="empty-hero"><div class="big-ico">${ico("watch")}</div><h3>Pas de données de poignet pour ce patient</h3><p>Les résultats ci-dessous viennent des patients de test de SeizeIT2.</p></div>`));
    }
    // ---- performance mesurée (SeizeIT2, patients jamais vus à l'entraînement)
    const M = B2.metrics || {}, T = B2.targets || {};
    v.appendChild(card(`<div class="card-head"><div><div class="card-title">Performance du détecteur</div><div class="card-sub">${esc(B2.dataset?.name || "SeizeIT2")} · patients de test</div></div></div><div class="list">
      ${row("target", "Crises détectées", `${M.n_detected ?? "—"} sur ${M.n_seizures ?? "—"} crises convulsives ${ok(M.sensitivity != null && T.sensitivity != null ? M.sensitivity >= T.sensitivity : null)}`, pct(M.sensitivity, 0), `objectif ≥ ${pct(T.sensitivity, 0)}`)}
      ${row("warning", "Fausses alertes", `${num(M.hours, 0)} h d'enregistrement ${ok(M.fa_per_day != null && T.fa_per_day != null ? M.fa_per_day < T.fa_per_day : null)}`, num(M.fa_per_day, 2), `/ jour · objectif < ${num(T.fa_per_day, 0)}`)}
      ${row("clock", "Délai médian", `90 % des alertes en moins de ${num(M.delay_p90_s, 0)} s ${ok(M.delay_median_s != null && T.delay_s != null ? M.delay_median_s < T.delay_s : null)}`, `${num(M.delay_median_s, 0)} s`, `objectif < ${num(T.delay_s, 0)} s`)}
      </div>`));
    const PE = B2.prior_effect || [];
    if (PE.length) {
      const L = { none: ["watch", "Sans prévision"], useless: ["repeat", "Prévision inutile"], branch1: ["gauge", "Prévision de la branche 1"], perfect: ["medal", "Prévision parfaite"] };
      v.appendChild(card(`<div class="card-head"><div><div class="card-title">Apport de la prévision (simulation)</div><div class="card-sub">Fausses alertes par jour à ${pct(T.sensitivity ?? 0.9, 0)} de sensibilité</div></div></div><div class="list">${PE.map((r) => row((L[r.prior] || ["info"])[0], (L[r.prior] || [0, r.prior])[1], r.reached_target ? `sensibilité ${pct(r.sensitivity, 0)}` : `objectif non atteint (max ${pct(r.sensitivity, 0)})`, num(r.fa_per_day, 2), "/ jour")).join("")}</div>`));
    }
    const LA = B2.lookalike || [];
    if (LA.length) {
      v.appendChild(card(`<div class="card-head"><div><div class="card-title">Gestes du quotidien</div><div class="card-sub">Alertes par heure d'activité (doit rester à 0)</div></div></div><div class="list">${LA.map((r) => row("move", esc(String(r.activity).replace(/_/g, " ")), `${num(r.hours * 60, 0)} min enregistrées`, num(r.alarms_per_hour, 1), "/ h")).join("")}</div>`));
    }
  }
  // schéma de la fusion
  const steps = [
    ["gauge", "linear-gradient(150deg,#0b2a4a,#0e7490)", "Prévision du risque", "Branche 1 · probabilité sur 1 h et 24 h", true],
    ["sliders", "linear-gradient(150deg,#0e7490,#14b8a6)", "Ajustement a priori", "log(r / r̄) borné à ±1, ajouté au logit du détecteur", true],
    ["watch", B2 ? "linear-gradient(150deg,#1d4ed8,#257de0)" : "#9aa8bb", "Détecteur de crises", "Branche 2 · fenêtres de 10 s, 20 s positives d'affilée", !!B2],
    ["bell", B2 ? "linear-gradient(150deg,#b02a2b,#dc3c3d)" : "#9aa8bb", "Alerte aux aidants", "Notification en cas de crise convulsive", !!B2],
  ];
  v.appendChild(card(`<div class="card-head"><div class="card-title">Comment les deux branches s'assemblent</div></div><div class="flow">${steps.map(([ic, bg, t, s, ready], i) => `
    <div class="flow-step"><div class="flow-rail"><div class="flow-node" style="background:${bg}">${ico(ic)}</div>${i < steps.length - 1 ? '<div class="flow-line"></div>' : ""}</div>
    <div class="flow-text"><div class="row-title">${t} ${ready ? "" : `<span class="badge neutral" style="margin-left:4px">${ico("clock")}à venir</span>`}</div><div class="row-sub">${s}</div></div></div>`).join("")}</div>`));
}

function emptyData(v) {
  v.innerHTML = `<div class="card"><div class="empty-hero"><div class="big-ico">${ico("database")}</div><h3>Aucun résultat chargé</h3><p>Exportez les résultats avec <code>python -m epicare_b1 export-app</code>, ou importez un fichier depuis les Réglages.</p></div></div>`;
}

/* ============================================================ navigation, feuilles */
const RENDER = { home: renderHome, trends: renderTrends, cycles: renderCycles, perf: renderPerf, detect: renderDetect };
function show(view, push = true) {
  if (!RENDER[view]) view = "home";
  if (push && location.hash !== `#${view}`) history.pushState(null, "", `#${view}`);
  state.view = view; hideTip();
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view));
  document.querySelectorAll(".view").forEach((s) => (s.hidden = s.id !== `view-${view}`));
  RENDER[view]();
  window.scrollTo({ top: 0 });
}
function renderAll() {
  const p = patient();
  $("patientLabel").textContent = p ? `Patient ${p.id}` : "—";
  $("synthNotice").hidden = !state.doc?.dataset?.synthetic;
  $("brandSub").textContent = b2() ? "Prévision et détection" : "Prévision du risque";
  RENDER[state.view]();
}

function openSheet(html) {
  $("sheetBody").innerHTML = html;
  $("sheet").hidden = false; $("sheetBackdrop").hidden = false;
}
function closeSheet() { $("sheet").hidden = true; $("sheetBackdrop").hidden = true; }

function patientSheet() {
  openSheet(`<h2>Patient</h2>${patients().map((p, i) => `
    <button class="option ${i === state.patientIdx ? "on" : ""}" data-i="${i}"><div class="row-ico">${ico("user")}</div>
    <div class="row-main"><div class="row-title">Patient ${esc(p.id)}</div><div class="row-sub">${num(p.summary?.days, 0)} jours · ${p.summary?.n_events ?? "?"} épisodes · risque ${(LEVELS[p.current?.level]?.label || "—").toLowerCase()}</div></div>
    ${i === state.patientIdx ? `<span class="check">${ico("check")}</span>` : ""}</button>`).join("")}`);
  $("sheetBody").querySelectorAll(".option").forEach((b) => (b.onclick = () => {
    state.patientIdx = +b.dataset.i; store.setItem(LS_PATIENT, state.patientIdx); closeSheet(); renderAll();
  }));
}

function settingsSheet() {
  const d = state.doc || {}, theme = store.getItem(LS_THEME) || "auto";
  const gen = d.generated ? new Date(d.generated) : null;
  openSheet(`<h2>Réglages</h2>
    <div class="card" style="margin-bottom:12px"><div class="card-title" style="margin-bottom:10px">Données</div>
      <dl class="kv">
        <dt>Source</dt><dd>${esc(state.source)}</dd>
        <dt>Jeu de données</dt><dd>${esc(d.dataset?.name || "—")}</dd>
        <dt>Patients</dt><dd>${patients().length}</dd>
        <dt>Généré le</dt><dd>${gen && !isNaN(gen) ? `${fmtDate(gen)} · ${fmtTime(gen)}` : "—"}</dd>
        <dt>Branche 1</dt><dd>${b1() ? "chargée" : "absente"}</dd>
        <dt>Branche 2</dt><dd>${b2() ? "chargée" : "à venir"}</dd>
      </dl>
      <div style="margin-top:14px">
        <button class="btn primary" id="importBtn">${ico("upload")}Importer des résultats (.json)</button>
        ${store.getItem(LS_DOC) ? `<button class="btn ghost" id="resetBtn">${ico("reset")}Revenir au fichier intégré</button>` : ""}
      </div>
      <p class="fine" style="margin-top:10px">Un fichier de la branche 2 importé après celui de la branche 1 est fusionné avec lui.</p>
    </div>
    <div class="card" style="margin-bottom:12px"><div class="card-title" style="margin-bottom:10px">Apparence</div>
      <div class="seg" id="themeSeg" style="width:100%;display:grid;grid-template-columns:repeat(3,1fr)">
        <button data-t="auto" class="${theme === "auto" ? "on" : ""}">Auto</button><button data-t="light" class="${theme === "light" ? "on" : ""}">Clair</button><button data-t="dark" class="${theme === "dark" ? "on" : ""}">Sombre</button>
      </div>
    </div>
    <p class="fine">EpiCare — prévision du risque de crise (branche 1) à partir d'une montre Empatica E4 et de l'historique des crises. Données : My Seizure Gauge (Mayo Clinic, CC BY 4.0). Outil de recherche, pas un dispositif médical.</p>`);
  $("importBtn").onclick = () => $("fileInput").click();
  const rb = $("resetBtn"); if (rb) rb.onclick = async () => { store.removeItem(LS_DOC); state.doc = await loadData(); state.patientIdx = 0; closeSheet(); renderAll(); };
  $("themeSeg").querySelectorAll("button").forEach((b) => (b.onclick = () => { setTheme(b.dataset.t); settingsSheet(); }));
}

function setTheme(t) {
  store.setItem(LS_THEME, t);
  if (t === "auto") document.documentElement.removeAttribute("data-theme"); else document.documentElement.dataset.theme = t;
  const dark = t === "dark" || (t === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.querySelector('meta[name="theme-color"]').setAttribute("content", dark ? "#0a0e15" : "#0B2A4A");
  if (state.doc) RENDER[state.view]();
}

$("fileInput").addEventListener("change", async (e) => {
  const f = e.target.files[0]; if (!f) return;
  try {
    const doc = JSON.parse(await f.text());
    const isB1 = !!doc.branches?.branch1;
    const merged = isB1 ? mergeDocs(doc, state.doc?.branches?.branch2 ? { branches: { branch2: state.doc.branches.branch2 } } : null) : mergeDocs(state.doc, doc);
    if (!merged?.branches?.branch1 && !merged?.branches?.branch2) throw new Error("schéma inconnu");
    state.doc = merged; state.source = "Fichier importé"; state.patientIdx = 0;
    try { store.setItem(LS_DOC, JSON.stringify(merged)); } catch { /* trop gros : gardé pour la session */ }
    closeSheet(); renderAll();
  } catch (err) { alert(`Fichier non reconnu : ${err.message}`); }
  e.target.value = "";
});

/* ============================================================ démarrage */
async function boot() {
  hydrateIcons();
  setTheme(store.getItem(LS_THEME) || "auto");
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => setTheme(store.getItem(LS_THEME) || "auto"));
  $("view-home").innerHTML = `<div class="loading"><div class="spinner"></div>Chargement des résultats…</div>`;
  document.querySelectorAll(".tab").forEach((t) => (t.onclick = () => show(t.dataset.view)));
  $("patientBtn").onclick = patientSheet;
  $("settingsBtn").onclick = settingsSheet;
  $("sheetBackdrop").onclick = closeSheet;
  document.addEventListener("scroll", hideTip, { passive: true });
  let rt; window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => state.doc && RENDER[state.view](), 150); });
  state.doc = await loadData();
  state.patientIdx = Math.min(+(store.getItem(LS_PATIENT) || 0), Math.max(0, patients().length - 1));
  state.view = RENDER[location.hash.slice(1)] ? location.hash.slice(1) : "home";
  window.addEventListener("popstate", () => show(location.hash.slice(1) || "home", false));
  show(state.view, false);
  renderAll();
  if ("serviceWorker" in navigator && /^https?:$/.test(location.protocol) && !window.EPICARE_NATIVE) navigator.serviceWorker.register("sw.js").catch(() => {});
}
boot();
