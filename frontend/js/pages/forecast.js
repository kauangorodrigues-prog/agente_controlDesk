// ── Página: Forecast operacional ───────────────────────────────────
import { Api } from "../api.js";
import { kpi, empty, skeletonKpis, fmt, toast } from "../ui.js";
import { icon } from "../icons.js";
import { lineChart, barChart, riskColor } from "../charts.js";

export const meta = { title: "Previsão", subtitle: "Forecast de volume e dimensionamento de equipe", icon: "trending" };

export async function mount(root) {
  root.innerHTML = `
    <div class="page-head">
      <div class="actions">
        <button class="btn btn-primary" id="fc-gen">${icon("trending")} Gerar Previsão</button>
      </div>
    </div>
    <div class="grid kpi-grid" id="fc-kpis">${skeletonKpis(4)}</div>
    <div class="card" style="margin-top:18px">
      <div class="card-head">${icon("chart")}<h3>Volume Previsto por Hora</h3><span class="spacer"></span><span class="sub">com intervalo de confiança</span></div>
      <div class="card-body" id="fc-line" style="min-height:260px"></div>
    </div>
    <div class="card" style="margin-top:18px">
      <div class="card-head">${icon("users")}<h3>Agentes Necessários</h3></div>
      <div class="card-body" id="fc-bar" style="min-height:240px"></div>
    </div>`;

  root.querySelector("#fc-gen").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true; btn.innerHTML = `<span class="spinner dark"></span> Gerando…`;
    try {
      const res = await Api.forecastGerar(24, 5.0);
      toast(`Previsão gerada — ${res.periodos} períodos`, "success");
      await load();
    } catch (err) { toast(err.message || "Falha ao gerar previsão", "error"); }
    finally { btn.disabled = false; btn.innerHTML = `${icon("trending")} Gerar Previsão`; }
  });

  async function load() {
    const rows = await Api.forecast().catch(() => []);
    renderKpis(rows);
    renderCharts(rows);
  }

  function renderKpis(rows) {
    const box = root.querySelector("#fc-kpis");
    if (!rows.length) { box.innerHTML = empty("Nenhuma previsão gerada", "Clique em 'Gerar Previsão'"); return; }
    const pico = Math.max(...rows.map((r) => r.yhat));
    const picoRow = rows.find((r) => r.yhat === pico);
    const totalVol = rows.reduce((s, r) => s + r.yhat, 0);
    const picoAg = Math.max(...rows.map((r) => r.agentes_necessarios));
    box.innerHTML = [
      kpi({ label: "Volume Total Previsto", value: fmt.int(totalVol), icon: "phone", tone: "orange", delta: `próximas ${rows.length}h`, deltaDir: "flat" }),
      kpi({ label: "Pico de Chamadas", value: fmt.int(pico), icon: "trending", tone: "blue", delta: picoRow ? `às ${fmt.hora(picoRow.ds)}` : "", deltaDir: "up" }),
      kpi({ label: "Agentes no Pico", value: fmt.int(picoAg), icon: "users", tone: "green" }),
      kpi({ label: "Média/Hora", value: fmt.int(totalVol / rows.length), icon: "activity", tone: "orange" }),
    ].join("");
  }

  function renderCharts(rows) {
    const line = root.querySelector("#fc-line");
    const bar = root.querySelector("#fc-bar");
    if (!rows.length) { line.innerHTML = empty("Sem previsão"); bar.innerHTML = ""; return; }
    lineChart(line, rows.map((r) => ({ label: fmt.hora(r.ds), y: r.yhat, lower: r.yhat_lower, upper: r.yhat_upper })),
      { height: 260, band: true, yLabel: "Chamadas" });
    barChart(bar, rows.map((r) => ({ label: fmt.hora(r.ds), value: r.agentes_necessarios })),
      { height: 240, valueFmt: (v) => fmt.int(v) });
  }

  await load();
  return { onRefresh: load };
}
