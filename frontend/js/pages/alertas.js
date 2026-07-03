// ── Página: Central de Alertas ─────────────────────────────────────
import { Api } from "../api.js";
import { kpi, empty, skeletonKpis, fmt, escapeHtml } from "../ui.js";
import { icon } from "../icons.js";

export const meta = { title: "Alertas", subtitle: "Histórico de notificações do agente IA", icon: "bell" };

export async function mount(root) {
  let filtro = "";
  root.innerHTML = `
    <div class="page-head">
      <div class="actions" id="al-filters">
        ${["", "CRITICO", "ATENCAO", "INFO"].map((n) =>
          `<button class="btn btn-sm ${n === "" ? "btn-primary" : ""}" data-nivel="${n}">${n === "" ? "Todos" : nivelLabel(n)}</button>`).join("")}
      </div>
    </div>
    <div class="grid kpi-grid" id="al-kpis">${skeletonKpis(3)}</div>
    <div class="card" style="margin-top:18px">
      <div class="card-head">${icon("bell")}<h3>Linha do Tempo</h3></div>
      <div class="card-body" id="al-feed" style="max-height:640px;overflow-y:auto"></div>
    </div>`;

  root.querySelectorAll("#al-filters [data-nivel]").forEach((b) => b.addEventListener("click", () => {
    filtro = b.dataset.nivel;
    root.querySelectorAll("#al-filters .btn").forEach((x) => x.classList.remove("btn-primary"));
    b.classList.add("btn-primary");
    load();
  }));

  async function load() {
    const all = await Api.alertas(100).catch(() => []);
    const rows = filtro ? all.filter((a) => a.nivel === filtro) : all;
    renderKpis(all);
    renderFeed(rows);
  }

  function renderKpis(all) {
    const box = root.querySelector("#al-kpis");
    const c = (n) => all.filter((a) => a.nivel === n).length;
    box.innerHTML = [
      kpi({ label: "Críticos", value: fmt.int(c("CRITICO")), icon: "alert-octagon", tone: c("CRITICO") ? "red" : "green" }),
      kpi({ label: "Atenção", value: fmt.int(c("ATENCAO")), icon: "alert-triangle", tone: c("ATENCAO") ? "yellow" : "green" }),
      kpi({ label: "Informativos", value: fmt.int(c("INFO")), icon: "info", tone: "blue" }),
    ].join("");
  }

  function renderFeed(rows) {
    const box = root.querySelector("#al-feed");
    if (!rows.length) { box.innerHTML = empty("Nenhum alerta encontrado", "", "check"); return; }
    const ic = { CRITICO: ["alert-octagon", "danger"], ATENCAO: ["alert-triangle", "warn"], INFO: ["info", "info"] };
    box.innerHTML = rows.map((a) => {
      const [i, tone] = ic[a.nivel] || ["info", "info"];
      const msg = escapeHtml(a.mensagem).replace(/\*([^*]+)\*/g, "<strong>$1</strong>");
      return `<div class="alert-item">
        <div class="ai-icon" style="background:var(--${tone}-dim);color:var(--${tone})">${icon(i)}</div>
        <div class="ai-body">
          <div class="ai-msg">${msg}</div>
          <div class="ai-time">${fmt.dataHora(a.ts)} · ${fmt.rel(a.ts)} · ${escapeHtml(a.chave || "")}</div>
        </div>
      </div>`;
    }).join("");
  }

  function nivelLabel(n) { return { CRITICO: "Crítico", ATENCAO: "Atenção", INFO: "Info" }[n] || n; }

  await load();
  return { onRefresh: load };
}
