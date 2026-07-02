// ── Página: Feriados & Guardrails ──────────────────────────────────
import { Api } from "../api.js";
import { badge, empty, fmt, escapeHtml, table, toast, modal } from "../ui.js";
import { getUser } from "../api.js";
import { icon } from "../icons.js";

export const meta = { title: "Feriados", subtitle: "Datas especiais e bloqueios de discagem", icon: "calendar" };

const ANO_ATUAL = new Date().getFullYear();

export async function mount(root) {
  let ano = ANO_ATUAL;
  const isAdmin = getUser()?.role === "admin";

  root.innerHTML = `
    <div class="page-head">
      <div class="actions">
        <select class="select" id="fr-ano" style="width:auto">
          <option value="${ANO_ATUAL}">${ANO_ATUAL}</option>
          <option value="${ANO_ATUAL + 1}">${ANO_ATUAL + 1}</option>
        </select>
        ${isAdmin ? `<button class="btn" id="fr-sync">${icon("refresh")} Sincronizar Nacionais</button>
        <button class="btn btn-primary" id="fr-add">${icon("plus")} Novo Feriado</button>` : ""}
      </div>
    </div>
    <div class="card" id="fr-prox-card" style="margin-bottom:18px">
      <div class="card-head">${icon("alert-triangle")}<h3>Próximos 30 dias</h3></div>
      <div class="card-body" id="fr-prox"></div>
    </div>
    <div class="card">
      <div class="card-head">${icon("calendar")}<h3>Calendário ${ano}</h3></div>
      <div class="card-body pad-0" id="fr-table"></div>
    </div>`;

  root.querySelector("#fr-ano").addEventListener("change", (e) => { ano = +e.target.value; root.querySelector(".card-head h3").textContent = `Calendário ${ano}`; loadTable(); });
  root.querySelector("#fr-sync")?.addEventListener("click", async (e) => {
    const btn = e.currentTarget; btn.disabled = true; btn.innerHTML = `<span class="spinner"></span> Sincronizando…`;
    try { const r = await Api.feriadosSync(ano); toast(`${r.sincronizados} feriados nacionais sincronizados`, "success"); await loadTable(); await loadProx(); }
    catch (err) { toast(err.message || "Falha ao sincronizar", "error"); }
    finally { btn.disabled = false; btn.innerHTML = `${icon("refresh")} Sincronizar Nacionais`; }
  });
  root.querySelector("#fr-add")?.addEventListener("click", openAddModal);

  async function loadProx() {
    const box = root.querySelector("#fr-prox");
    const rows = await Api.feriadosProximos(30).catch(() => []);
    if (!rows.length) { box.innerHTML = empty("Nenhum feriado nos próximos 30 dias", "", "check"); return; }
    box.innerHTML = rows.map((f) => {
      const acoes = [];
      if (f.pausar_mailing) acoes.push("pausa mailing");
      if (f.pausar_discagem) acoes.push("pausa discagem");
      return `<div class="alert-item">
        <div class="ai-icon" style="background:var(--orange-dim);color:var(--orange-bright)">${icon("calendar")}</div>
        <div class="ai-body">
          <div class="ai-msg"><strong>${fmt.data(f.data)}</strong> — ${escapeHtml(f.nome)} ${tipoBadge(f.tipo)}</div>
          <div class="ai-time">${acoes.join(" · ") || "sem pausa"}</div>
        </div>
      </div>`;
    }).join("");
  }

  async function loadTable() {
    const box = root.querySelector("#fr-table");
    const rows = await Api.feriados(ano).catch(() => []);
    const cols = [
      { key: "data", label: "Data", render: (f) => `<span class="strong">${fmt.data(f.data)}</span>` },
      { key: "nome", label: "Nome", render: (f) => escapeHtml(f.nome) },
      { key: "tipo", label: "Tipo", render: (f) => tipoBadge(f.tipo) },
      { key: "uf", label: "UF", render: (f) => f.uf ? badge(f.uf, "gray") : `<span class="text-faint">—</span>` },
      { key: "pausar_mailing", label: "Mailing", render: (f) => f.pausar_mailing ? `<span class="text-danger">${icon("pause", "")}</span>` : `<span class="text-success">${icon("play")}</span>` },
      { key: "pausar_discagem", label: "Discagem", render: (f) => f.pausar_discagem ? `<span class="text-danger">${icon("pause")}</span>` : `<span class="text-success">${icon("play")}</span>` },
    ];
    if (isAdmin) cols.push({ key: "acao", label: "", render: (f) => `<button class="btn btn-danger btn-sm" data-del="${f.id}">${icon("trash")}</button>` });
    box.innerHTML = table(cols, rows, { emptyMsg: `Nenhum feriado cadastrado em ${ano}.` });
    box.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => removeFeriado(+b.dataset.del)));
  }

  async function removeFeriado(id) {
    const m = modal({
      title: "Remover feriado",
      bodyHtml: `<p class="text-soft">Confirma a remoção deste feriado? A ação não pode ser desfeita.</p>`,
      footHtml: `<button class="btn" data-cancel>Cancelar</button><button class="btn btn-danger" data-ok>${icon("trash")} Remover</button>`,
    });
    m.el.querySelector("[data-cancel]").addEventListener("click", m.close);
    m.el.querySelector("[data-ok]").addEventListener("click", async () => {
      try { await Api.feriadoDel(id); toast("Feriado removido", "success"); m.close(); await loadTable(); await loadProx(); }
      catch (err) { toast(err.message || "Falha ao remover", "error"); }
    });
  }

  function openAddModal() {
    const m = modal({
      title: "Cadastrar feriado",
      bodyHtml: `
        <div class="field"><label>Data</label><input class="input" type="date" id="f-data" value="${new Date().toISOString().slice(0, 10)}"></div>
        <div class="field"><label>Nome</label><input class="input" id="f-nome" placeholder="Ex.: Aniversário da cidade"></div>
        <div class="grid grid-2" style="gap:14px">
          <div class="field"><label>Tipo</label>
            <select class="select" id="f-tipo"><option>EMPRESA</option><option>MUNICIPAL</option><option>ESTADUAL</option><option>NACIONAL</option></select>
          </div>
          <div class="field"><label>UF (opcional)</label><input class="input" id="f-uf" maxlength="2" placeholder="SP"></div>
        </div>
        <div class="row gap-lg" style="margin-top:4px">
          <label class="checkbox"><input type="checkbox" id="f-pm" checked> Pausar mailing</label>
          <label class="checkbox"><input type="checkbox" id="f-pd" checked> Pausar discagem</label>
        </div>`,
      footHtml: `<button class="btn" data-cancel>Cancelar</button><button class="btn btn-primary" data-ok>${icon("check")} Salvar</button>`,
    });
    m.el.querySelector("[data-cancel]").addEventListener("click", m.close);
    m.el.querySelector("[data-ok]").addEventListener("click", async () => {
      const data = m.el.querySelector("#f-data").value;
      const nome = m.el.querySelector("#f-nome").value.trim();
      if (!nome) { toast("Informe o nome do feriado", "warn"); return; }
      const body = {
        data, nome,
        tipo: m.el.querySelector("#f-tipo").value,
        uf: m.el.querySelector("#f-uf").value.trim().toUpperCase() || null,
        pausar_mailing: m.el.querySelector("#f-pm").checked,
        pausar_discagem: m.el.querySelector("#f-pd").checked,
      };
      try { await Api.feriadoAdd(body); toast(`Feriado '${nome}' cadastrado`, "success"); m.close(); await loadTable(); await loadProx(); }
      catch (err) { toast(err.message || "Falha ao salvar", "error"); }
    });
  }

  function tipoBadge(t) {
    const c = { NACIONAL: "orange", ESTADUAL: "blue", MUNICIPAL: "yellow", EMPRESA: "gray" }[t] || "gray";
    return badge(t, c);
  }

  await Promise.all([loadProx(), loadTable()]);
  return { onRefresh: async () => { await loadProx(); await loadTable(); } };
}
