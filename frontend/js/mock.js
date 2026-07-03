// ══════════════════════════════════════════════════════════════════
// Camada de dados simulados (modo DEMO)
// Reproduz o formato exato retornado por cada endpoint do FastAPI,
// permitindo que o dashboard seja totalmente funcional sem o backend.
// ══════════════════════════════════════════════════════════════════

const CAMPANHAS = [
  { id: "CMP001", nome: "Itaú · Cartão", uf: "SP" },
  { id: "CMP002", nome: "Santander · Consignado", uf: "SP" },
  { id: "CMP003", nome: "Bradesco · Empréstimo", uf: "RJ" },
  { id: "CMP004", nome: "Nubank · Rotativo", uf: "MG" },
  { id: "CMP005", nome: "Caixa · Habitacional", uf: "BA" },
];

const NOMES = [
  "Ana Paula Souza", "Bruno Carvalho", "Carla Mendes", "Diego Ramos",
  "Elaine Torres", "Felipe Nunes", "Gabriela Lima", "Henrique Alves",
  "Isabela Rocha", "João Pedro Dias", "Karina Freitas", "Lucas Martins",
  "Mariana Costa", "Nathan Oliveira", "Patrícia Gomes", "Rafael Barbosa",
];

// Gerador determinístico-ish com leve variação temporal para parecer "vivo"
function jitter(base, amp) {
  const t = Date.now() / 60000; // muda a cada minuto
  return base + Math.sin(t + base) * amp + (Math.random() - 0.5) * amp * 0.4;
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const r = (min, max) => Math.random() * (max - min) + min;
const ri = (min, max) => Math.floor(r(min, max + 1));
const pick = (arr) => arr[ri(0, arr.length - 1)];
const nowISO = () => new Date().toISOString();

function fakeCPF() {
  let n = "";
  for (let i = 0; i < 11; i++) n += ri(0, 9);
  return n.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
}
function fakeTel() {
  const ddd = pick(["11", "21", "31", "41", "51", "71", "85", "61"]);
  return `(${ddd}) 9${ri(1000, 9999)}-${ri(1000, 9999)}`;
}

// ---------- Ocupação global ----------
function ocupacao() {
  const total = Math.round(jitter(142, 10));
  const ociosos = Math.round(clamp(jitter(18, 8), 2, total));
  const em_pausa = Math.round(clamp(jitter(12, 5), 0, total - ociosos));
  const em_ligacao = total - ociosos - em_pausa;
  const ocupacao_pct = +(((total - ociosos) / total) * 100).toFixed(2);
  const ociosidade_pct = +((ociosos / total) * 100).toFixed(2);
  const pausaLonga = [];
  const nLong = ri(0, 3);
  for (let i = 0; i < nLong; i++)
    pausaLonga.push({ nome: pick(NOMES), min_pausa: ri(21, 48) });
  return {
    total, ociosos, em_pausa, em_ligacao,
    ocupacao_pct, ociosidade_pct,
    agentes_pausa_longa: pausaLonga,
    ts: nowISO(),
  };
}

// ---------- Ocupação por campanha ----------
function ocupacaoCampanhas() {
  return CAMPANHAS.map((c) => {
    const total = ri(18, 38);
    const ociosos = ri(1, Math.round(total * 0.25));
    const em_pausa = ri(0, Math.round(total * 0.15));
    const em_ligacao = total - ociosos - em_pausa;
    return {
      campanha: c.nome, total, ociosos, em_pausa, em_ligacao,
      ociosidade_pct: +((ociosos / total) * 100).toFixed(1),
      ocupacao_pct: +(((total - ociosos) / total) * 100).toFixed(1),
    };
  });
}

// ---------- Config de campanhas ----------
function campanhasConfig() {
  return CAMPANHAS.map((c) => ({
    campanha_id: c.id,
    campanha_nome: c.nome,
    uf_restricao: c.uf,
    hora_inicio: "08:00",
    hora_fim: "21:00",
    hora_fim_sabado: "16:00",
    pacing_min: 1.0,
    pacing_max: 8.0,
    permitir_domingo: false,
    pausar_feriados: true,
    ativo: true,
  }));
}

// ---------- Snapshot / desempenho campanhas ----------
function campanhasDesempenho() {
  return CAMPANHAS.map((c) => {
    const acion = ri(1800, 9200);
    const cpcRate = r(0.14, 0.32);
    const cpcs = Math.round(acion * cpcRate);
    return {
      campanha_id: c.id,
      campanha: c.nome,
      agentes: ri(18, 38),
      acionamentos: acion,
      cpcs,
      rpcs: Math.round(cpcs * r(0.6, 0.9)),
      cpc_pct: +(cpcRate * 100).toFixed(1),
      ociosidade: +r(4, 22).toFixed(1),
      abandono: +r(1.5, 9).toFixed(1),
      mailing_restante: +r(3, 68).toFixed(1),
      pacing_medio: +r(1.5, 7.5).toFixed(1),
      status: Math.random() > 0.15 ? "ACTIVE" : "PAUSED",
    };
  });
}

// ---------- Histórico de pacing ----------
function pacingHistorico(horas = 24, campanhaId = null) {
  const rows = [];
  const n = ri(40, 90);
  const pool = campanhaId ? CAMPANHAS.filter((c) => c.id === campanhaId) : CAMPANHAS;
  const base = pool.length ? pool : CAMPANHAS;
  for (let i = 0; i < n; i++) {
    const c = pick(base);
    const ant = +r(1, 8).toFixed(1);
    const bloqueado = Math.random() < 0.18;
    const motivo = bloqueado ? pick(["bloqueado_guardrail", "pausa_feriado"]) : pick(["ajuste_proporcional", "abandono_alto"]);
    rows.push({
      campanha_id: c.id,
      campanha_nome: c.nome,
      pacing_anterior: ant,
      pacing_novo: bloqueado ? 0 : +clamp(ant + r(-2, 2), 1, 8).toFixed(1),
      motivo,
      ocupacao_pct: +r(65, 95).toFixed(1),
      bloqueado,
      motivo_bloqueio: bloqueado ? (motivo === "pausa_feriado" ? "Feriado: Corpus Christi" : "Após o horário permitido (fim: 21:00)") : "",
      ts: new Date(Date.now() - ri(0, horas * 3600 * 1000)).toISOString(),
    });
  }
  return rows.sort((a, b) => new Date(b.ts) - new Date(a.ts));
}

// ---------- Mailing top ----------
function mailingTop(n = 100, campanhaId = null) {
  const rows = [];
  const pool = campanhaId ? CAMPANHAS.filter((c) => c.id === campanhaId) : CAMPANHAS;
  const base = pool.length ? pool : CAMPANHAS;
  for (let i = 0; i < n; i++) {
    const c = pick(base);
    rows.push({
      cpf: fakeCPF(),
      telefone: fakeTel(),
      nome: pick(NOMES),
      campanha_id: c.id,
      campanha: c.nome,
      ddd: /\((\d{2})\)/.exec(fakeTel())?.[1] ?? "11",
      days_delay: ri(5, 180),
      faixa_atraso_dias: ri(10, 120),
      previous_cpc: +r(0, 1).toFixed(2),
      score_discagem: +r(35, 99).toFixed(1),
      promessa_quebrada: Math.random() < 0.2,
    });
  }
  return rows.sort((a, b) => b.score_discagem - a.score_discagem);
}

// ---------- Forecast ----------
function forecast(periodos = 24) {
  const rows = [];
  const base = new Date();
  base.setMinutes(0, 0, 0);
  for (let i = 1; i <= periodos; i++) {
    const ds = new Date(base.getTime() + i * 3600 * 1000);
    const h = ds.getHours();
    // curva diária: pico ~10h e ~15h
    const dayFactor = h < 8 || h > 21 ? 0.15 : (0.6 + 0.4 * Math.sin(((h - 8) / 13) * Math.PI));
    const yhat = Math.round(clamp(dayFactor * r(700, 1000), 0, 1400));
    rows.push({
      ds: ds.toISOString(),
      yhat,
      yhat_lower: Math.round(yhat * 0.82),
      yhat_upper: Math.round(yhat * 1.18),
      agentes_necessarios: Math.ceil((yhat * (5 / 60))),
    });
  }
  return rows;
}

// ---------- Feriados ----------
const FERIADOS_2026 = [
  ["2026-01-01", "Confraternização Universal", "NACIONAL", null],
  ["2026-02-16", "Carnaval", "NACIONAL", null],
  ["2026-02-17", "Carnaval", "NACIONAL", null],
  ["2026-04-03", "Sexta-feira Santa", "NACIONAL", null],
  ["2026-04-21", "Tiradentes", "NACIONAL", null],
  ["2026-05-01", "Dia do Trabalho", "NACIONAL", null],
  ["2026-06-04", "Corpus Christi", "NACIONAL", null],
  ["2026-07-09", "Revolução Constitucionalista", "ESTADUAL", "SP"],
  ["2026-09-07", "Independência do Brasil", "NACIONAL", null],
  ["2026-10-12", "Nossa Senhora Aparecida", "NACIONAL", null],
  ["2026-11-02", "Finados", "NACIONAL", null],
  ["2026-11-15", "Proclamação da República", "NACIONAL", null],
  ["2026-11-20", "Consciência Negra", "NACIONAL", null],
  ["2026-12-25", "Natal", "NACIONAL", null],
];
function feriados(ano) {
  const y = ano || new Date().getFullYear();
  return FERIADOS_2026.filter((f) => f[0].startsWith(String(y))).map((f, i) => ({
    id: i + 1,
    data: f[0],
    nome: f[1],
    tipo: f[2],
    uf: f[3],
    municipio: null,
    pausar_mailing: true,
    pausar_discagem: true,
    pacing_especial: null,
    observacao: null,
    criado_por: "SISTEMA_AUTO",
  }));
}
function feriadosProximos(dias = 30) {
  const hoje = new Date();
  const fim = new Date(hoje.getTime() + dias * 86400000);
  return feriados(hoje.getFullYear())
    .concat(feriados(hoje.getFullYear() + 1))
    .filter((f) => {
      const d = new Date(f.data);
      return d >= hoje && d <= fim;
    });
}

// ---------- Alertas ----------
function alertas(limite = 50) {
  const templates = [
    ["ATENCAO", "Ociosidade em *{p}%* (limite 15.0%) — Ociosos: {a}/{t}", "ociosidade_alta"],
    ["ATENCAO", "Agentes em pausa > 20 min: {nome}", "pausa_longa"],
    ["CRITICO", "Mailing *{camp}*: apenas *{p}%* restante", "auditoria"],
    ["INFO", "Pacing *{camp}* ajustado: {x} → {y} ↑", "pacing"],
    ["INFO", "Campanha *{camp}* pausada — Feriado: Corpus Christi", "pausa_feriado"],
    ["ATENCAO", "*{n} campanha(s) parada(s)*: {camp}", "auditoria"],
    ["INFO", "*Intraday {hh}:00* — Acionamentos: *{a}* | CPCs: *{c}* ({p}%)", "relatorio_intraday"],
    ["CRITICO", "Abandono em *{p}%* na campanha {camp} (limite 8.0%)", "abandono"],
  ];
  const rows = [];
  const n = Math.min(limite, ri(18, 40));
  for (let i = 0; i < n; i++) {
    const [nivel, tpl, chave] = pick(templates);
    const camp = pick(CAMPANHAS).nome;
    const msg = tpl
      .replace("{p}", r(3, 24).toFixed(1))
      .replace("{a}", ri(20, 40))
      .replace("{t}", ri(120, 160))
      .replace("{camp}", camp)
      .replace("{nome}", pick(NOMES))
      .replace("{x}", r(1, 4).toFixed(1))
      .replace("{y}", r(4, 8).toFixed(1))
      .replace("{n}", ri(1, 3))
      .replace("{hh}", String(ri(8, 20)).padStart(2, "0"))
      .replace("{c}", ri(300, 1200));
    rows.push({
      nivel, mensagem: msg, chave, canal: "webhook", enviado: true,
      ts: new Date(Date.now() - i * ri(3, 25) * 60000).toISOString(),
    });
  }
  return rows.sort((a, b) => new Date(b.ts) - new Date(a.ts));
}

// ---------- Auditoria ----------
function auditoria() {
  return {
    agentes_improdutivos: ri(0, 5),
    campanhas_paradas: ri(0, 2),
    mailing_critico: ri(0, 3),
    ts: nowISO(),
  };
}
function agentesImprodutivos() {
  const n = ri(0, 5);
  const rows = [];
  for (let i = 0; i < n; i++) {
    rows.push({
      nome: pick(NOMES),
      campanha: pick(CAMPANHAS).nome,
      min_logado: ri(35, 180),
      ligacoes: 0,
    });
  }
  return rows;
}

// ---------- Health ----------
function health() {
  return { status: "running", versao: "2.0.0", banco: false };
}

// ---------- Roteador do mock por (método + caminho) ----------
export function mockResponse(method, path) {
  const p = path.split("?")[0];
  const q = new URLSearchParams(path.split("?")[1] || "");

  if (p === "/" || p === "/health") return health();
  if (p === "/ocupacao") return ocupacao();
  if (p === "/ocupacao/campanhas") return ocupacaoCampanhas();
  if (p === "/campanhas/config") return campanhasConfig();
  if (p === "/campanhas/desempenho") return campanhasDesempenho(); // extra p/ frontend
  if (p === "/pacing/historico") return pacingHistorico(+(q.get("horas") || 24), q.get("campanha_id"));
  if (p === "/pacing/ajustar") return { resultado: pacingAjustarMock() };
  if (p === "/mailing/top") return mailingTop(+(q.get("n") || 100), q.get("campanha_id"));
  if (p === "/mailing/processar") return { registros: ri(1200, 4800) };
  if (p === "/forecast") return forecast(24);
  if (p === "/forecast/gerar") return { periodos: +(q.get("periodos") || 24) };
  if (p === "/feriados") return feriados(q.get("ano") ? +q.get("ano") : undefined);
  if (p === "/feriados/proximos") return feriadosProximos(+(q.get("dias") || 30));
  if (p === "/feriados/sincronizar") return { sincronizados: 14 };
  if (p === "/auditoria/executar") return auditoria();
  if (p === "/auditoria/improdutivos") return agentesImprodutivos(); // extra
  if (p === "/alertas") return alertas(+(q.get("limite") || 50));
  if (p === "/etl/run") return { resultado: { agentes: ri(100, 160), chamadas: ri(8000, 20000), campanhas: 5, mailing: 5, clientes: ri(3000, 9000), promessas: ri(50, 300) } };
  // POST feriados / DELETE etc.
  if (p.startsWith("/feriados") && (method === "POST" || method === "DELETE"))
    return { message: "ok (demo)" };

  return {};
}

function pacingAjustarMock() {
  const out = {};
  CAMPANHAS.forEach((c) => {
    const roll = Math.random();
    if (roll < 0.2) out[c.id] = { status: "bloqueado", motivo: "Após o horário permitido" };
    else if (roll < 0.4) out[c.id] = { status: "sem_alteracao", pacing: +r(2, 6).toFixed(1) };
    else out[c.id] = { status: "ajustado", pacing_anterior: +r(1, 4).toFixed(1), pacing_novo: +r(4, 8).toFixed(1) };
  });
  return out;
}

// Credenciais demo aceitas no login offline
export const DEMO_CREDS = { username: "admin", password: "admin", role: "admin" };
