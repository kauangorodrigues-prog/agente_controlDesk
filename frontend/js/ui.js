// ══════════════════════════════════════════════════════════════════
// Helpers de UI — toasts, formatação, KPIs, tabelas, estados vazios
// ══════════════════════════════════════════════════════════════════
import { icon } from "./icons.js";

// ---------- DOM ----------
export const $  = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
export function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}
export function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- Formatação ----------
export const fmt = {
  int:   (n) => (n == null || isNaN(n)) ? "—" : Math.round(+n).toLocaleString("pt-BR"),
  num:   (n, d = 1) => (n == null || isNaN(n)) ? "—" : (+n).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }),
  pct:   (n, d = 1) => (n == null || isNaN(n)) ? "—" : `${(+n).toFixed(d)}%`,
  hora:  (iso) => { try { return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }); } catch { return "—"; } },
  horaS: (iso) => { try { return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }); } catch { return "—"; } },
  data:  (iso) => { try { return new Date(iso).toLocaleDateString("pt-BR"); } catch { return "—"; } },
  dataHora: (iso) => { try { const d = new Date(iso); return `${d.toLocaleDateString("pt-BR")} ${d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`; } catch { return "—"; } },
  rel:   (iso) => {
    try {
      const diff = (Date.now() - new Date(iso).getTime()) / 1000;
      if (diff < 60) return "agora";
      if (diff < 3600) return `há ${Math.floor(diff / 60)} min`;
      if (diff < 86400) return `há ${Math.floor(diff / 3600)}h`;
      return `há ${Math.floor(diff / 86400)}d`;
    } catch { return "—"; }
  },
};

// ---------- Toasts ----------
let toastWrap;
export function toast(msg, type = "info", ms = 3800) {
  if (!toastWrap) {
    toastWrap = el(`<div class="toast-wrap"></div>`);
    document.body.appendChild(toastWrap);
  }
  const ic = { success: "check", error: "x", warn: "alert-triangle", info: "info" }[type] || "info";
  const t = el(`<div class="toast ${type}">${icon(ic)}<span>${escapeHtml(msg)}</span></div>`);
  toastWrap.appendChild(t);
  setTimeout(() => {
    t.classList.add("out");
    setTimeout(() => t.remove(), 300);
  }, ms);
}

// ---------- KPI card ----------
export function kpi({ label, value, unit = "", icon: ic = "activity", tone = "orange", delta, deltaDir }) {
  const deltaHtml = delta != null
    ? `<div class="kpi-delta ${deltaDir || "flat"}">${delta}</div>` : "";
  const unitHtml = unit ? `<small>${unit}</small>` : "";
  return `<div class="kpi">
    <div class="kpi-top">
      <span class="kpi-label">${escapeHtml(label)}</span>
      <span class="kpi-icon ${tone}">${icon(ic)}</span>
    </div>
    <div class="kpi-value">${value}${unitHtml}</div>
    ${deltaHtml}
  </div>`;
}

// ---------- Badge ----------
export function badge(text, color = "gray", dot = false) {
  return `<span class="badge ${color}">${dot ? '<span class="dot"></span>' : ""}${escapeHtml(text)}</span>`;
}

// ---------- Estado vazio ----------
export function empty(msg, hint = "", ic = "inbox") {
  return `<div class="empty">${icon(ic)}<p>${escapeHtml(msg)}</p>${hint ? `<div class="hint">${escapeHtml(hint)}</div>` : ""}</div>`;
}

// ---------- Skeleton ----------
export function skeletonKpis(n = 4) {
  return `<div class="grid kpi-grid">${Array(n).fill('<div class="skel skel-kpi"></div>').join("")}</div>`;
}
export function skeletonLines(n = 5) {
  return Array(n).fill('<div class="skel skel-line"></div>').join("");
}

// ---------- Progress ----------
export function progress(pct, tone) {
  const t = tone || (pct < 8 ? "red" : pct < 20 ? "yellow" : "green");
  return `<div class="progress"><div class="fill ${t}" style="width:${Math.max(0, Math.min(100, pct))}%"></div></div>`;
}

// ---------- Tabela genérica ----------
// cols: [{ key, label, num, render, cls }]
export function table(cols, rows, { emptyMsg = "Nenhum registro." } = {}) {
  if (!rows || rows.length === 0) return empty(emptyMsg);
  const head = cols.map((c) => `<th class="${c.num ? "num" : ""}">${escapeHtml(c.label)}</th>`).join("");
  const body = rows.map((row) => {
    const tds = cols.map((c) => {
      const val = c.render ? c.render(row) : escapeHtml(row[c.key]);
      return `<td class="${c.num ? "num" : ""} ${c.cls || ""}">${val}</td>`;
    }).join("");
    return `<tr>${tds}</tr>`;
  }).join("");
  return `<div class="table-wrap"><table class="data"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

// ---------- Modal ----------
export function modal({ title, bodyHtml, footHtml }) {
  const backdrop = el(`<div class="modal-backdrop">
    <div class="modal" role="dialog" aria-modal="true">
      <div class="modal-head"><h3>${escapeHtml(title)}</h3><button class="btn btn-ghost btn-icon" data-close>${icon("x")}</button></div>
      <div class="modal-body">${bodyHtml}</div>
      ${footHtml ? `<div class="modal-foot">${footHtml}</div>` : ""}
    </div></div>`);
  const close = () => backdrop.remove();
  backdrop.addEventListener("click", (e) => { if (e.target === backdrop) close(); });
  backdrop.querySelector("[data-close]").addEventListener("click", close);
  document.addEventListener("keydown", function esc(e) { if (e.key === "Escape") { close(); document.removeEventListener("keydown", esc); } });
  document.body.appendChild(backdrop);
  return { el: backdrop, close };
}

// ---------- Download CSV ----------
export function downloadCsv(filename, rows, cols) {
  const header = cols.map((c) => `"${c.label}"`).join(",");
  const lines = rows.map((row) =>
    cols.map((c) => {
      const v = c.raw ? c.raw(row) : row[c.key];
      return `"${String(v ?? "").replace(/"/g, '""')}"`;
    }).join(",")
  );
  const csv = [header, ...lines].join("\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export function nivelColor(nivel) {
  return { CRITICO: "red", ATENCAO: "yellow", INFO: "blue" }[nivel] || "gray";
}
