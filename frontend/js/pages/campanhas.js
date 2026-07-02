// ── Página: Campanhas ──────────────────────────────────────────────
import { Api } from "../api.js";
import { kpi, badge, empty, skeletonKpis, fmt, escapeHtml, table, progress } from "../ui.js";
import { icon } from "../icons.js";
import { barChart, riskColor } from "../charts.js";

export const meta = { title: "Campanhas", subtitle: "Desempenho consolidado do dia", icon: "target" };

export async function mount(root) {
  root.innerHTML = `
    <div class="grid kpi-grid" id="cmp-kpis">${skeletonKpis(4)}</div>
    <div class="grid grid-2" style="margin-top:18px">
      <div class="card"><div class="card-head">${icon("phone")}<h3>Acionamentos por Campanha</h3></div><div class="card-body" id="cmp-bar1" style="min-height:220px"></div></div>
      <div class="card"><div class="card-head">${icon("alert-triangle")}<h3>Abandono por Campanha (%)</h3></div><div class="card-body" id="cmp-bar2" style="min-height:220px"></div></div>
    </div>
    <div class="card" style="margin-top:18px">
      <div class="card-head">${icon("list")}<h3>Detalhamento</h3></div>
      <div class="card-body pad-0" id="cmp-table">${empty("Carregando…", "", "layers")}</div>
    </div>`;

  async function load() {
    const rows = await Api.campanhasDesempenho().catch(() => []);
    renderKpis(rows);
    renderCharts(rows);
    renderTable(rows);
  }

  function renderKpis(rows) {
    const box = root.querySelector("#cmp-kpis");
    if (!rows.length) { box.innerHTML = empty("Sem dados de campanhas hoje"); return; }
    const totalAcion = rows.reduce((s, r) => s + r.acionamentos, 0);
    const totalCpc = rows.reduce((s, r) => s + r.cpcs, 0);
    const taxaCpc = totalAcion ? (totalCpc / totalAcion) * 100 : 0;
    const ativas = rows.filter((r) => r.status === "ACTIVE").length;
    const abandonoMed = rows.reduce((s, r) => s + r.abandono, 0) / rows.length;
    box.innerHTML = [
      kpi({ label: "Campanhas Ativas", value: `${ativas}`, unit: `/ ${rows.length}`, icon: "target", tone: "orange" }),
      kpi({ label: "Acionamentos", value: fmt.int(totalAcion), icon: "phone", tone: "blue" }),
      kpi({ label: "CPCs", value: fmt.int(totalCpc), icon: "check", tone: "green", delta: `${fmt.pct(taxaCpc)} de conversão`, deltaDir: "up" }),
      kpi({ label: "Abandono Médio", value: fmt.pct(abandonoMed), icon: "alert-triangle", tone: abandonoMed > 8 ? "red" : "yellow", delta: `limite 8.0%`, deltaDir: abandonoMed > 8 ? "down" : "flat" }),
    ].join("");
  }

  function renderCharts(rows) {
    if (!rows.length) return;
    barChart(root.querySelector("#cmp-bar1"), rows.map((r) => ({ label: r.campanha, value: r.acionamentos })), { height: 220 });
    barChart(root.querySelector("#cmp-bar2"), rows.map((r) => ({ label: r.campanha, value: r.abandono })),
      { height: 220, valueFmt: (v) => v.toFixed(1) + "%", colorScale: (v) => riskColor(v) });
  }

  function renderTable(rows) {
    const box = root.querySelector("#cmp-table");
    box.innerHTML = table([
      { key: "campanha", label: "Campanha", render: (r) => `<span class="strong">${escapeHtml(r.campanha)}</span>` },
      { key: "status", label: "Status", render: (r) => r.status === "ACTIVE" ? badge("Ativa", "green", true) : badge("Pausada", "gray", true) },
      { key: "agentes", label: "Agentes", num: true, render: (r) => fmt.int(r.agentes) },
      { key: "acionamentos", label: "Acionam.", num: true, render: (r) => fmt.int(r.acionamentos) },
      { key: "cpcs", label: "CPCs", num: true, render: (r) => fmt.int(r.cpcs) },
      { key: "cpc_pct", label: "Conv.", num: true, render: (r) => fmt.pct(r.cpc_pct) },
      { key: "abandono", label: "Abandono", num: true, render: (r) => `<span class="${r.abandono > 8 ? "text-danger" : ""}">${fmt.pct(r.abandono)}</span>` },
      { key: "pacing_medio", label: "Pacing", num: true, render: (r) => fmt.num(r.pacing_medio) },
      { key: "mailing_restante", label: "Mailing", render: (r) => `<div style="min-width:120px">${progress(r.mailing_restante)}<span class="text-dim" style="font-size:11px">${fmt.pct(r.mailing_restante)}</span></div>` },
    ], rows, { emptyMsg: "Sem campanhas registradas hoje." });
  }

  await load();
  return { onRefresh: load };
}
