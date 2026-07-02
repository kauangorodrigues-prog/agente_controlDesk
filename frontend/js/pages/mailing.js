// ── Página: Mailing Scoring ────────────────────────────────────────
import { Api } from "../api.js";
import { kpi, badge, empty, skeletonKpis, fmt, escapeHtml, table, toast, downloadCsv } from "../ui.js";
import { icon } from "../icons.js";
import { barChart } from "../charts.js";

export const meta = { title: "Mailing", subtitle: "Priorização inteligente de discagem por score", icon: "layers" };

export async function mount(root) {
  let limite = 100;
  let cache = [];

  root.innerHTML = `
    <div class="page-head">
      <div class="actions">
        <select class="select" id="ml-n" style="width:auto">
          <option value="50">Top 50</option>
          <option value="100" selected>Top 100</option>
          <option value="250">Top 250</option>
          <option value="500">Top 500</option>
        </select>
        <button class="btn" id="ml-csv">${icon("download")} Exportar CSV</button>
        <button class="btn btn-primary" id="ml-proc">${icon("spark")} Recalcular Score</button>
      </div>
    </div>
    <div class="grid kpi-grid" id="ml-kpis">${skeletonKpis(4)}</div>
    <div class="grid grid-2" style="margin-top:18px">
      <div class="card col-2"><div class="card-head">${icon("chart")}<h3>Distribuição de Score</h3><span class="spacer"></span><span class="sub">faixas de 0–100</span></div><div class="card-body" id="ml-dist" style="min-height:200px"></div></div>
    </div>
    <div class="card" style="margin-top:18px">
      <div class="card-head">${icon("list")}<h3>Ranking de Contatos</h3></div>
      <div class="card-body pad-0" id="ml-table"></div>
    </div>`;

  root.querySelector("#ml-n").addEventListener("change", (e) => { limite = +e.target.value; load(); });
  root.querySelector("#ml-csv").addEventListener("click", () => {
    if (!cache.length) { toast("Nada para exportar", "warn"); return; }
    downloadCsv(`mailing_priorizado_${new Date().toISOString().slice(0, 10)}.csv`, cache, [
      { label: "CPF", key: "cpf" }, { label: "Telefone", key: "telefone" },
      { label: "Nome", key: "nome" }, { label: "Campanha", key: "campanha" },
      { label: "DDD", key: "ddd" }, { label: "Atraso (dias)", key: "days_delay" },
      { label: "Score", key: "score_discagem" },
    ]);
    toast("CSV exportado", "success");
  });
  root.querySelector("#ml-proc").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true; btn.innerHTML = `<span class="spinner dark"></span> Processando…`;
    try {
      const res = await Api.mailingProcessar();
      toast(`Score recalculado — ${fmt.int(res.registros)} registros`, "success");
      await load();
    } catch (err) { toast(err.message || "Falha ao processar", "error"); }
    finally { btn.disabled = false; btn.innerHTML = `${icon("spark")} Recalcular Score`; }
  });

  async function load() {
    const rows = await Api.mailingTop(limite).catch(() => []);
    cache = rows;
    renderKpis(rows);
    renderDist(rows);
    renderTable(rows);
  }

  function renderKpis(rows) {
    const box = root.querySelector("#ml-kpis");
    if (!rows.length) { box.innerHTML = empty("Sem mailing pontuado", "Execute 'Recalcular Score'"); return; }
    const media = rows.reduce((s, r) => s + r.score_discagem, 0) / rows.length;
    const altos = rows.filter((r) => r.score_discagem >= 70).length;
    const quebradas = rows.filter((r) => r.promessa_quebrada).length;
    box.innerHTML = [
      kpi({ label: "Registros", value: fmt.int(rows.length), icon: "layers", tone: "orange" }),
      kpi({ label: "Score Médio", value: fmt.num(media), icon: "spark", tone: "blue" }),
      kpi({ label: "Alta Prioridade", value: fmt.int(altos), icon: "trending", tone: "green", delta: "score ≥ 70", deltaDir: "up" }),
      kpi({ label: "Promessas Quebradas", value: fmt.int(quebradas), icon: "alert-triangle", tone: quebradas ? "yellow" : "green" }),
    ].join("");
  }

  function renderDist(rows) {
    const box = root.querySelector("#ml-dist");
    if (!rows.length) { box.innerHTML = empty("Sem dados"); return; }
    const faixas = [
      { label: "0–20", min: 0, max: 20, color: "#F43F5E" },
      { label: "20–40", min: 20, max: 40, color: "#F5A623" },
      { label: "40–60", min: 40, max: 60, color: "#FFB84D" },
      { label: "60–80", min: 60, max: 80, color: "#FF8A2B" },
      { label: "80–100", min: 80, max: 101, color: "#FF6B00" },
    ];
    const data = faixas.map((f) => ({ label: f.label, value: rows.filter((r) => r.score_discagem >= f.min && r.score_discagem < f.max).length, color: f.color }));
    barChart(box, data, { height: 200, valueFmt: (v) => fmt.int(v) });
  }

  function renderTable(rows) {
    const box = root.querySelector("#ml-table");
    box.innerHTML = table([
      { key: "rank", label: "#", render: (r, i) => "" }, // placeholder replaced below
      { key: "nome", label: "Nome", render: (r) => `<span class="strong">${escapeHtml(r.nome || "—")}</span>` },
      { key: "cpf", label: "CPF", render: (r) => `<span class="mono text-dim">${escapeHtml(r.cpf)}</span>` },
      { key: "telefone", label: "Telefone", render: (r) => `<span class="mono">${escapeHtml(r.telefone)}</span>` },
      { key: "campanha", label: "Campanha", render: (r) => escapeHtml(r.campanha || r.campanha_id || "—") },
      { key: "days_delay", label: "Atraso", num: true, render: (r) => `${fmt.int(r.days_delay)}d` },
      { key: "promessa_quebrada", label: "PQ", render: (r) => r.promessa_quebrada ? badge("quebrada", "red") : `<span class="text-faint">—</span>` },
      { key: "score_discagem", label: "Score", num: true, render: (r) => scoreBadge(r.score_discagem) },
    ].filter((c) => c.key !== "rank"), rows.slice(0, 200), { emptyMsg: "Nenhum contato pontuado." });
  }

  function scoreBadge(s) {
    const c = s >= 70 ? "green" : s >= 40 ? "yellow" : "red";
    return badge(fmt.num(s), c);
  }

  await load();
  return { onRefresh: load };
}
