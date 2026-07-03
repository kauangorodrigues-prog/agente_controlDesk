// ── Página: Auditoria operacional ──────────────────────────────────
import { Api } from "../api.js";
import { kpi, badge, empty, skeletonKpis, fmt, escapeHtml, table, toast } from "../ui.js";
import { icon } from "../icons.js";

export const meta = { title: "Auditoria", subtitle: "Detecção contínua de anomalias operacionais", icon: "shield" };

export async function mount(root) {
  root.innerHTML = `
    <div class="page-head">
      <div class="actions"><button class="btn btn-primary" id="au-run">${icon("shield")} Executar Auditoria</button></div>
    </div>
    <div class="grid kpi-grid" id="au-kpis">${skeletonKpis(3)}</div>
    <div class="card" style="margin-top:18px">
      <div class="card-head">${icon("users")}<h3>Agentes sem Produção</h3><span class="spacer"></span><span class="sub">logados > 30 min · 0 ligações</span></div>
      <div class="card-body pad-0" id="au-imp"></div>
    </div>`;

  root.querySelector("#au-run").addEventListener("click", async (e) => {
    const btn = e.currentTarget; btn.disabled = true; btn.innerHTML = `<span class="spinner dark"></span> Auditando…`;
    try { const r = await Api.auditoria(); renderKpis(r); toast("Auditoria concluída", "success"); await loadImp(); }
    catch (err) { toast(err.message || "Falha na auditoria", "error"); }
    finally { btn.disabled = false; btn.innerHTML = `${icon("shield")} Executar Auditoria`; }
  });

  function renderKpis(r) {
    const box = root.querySelector("#au-kpis");
    if (!r) { box.innerHTML = empty("Execute a auditoria"); return; }
    const tone = (v) => v > 0 ? "red" : "green";
    box.innerHTML = [
      kpi({ label: "Agentes Improdutivos", value: fmt.int(r.agentes_improdutivos), icon: "users", tone: tone(r.agentes_improdutivos) }),
      kpi({ label: "Campanhas Paradas", value: fmt.int(r.campanhas_paradas), icon: "pause", tone: tone(r.campanhas_paradas) }),
      kpi({ label: "Mailing Crítico", value: fmt.int(r.mailing_critico), icon: "alert-octagon", tone: tone(r.mailing_critico), delta: "< 5% restante", deltaDir: r.mailing_critico ? "down" : "flat" }),
    ].join("");
  }

  async function loadImp() {
    const box = root.querySelector("#au-imp");
    const rows = await Api.agentesImprodutivos().catch(() => []);
    if (!rows.length) { box.innerHTML = empty("Nenhum agente improdutivo", "Toda a equipe está produzindo", "check"); return; }
    box.innerHTML = table([
      { key: "nome", label: "Agente", render: (r) => `<span class="strong">${escapeHtml(r.nome)}</span>` },
      { key: "campanha", label: "Campanha", render: (r) => escapeHtml(r.campanha) },
      { key: "min_logado", label: "Tempo Logado", num: true, render: (r) => `${fmt.int(r.min_logado)} min` },
      { key: "ligacoes", label: "Ligações", num: true, render: (r) => badge(fmt.int(r.ligacoes), "red") },
    ], rows, { emptyMsg: "Nenhum agente improdutivo." });
  }

  async function load() {
    const [r] = await Promise.all([Api.auditoria().catch(() => null), loadImp()]);
    renderKpis(r);
  }

  await load();
  return { onRefresh: load };
}
