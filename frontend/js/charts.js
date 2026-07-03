// ══════════════════════════════════════════════════════════════════
// Charts SVG próprios — line (com banda), bar, donut/gauge.
// Sem dependências externas. Responsivos via viewBox.
// ══════════════════════════════════════════════════════════════════
import { escapeHtml } from "./ui.js";

const ORANGE = "#FF6B00";
const ORANGE_BRIGHT = "#FF8A2B";

let _tt;
function tooltip() {
  if (!_tt) {
    _tt = document.createElement("div");
    _tt.className = "chart-tooltip";
    document.body.appendChild(_tt);
  }
  return _tt;
}
function showTip(x, y, html) {
  const t = tooltip();
  t.innerHTML = html;
  t.style.opacity = "1";
  t.style.left = Math.min(window.innerWidth - 180, x + 14) + "px";
  t.style.top = (y - 10) + "px";
}
function hideTip() { if (_tt) _tt.style.opacity = "0"; }

const uid = () => "c" + Math.random().toString(36).slice(2, 8);

// ---------- Line chart (com banda de confiança opcional) ----------
// data: [{ label, y, lower, upper }]  — lower/upper opcionais
export function lineChart(container, data, opts = {}) {
  const {
    height = 240, yLabel = "", band = false,
    color = ORANGE, valueFmt = (v) => Math.round(v).toLocaleString("pt-BR"),
  } = opts;
  if (!data || data.length === 0) { container.innerHTML = ""; return; }

  const W = 800, H = height;
  const padL = 46, padR = 18, padT = 16, padB = 34;
  const iw = W - padL - padR, ih = H - padT - padB;

  const ys = data.map((d) => d.y);
  const los = band ? data.map((d) => d.lower ?? d.y) : ys;
  const his = band ? data.map((d) => d.upper ?? d.y) : ys;
  let min = Math.min(...los), max = Math.max(...his);
  if (min === max) { max = min + 1; }
  min = Math.min(min, 0); // baseline em 0 quando faz sentido
  const pad = (max - min) * 0.08; max += pad;

  const X = (i) => padL + (data.length === 1 ? iw / 2 : (i / (data.length - 1)) * iw);
  const Y = (v) => padT + ih - ((v - min) / (max - min)) * ih;

  // grid + eixo Y (5 ticks)
  let grid = "", yticks = "";
  for (let i = 0; i <= 4; i++) {
    const v = min + (i / 4) * (max - min);
    const yy = Y(v);
    grid += `<line class="grid-line" x1="${padL}" y1="${yy}" x2="${W - padR}" y2="${yy}"/>`;
    yticks += `<text class="axis-label" x="${padL - 8}" y="${yy + 3}" text-anchor="end">${valueFmt(v)}</text>`;
  }
  // eixo X labels (até 8)
  let xticks = "";
  const step = Math.ceil(data.length / 8);
  data.forEach((d, i) => {
    if (i % step === 0 || i === data.length - 1) {
      xticks += `<text class="axis-label" x="${X(i)}" y="${H - 12}" text-anchor="middle">${escapeHtml(d.label)}</text>`;
    }
  });

  const gid = uid();
  const linePath = data.map((d, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(d.y).toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L${X(data.length - 1)} ${padT + ih} L${X(0)} ${padT + ih} Z`;

  let bandPath = "";
  if (band) {
    const up = data.map((d, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(d.upper ?? d.y).toFixed(1)}`).join(" ");
    const lo = data.map((d, i) => `L${X(data.length - 1 - i).toFixed(1)} ${Y(data[data.length - 1 - i].lower ?? data[data.length - 1 - i].y).toFixed(1)}`).join(" ");
    bandPath = `<path d="${up} ${lo} Z" fill="${color}" opacity="0.10"/>`;
  }

  const dots = data.map((d, i) =>
    `<circle cx="${X(i).toFixed(1)}" cy="${Y(d.y).toFixed(1)}" r="3.2" fill="${color}" stroke="#0A0A0C" stroke-width="1.5"
      data-i="${i}" class="cdot"/>`).join("");

  container.innerHTML = `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="height:${H}px">
    <defs>
      <linearGradient id="area-${gid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${color}" stop-opacity="0.30"/>
        <stop offset="1" stop-color="${color}" stop-opacity="0"/>
      </linearGradient>
    </defs>
    ${grid}${yticks}${xticks}
    ${bandPath}
    <path d="${areaPath}" fill="url(#area-${gid})"/>
    <path d="${linePath}" fill="none" stroke="${color}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>
    ${dots}
  </svg>`;

  const svg = container.querySelector("svg");
  svg.querySelectorAll(".cdot").forEach((c) => {
    c.addEventListener("mouseenter", (e) => {
      c.setAttribute("r", "5");
      const d = data[+c.dataset.i];
      const extra = band ? `<br><span style="color:#8A8A96">faixa:</span> ${valueFmt(d.lower)}–${valueFmt(d.upper)}` : "";
      showTip(e.clientX, e.clientY, `<b>${escapeHtml(d.label)}</b><br>${yLabel ? yLabel + ": " : ""}${valueFmt(d.y)}${extra}`);
    });
    c.addEventListener("mouseleave", () => { c.setAttribute("r", "3.2"); hideTip(); });
  });
}

// ---------- Bar chart ----------
// data: [{ label, value, color? }]
export function barChart(container, data, opts = {}) {
  const { height = 260, valueFmt = (v) => (+v).toLocaleString("pt-BR"), horizontal = false, colorScale } = opts;
  if (!data || data.length === 0) { container.innerHTML = ""; return; }

  const W = 800, H = height;
  const max = Math.max(...data.map((d) => d.value), 1);

  if (horizontal) {
    const rowH = 34, padL = 4, padR = 60, gap = 10;
    const barArea = W - 200;
    const bars = data.map((d, i) => {
      const y = i * (rowH + gap) + 6;
      const w = (d.value / max) * barArea;
      const col = d.color || colorScale?.(d.value, max) || ORANGE;
      return `<text class="axis-label" x="0" y="${y + rowH / 2 + 4}" style="font-size:12px;fill:#C4C4CE">${escapeHtml(d.label)}</text>
        <rect x="180" y="${y}" width="${w.toFixed(1)}" height="${rowH}" rx="6" fill="${col}" class="cbar" data-i="${i}"/>
        <text class="axis-label" x="${185 + w}" y="${y + rowH / 2 + 4}" style="fill:#F4F4F6">${valueFmt(d.value)}</text>`;
    }).join("");
    const totalH = data.length * (rowH + gap) + 12;
    container.innerHTML = `<svg class="chart" viewBox="0 0 ${W} ${totalH}" preserveAspectRatio="xMinYMin meet" style="height:${totalH}px">${bars}</svg>`;
  } else {
    const padL = 46, padR = 14, padT = 14, padB = 46;
    const iw = W - padL - padR, ih = H - padT - padB;
    const bw = (iw / data.length) * 0.62;
    const gap = (iw / data.length);

    let grid = "", yticks = "";
    for (let i = 0; i <= 4; i++) {
      const v = (i / 4) * max, yy = padT + ih - (v / max) * ih;
      grid += `<line class="grid-line" x1="${padL}" y1="${yy}" x2="${W - padR}" y2="${yy}"/>`;
      yticks += `<text class="axis-label" x="${padL - 8}" y="${yy + 3}" text-anchor="end">${valueFmt(v)}</text>`;
    }
    const bars = data.map((d, i) => {
      const x = padL + i * gap + (gap - bw) / 2;
      const h = (d.value / max) * ih;
      const y = padT + ih - h;
      const col = d.color || colorScale?.(d.value, max) || ORANGE;
      const label = d.label.length > 12 ? d.label.slice(0, 11) + "…" : d.label;
      return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(h, 0).toFixed(1)}" rx="5"
          fill="${col}" class="cbar" data-i="${i}"/>
        <text class="axis-label" x="${(x + bw / 2).toFixed(1)}" y="${H - 26}" text-anchor="middle">${escapeHtml(label)}</text>`;
    }).join("");
    container.innerHTML = `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="height:${H}px">${grid}${yticks}${bars}</svg>`;
  }

  container.querySelectorAll(".cbar").forEach((b) => {
    const d = data[+b.dataset.i];
    b.style.transition = "opacity .15s";
    b.addEventListener("mouseenter", (e) => { b.style.opacity = "0.8"; showTip(e.clientX, e.clientY, `<b>${escapeHtml(d.label)}</b><br>${valueFmt(d.value)}`); });
    b.addEventListener("mousemove", (e) => showTip(e.clientX, e.clientY, `<b>${escapeHtml(d.label)}</b><br>${valueFmt(d.value)}`));
    b.addEventListener("mouseleave", () => { b.style.opacity = "1"; hideTip(); });
  });
}

// ---------- Donut / gauge ----------
// segments: [{ label, value, color }]
export function donut(container, segments, opts = {}) {
  const { size = 150, thickness = 18, centerTop = "", centerSub = "" } = opts;
  const total = segments.reduce((s, d) => s + d.value, 0) || 1;
  const r = (size - thickness) / 2;
  const cx = size / 2, cy = size / 2;
  const circ = 2 * Math.PI * r;
  let offset = 0;
  const rings = segments.map((s) => {
    const frac = s.value / total;
    const len = frac * circ;
    const dash = `${len} ${circ - len}`;
    const ring = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${s.color}" stroke-width="${thickness}"
      stroke-dasharray="${dash}" stroke-dashoffset="${-offset}" transform="rotate(-90 ${cx} ${cy})" stroke-linecap="butt"/>`;
    offset += len;
    return ring;
  }).join("");

  container.innerHTML = `<div class="gauge" style="width:${size}px;height:${size}px">
    <svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#26262F" stroke-width="${thickness}"/>
      ${rings}
    </svg>
    <div class="val"><b>${centerTop}</b>${centerSub ? `<span>${centerSub}</span>` : ""}</div>
  </div>`;
}

// escala de cor verde→amarelo→vermelho (para métricas "quanto menor melhor")
export function riskColor(pct) {
  if (pct < 8)  return "#22C55E";
  if (pct < 15) return "#F5A623";
  return "#F43F5E";
}
// escala inversa (quanto maior melhor)
export function goodColor(pct) {
  if (pct >= 85) return "#22C55E";
  if (pct >= 65) return "#F5A623";
  return "#F43F5E";
}
