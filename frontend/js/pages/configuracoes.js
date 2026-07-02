// ── Página: Configurações ──────────────────────────────────────────
import { Api, getUser } from "../api.js";
import { CONFIG, Demo, API_BASE } from "../config.js";
import { badge, empty, fmt, escapeHtml, table, toast } from "../ui.js";
import { icon } from "../icons.js";

export const meta = { title: "Configurações", subtitle: "Sessão, integrações e operações manuais", icon: "settings" };

export async function mount(root) {
  const user = getUser();
  const demoOn = Demo.forced;

  root.innerHTML = `
    <div class="grid grid-2">
      <div class="card">
        <div class="card-head">${icon("shield")}<h3>Conta & Sessão</h3></div>
        <div class="card-body" id="cfg-conta">
          <div class="progress-row"><div class="lbl"><span>Usuário</span><b>${escapeHtml(user?.username || "—")}</b></div></div>
          <div class="progress-row"><div class="lbl"><span>Papel</span><b>${user?.role === "admin" ? badge("Administrador", "orange") : badge(user?.role || "usuário", "gray")}</b></div></div>
          <div class="progress-row"><div class="lbl"><span>Versão</span><b>ATLAS ${CONFIG.version}</b></div></div>
          <div class="progress-row" style="margin-bottom:0"><div class="lbl"><span>Modo</span><b id="cfg-modo">—</b></div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-head">${icon("server")}<h3>Fonte de Dados</h3></div>
        <div class="card-body">
          <div class="progress-row"><div class="lbl"><span>Banco de dados</span><b id="cfg-db">Verificando…</b></div></div>
          <div class="field" style="margin-top:8px">
            <label>Base da API</label>
            <div class="row gap-sm">
              <input class="input" id="cfg-apibase" placeholder="mesma origem" value="${escapeHtml(API_BASE)}">
              <button class="btn" id="cfg-apibase-save">${icon("check")} Salvar</button>
            </div>
          </div>
          <label class="checkbox" style="margin-top:6px">
            <input type="checkbox" id="cfg-demo" ${demoOn ? "checked" : ""}> Forçar modo demonstração (dados simulados)
          </label>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:18px">
      <div class="card-head">${icon("refresh")}<h3>Operações Manuais</h3><span class="spacer"></span><span class="sub">executam pipelines do agente</span></div>
      <div class="card-body">
        <div class="row gap" style="flex-wrap:wrap">
          <button class="btn btn-primary" id="op-etl">${icon("database")} Executar ETL agora</button>
          <button class="btn" id="op-mailing">${icon("spark")} Recalcular Mailing</button>
          <button class="btn" id="op-forecast">${icon("trending")} Gerar Forecast</button>
          <button class="btn" id="op-audit">${icon("shield")} Executar Auditoria</button>
        </div>
        <div id="op-result" style="margin-top:16px"></div>
      </div>
    </div>

    <div class="card" style="margin-top:18px">
      <div class="card-head">${icon("sliders")}<h3>Configuração de Campanhas</h3><span class="spacer"></span><span class="sub">guardrails de horário e pacing</span></div>
      <div class="card-body pad-0" id="cfg-camp"></div>
    </div>`;

  // ── Modo / DB status
  async function loadStatus() {
    const h = await Api.health().catch(() => null);
    const modo = root.querySelector("#cfg-modo");
    const db = root.querySelector("#cfg-db");
    if (Demo.active || Demo.forced) {
      modo.innerHTML = badge("Demonstração", "yellow", true);
      db.innerHTML = `<span class="text-warn">simulado</span>`;
    } else {
      modo.innerHTML = badge("Produção", "green", true);
      db.innerHTML = h?.banco ? `<span class="text-success">conectado</span>` : `<span class="text-danger">offline</span>`;
    }
  }

  // ── Base da API
  root.querySelector("#cfg-apibase-save").addEventListener("click", () => {
    const v = root.querySelector("#cfg-apibase").value.trim();
    if (v) localStorage.setItem("cd_api_base", v); else localStorage.removeItem("cd_api_base");
    toast("Base da API salva — recarregando…", "success", 1500);
    setTimeout(() => location.reload(), 900);
  });

  // ── Toggle demo
  root.querySelector("#cfg-demo").addEventListener("change", (e) => {
    Demo.forced = e.target.checked;
    toast(e.target.checked ? "Modo demonstração ativado — recarregando…" : "Modo demonstração desativado — recarregando…", "info", 1500);
    setTimeout(() => location.reload(), 900);
  });

  // ── Operações manuais
  const ops = {
    "op-etl": { fn: () => Api.etlRun(), label: "ETL", fmt: (r) => resultCounts(r.resultado || r) },
    "op-mailing": { fn: () => Api.mailingProcessar(), label: "Mailing", fmt: (r) => `${fmt.int(r.registros)} registros pontuados` },
    "op-forecast": { fn: () => Api.forecastGerar(24, 5), label: "Forecast", fmt: (r) => `${fmt.int(r.periodos)} períodos previstos` },
    "op-audit": { fn: () => Api.auditoria(), label: "Auditoria", fmt: (r) => resultCounts(r) },
  };
  Object.entries(ops).forEach(([id, cfg]) => {
    const btn = root.querySelector("#" + id);
    btn.addEventListener("click", async () => {
      const orig = btn.innerHTML;
      btn.disabled = true; btn.innerHTML = `<span class="spinner ${btn.classList.contains("btn-primary") ? "dark" : ""}"></span> Executando…`;
      try {
        const r = await cfg.fn();
        toast(`${cfg.label} concluído`, "success");
        root.querySelector("#op-result").innerHTML =
          `<div class="alert-item"><div class="ai-icon" style="background:var(--success-dim);color:var(--success)">${icon("check")}</div>
           <div class="ai-body"><div class="ai-msg"><strong>${cfg.label}</strong> — ${cfg.fmt(r)}</div><div class="ai-time">${fmt.horaS(new Date().toISOString())}</div></div></div>`;
      } catch (err) {
        toast(err.message || `Falha em ${cfg.label}`, "error");
      } finally { btn.disabled = false; btn.innerHTML = orig; }
    });
  });

  function resultCounts(obj) {
    if (!obj || typeof obj !== "object") return "concluído";
    return Object.entries(obj)
      .filter(([k]) => k !== "ts")
      .map(([k, v]) => `${escapeHtml(k)}: <b>${typeof v === "number" ? fmt.int(v) : escapeHtml(String(v))}</b>`)
      .join(" · ") || "sem alterações";
  }

  // ── Config de campanhas
  async function loadCamp() {
    const box = root.querySelector("#cfg-camp");
    const rows = await Api.campanhasConfig().catch(() => []);
    box.innerHTML = table([
      { key: "campanha_nome", label: "Campanha", render: (r) => `<span class="strong">${escapeHtml(r.campanha_nome || r.campanha_id)}</span>` },
      { key: "uf_restricao", label: "UF", render: (r) => r.uf_restricao ? badge(r.uf_restricao, "gray") : `<span class="text-faint">—</span>` },
      { key: "horario", label: "Horário", render: (r) => `<span class="mono">${escapeHtml(r.hora_inicio || "08:00")}–${escapeHtml(r.hora_fim || "21:00")}</span>` },
      { key: "sabado", label: "Sábado até", render: (r) => `<span class="mono">${escapeHtml(r.hora_fim_sabado || "16:00")}</span>` },
      { key: "pacing", label: "Pacing", num: true, render: (r) => `<span class="mono">${fmt.num(r.pacing_min ?? 1)}–${fmt.num(r.pacing_max ?? 8)}</span>` },
      { key: "domingo", label: "Domingo", render: (r) => r.permitir_domingo ? badge("permitido", "yellow") : badge("bloqueado", "green") },
      { key: "feriados", label: "Feriados", render: (r) => r.pausar_feriados !== false ? badge("pausa", "orange") : badge("ativo", "gray") },
    ], rows, { emptyMsg: "Nenhuma configuração de campanha encontrada." });
  }

  await Promise.all([loadStatus(), loadCamp()]);
  return { onRefresh: loadStatus };
}
