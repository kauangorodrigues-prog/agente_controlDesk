// ── Página: Pacing (auto-discagem preditiva) ───────────────────────
import { Api } from "../api.js";
import { kpi, badge, empty, skeletonKpis, fmt, escapeHtml, table, toast } from "../ui.js";
import { icon } from "../icons.js";

export const meta = { title: "Discagem", subtitle: "Pacing — ajuste automático da velocidade de discagem", icon: "gauge" };

export async function mount(root) {
  let horas = 24;
  let campanhaId = "";
  root.innerHTML = `
    <div class="page-head">
      <div class="actions">
        <select class="select" id="pac-camp" style="width:auto"><option value="">Todas as campanhas</option></select>
        <select class="select" id="pac-horas" style="width:auto">
          <option value="6">Últimas 6h</option>
          <option value="24" selected>Últimas 24h</option>
          <option value="72">Últimos 3 dias</option>
          <option value="168">Últimos 7 dias</option>
        </select>
        <button class="btn btn-primary" id="pac-run">${icon("zap")} Executar Ajuste</button>
      </div>
    </div>
    <div class="grid kpi-grid" id="pac-kpis">${skeletonKpis(4)}</div>
    <div class="card" style="margin-top:18px">
      <div class="card-head">${icon("list")}<h3>Histórico de Ajustes</h3></div>
      <div class="card-body pad-0" id="pac-table"></div>
    </div>`;

  root.querySelector("#pac-horas").addEventListener("change", (e) => { horas = +e.target.value; load(); });
  root.querySelector("#pac-camp").addEventListener("change", (e) => { campanhaId = e.target.value; load(); });
  (async () => {
    try {
      const camps = await Api.campanhasConfig();
      const sel = root.querySelector("#pac-camp");
      (camps || []).forEach((c) => {
        const o = document.createElement("option");
        o.value = c.campanha_id; o.textContent = c.campanha_nome || c.campanha_id;
        sel.appendChild(o);
      });
    } catch { /* silencioso */ }
  })();
  root.querySelector("#pac-run").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true; btn.innerHTML = `<span class="spinner dark"></span> Ajustando…`;
    try {
      const res = await Api.pacingAjustar();
      const r = res.resultado || {};
      const ajustados = Object.values(r).filter((x) => x.status === "ajustado").length;
      const bloqueados = Object.values(r).filter((x) => x.status === "bloqueado" || x.status === "pausado").length;
      toast(`Ajuste concluído — ${ajustados} ajustada(s), ${bloqueados} bloqueada(s)`, "success");
      await load();
    } catch (err) {
      toast(err.message || "Falha ao ajustar pacing", "error");
    } finally {
      btn.disabled = false; btn.innerHTML = `${icon("zap")} Executar Ajuste`;
    }
  });

  async function load() {
    const rows = await Api.pacingHistorico(horas, campanhaId || undefined).catch(() => []);
    renderKpis(rows);
    renderTable(rows);
  }

  function renderKpis(rows) {
    const box = root.querySelector("#pac-kpis");
    if (!rows.length) { box.innerHTML = empty("Nenhum ajuste no período"); return; }
    const efetivados = rows.filter((r) => !r.bloqueado).length;
    const bloqueados = rows.filter((r) => r.bloqueado).length;
    const subiu = rows.filter((r) => !r.bloqueado && r.pacing_novo > r.pacing_anterior).length;
    box.innerHTML = [
      kpi({ label: "Total de Ajustes", value: fmt.int(rows.length), icon: "activity", tone: "orange" }),
      kpi({ label: "Efetivados", value: fmt.int(efetivados), icon: "check", tone: "green" }),
      kpi({ label: "Bloqueados (guardrail)", value: fmt.int(bloqueados), icon: "shield", tone: bloqueados ? "yellow" : "green" }),
      kpi({ label: "Pacing Elevado", value: fmt.int(subiu), icon: "trending", tone: "blue", delta: "aceleração de discagem", deltaDir: "up" }),
    ].join("");
  }

  function renderTable(rows) {
    const box = root.querySelector("#pac-table");
    box.innerHTML = table([
      { key: "ts", label: "Horário", render: (r) => `<span class="mono">${fmt.horaS(r.ts)}</span>` },
      { key: "campanha_nome", label: "Campanha", render: (r) => `<span class="strong">${escapeHtml(r.campanha_nome)}</span>` },
      { key: "mov", label: "Ajuste", render: (r) => {
        if (r.bloqueado) return badge("bloqueado", "gray");
        const up = r.pacing_novo > r.pacing_anterior;
        return `<span class="mono">${fmt.num(r.pacing_anterior)} <span class="${up ? "text-success" : "text-warn"}">${up ? "↑" : "↓"}</span> ${fmt.num(r.pacing_novo)}</span>`;
      } },
      { key: "ocupacao_pct", label: "Ocupação", num: true, render: (r) => fmt.pct(r.ocupacao_pct) },
      { key: "motivo", label: "Motivo", render: (r) => motivoBadge(r.motivo) },
      { key: "status", label: "Status", render: (r) => r.bloqueado
          ? badge(r.motivo_bloqueio || "bloqueado", "yellow", true)
          : badge("ajustado", "green", true) },
    ], rows, { emptyMsg: "Nenhum ajuste de pacing registrado." });
  }

  function motivoBadge(m) {
    const map = {
      ajuste_proporcional: ["Proporcional", "blue"],
      abandono_alto: ["Abandono alto", "red"],
      bloqueado_guardrail: ["Guardrail", "yellow"],
      pausa_feriado: ["Feriado", "orange"],
    };
    const [t, c] = map[m] || [m, "gray"];
    return badge(t, c);
  }

  await load();
  return { onRefresh: load };
}
