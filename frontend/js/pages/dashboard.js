// ── Página: Visão em Tempo Real ────────────────────────────────────
import { Api } from "../api.js";
import { kpi, badge, empty, skeletonKpis, progress, fmt, escapeHtml, table } from "../ui.js";
import { icon } from "../icons.js";
import { barChart, donut, riskColor, goodColor } from "../charts.js";

export const meta = { title: "Tempo Real", subtitle: "Monitoramento operacional ao vivo", icon: "dashboard" };

export async function mount(root) {
  root.innerHTML = `
    <div class="grid kpi-grid" id="dash-kpis">${skeletonKpis(5)}</div>
    <div class="grid grid-2" style="margin-top:18px">
      <div class="card">
        <div class="card-head">${icon("users")}<h3>Distribuição de Agentes</h3></div>
        <div class="card-body row gap-lg" id="dash-donut" style="justify-content:center;min-height:200px"></div>
      </div>
      <div class="card">
        <div class="card-head">${icon("target")}<h3>Ocupação por Campanha</h3></div>
        <div class="card-body" id="dash-camp" style="min-height:200px"></div>
      </div>
    </div>
    <div class="grid grid-2" style="margin-top:18px">
      <div class="card">
        <div class="card-head">${icon("inbox")}<h3>Mailing Restante</h3><span class="spacer"></span><span class="sub">por campanha</span></div>
        <div class="card-body" id="dash-mailing"></div>
      </div>
      <div class="card">
        <div class="card-head">${icon("bell")}<h3>Alertas Recentes</h3></div>
        <div class="card-body" id="dash-alerts" style="max-height:340px;overflow-y:auto"></div>
      </div>
    </div>`;

  async function load() {
    const [ocup, camps, alerts, mailing] = await Promise.all([
      Api.ocupacao().catch(() => null),
      Api.ocupacaoCampanhas().catch(() => []),
      Api.alertas(8).catch(() => []),
      Api.campanhasDesempenho().catch(() => []),
    ]);
    renderKpis(ocup);
    renderDonut(ocup);
    renderCampBar(camps);
    renderMailing(mailing);
    renderAlerts(alerts);
  }

  function renderKpis(o) {
    const box = root.querySelector("#dash-kpis");
    if (!o || o.erro) { box.innerHTML = empty(o?.erro || "Sem agentes logados", "Verifique a conexão com o discador"); return; }
    const ocioDir = o.ociosidade_pct > 15 ? "down" : "up";
    box.innerHTML = [
      kpi({ label: "Agentes Logados", value: fmt.int(o.total), icon: "users", tone: "orange" }),
      kpi({ label: "Em Ligação", value: fmt.int(o.em_ligacao), icon: "phone", tone: "green" }),
      kpi({ label: "Disponíveis", value: fmt.int(o.ociosos), icon: "activity", tone: "blue", delta: `${fmt.pct(o.ociosidade_pct)} ociosidade`, deltaDir: ocioDir }),
      kpi({ label: "Em Pausa", value: fmt.int(o.em_pausa), icon: "pause", tone: o.agentes_pausa_longa?.length ? "yellow" : "orange", delta: o.agentes_pausa_longa?.length ? `${o.agentes_pausa_longa.length} pausa longa` : "dentro do limite", deltaDir: o.agentes_pausa_longa?.length ? "down" : "flat" }),
      kpi({ label: "Ocupação", value: fmt.pct(o.ocupacao_pct, 1), icon: "gauge", tone: "orange" }),
    ].join("");
  }

  function renderDonut(o) {
    const box = root.querySelector("#dash-donut");
    if (!o || !o.total) { box.innerHTML = empty("Sem dados de ocupação"); return; }
    box.innerHTML = `<div id="dnt"></div>
      <div class="chart-legend" style="flex-direction:column;gap:10px">
        <span><i style="background:#22C55E"></i> Em ligação · <b class="text-soft">${o.em_ligacao}</b></span>
        <span><i style="background:#3B9EFF"></i> Disponíveis · <b class="text-soft">${o.ociosos}</b></span>
        <span><i style="background:#F5A623"></i> Em pausa · <b class="text-soft">${o.em_pausa}</b></span>
      </div>`;
    donut(box.querySelector("#dnt"), [
      { label: "Em ligação", value: o.em_ligacao, color: "#22C55E" },
      { label: "Disponíveis", value: o.ociosos, color: "#3B9EFF" },
      { label: "Em pausa", value: o.em_pausa, color: "#F5A623" },
    ], { size: 160, thickness: 20, centerTop: fmt.pct(o.ocupacao_pct, 0), centerSub: "ocupação" });
  }

  function renderCampBar(camps) {
    const box = root.querySelector("#dash-camp");
    if (!camps || !camps.length) { box.innerHTML = empty("Sem campanhas ativas"); return; }
    barChart(box, camps.map((c) => ({ label: c.campanha, value: c.ocupacao_pct })),
      { height: 210, valueFmt: (v) => v.toFixed(0) + "%", colorScale: (v) => goodColor(v) });
  }

  function renderMailing(mailing) {
    const box = root.querySelector("#dash-mailing");
    if (!mailing || !mailing.length) { box.innerHTML = empty("Sem dados de mailing"); return; }
    box.innerHTML = mailing.map((c) => {
      const p = c.mailing_restante;
      return `<div class="progress-row">
        <div class="lbl"><span>${escapeHtml(c.campanha)} ${c.status === "PAUSED" ? badge("pausada", "gray") : ""}</span><b class="${p < 8 ? "text-danger" : p < 20 ? "text-warn" : "text-soft"}">${fmt.pct(p)}</b></div>
        ${progress(p)}
      </div>`;
    }).join("");
  }

  function renderAlerts(alerts) {
    const box = root.querySelector("#dash-alerts");
    if (!alerts || !alerts.length) { box.innerHTML = empty("Nenhum alerta recente", "", "check"); return; }
    const ic = { CRITICO: ["alert-octagon", "red"], ATENCAO: ["alert-triangle", "yellow"], INFO: ["info", "blue"] };
    box.innerHTML = alerts.map((a) => {
      const [i, tone] = ic[a.nivel] || ["info", "gray"];
      const msg = escapeHtml(a.mensagem).replace(/\*([^*]+)\*/g, "<strong>$1</strong>");
      return `<div class="alert-item">
        <div class="ai-icon" style="background:var(--${tone === "red" ? "danger" : tone === "yellow" ? "warn" : "info"}-dim);color:var(--${tone === "red" ? "danger" : tone === "yellow" ? "warn" : "info"})">${icon(i)}</div>
        <div class="ai-body"><div class="ai-msg">${msg}</div><div class="ai-time">${fmt.horaS(a.ts)} · ${fmt.rel(a.ts)}</div></div>
      </div>`;
    }).join("");
  }

  await load();
  return { onRefresh: load };
}
