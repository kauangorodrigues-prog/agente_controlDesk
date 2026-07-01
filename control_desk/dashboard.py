from __future__ import annotations

import time
from datetime import date

from .db import engine, testar_conexao
from .holidays import HolidayService
from .logging_setup import get_logger
from .occupancy import STATUS_LIGANDO, STATUS_OCIOSO, STATUS_PAUSA

log = get_logger("dashboard")


def rodar_dashboard() -> None:
    """Execute com: streamlit run main.py -- dashboard"""
    try:
        import pandas as pd
        import plotly.express as px
        import streamlit as st
    except ImportError:
        print("Streamlit/Plotly não instalados. Rode: pip install streamlit plotly")
        return

    from .audit import AuditService
    from .discagem import DISCAGEM

    st.set_page_config(page_title="Control Desk IA", page_icon="🤖", layout="wide")

    with st.sidebar:
        st.title("🤖 Control Desk IA")
        st.caption(f"v3.0.0 | {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")
        banco_ok = testar_conexao()
        st.markdown(f"**Banco:** {'🟢 Conectado' if banco_ok else '🔴 Offline'}")
        st.divider()
        try:
            camps = pd.read_sql("SELECT DISTINCT campanha FROM campaign_snapshot ORDER BY campanha", engine)
            camp_lista = ["Todas"] + camps["campanha"].tolist()
        except Exception:
            camp_lista = ["Todas"]
        camp_filtro = st.selectbox("🎯 Campanha", camp_lista)
        auto_refresh = st.toggle("⟳ Auto-refresh 30s", value=True)
        if st.button("🔄 Atualizar"):
            st.rerun()

    def _q(sql, params=None):
        try:
            return pd.read_sql(sql, engine, params=params)
        except Exception:
            return pd.DataFrame()

    aba1, aba2, aba3, aba4, aba5, aba6, aba7 = st.tabs([
        "📊 Tempo Real", "📋 Campanhas", "⚙️ Pacing Log",
        "📈 Forecast", "🗓️ Feriados", "🔍 Auditoria", "🧠 Discagem",
    ])

    # ── Aba 1: Tempo Real
    with aba1:
        st.subheader("Visão em Tempo Real")
        df_ag = _q("SELECT * FROM agents WHERE captured_at >= NOW() - INTERVAL '6 minutes'")
        if not df_ag.empty:
            df_ag["status_norm"] = df_ag["status"].str.lower().str.strip()
            total = len(df_ag)
            ociosos = int(df_ag["status_norm"].isin(STATUS_OCIOSO).sum())
            em_pausa = int(df_ag["status_norm"].isin(STATUS_PAUSA).sum())
            em_lig = int(df_ag["status_norm"].isin(STATUS_LIGANDO).sum())
            ocio_pct = round(ociosos / total * 100, 1) if total else 0
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("👥 Logados", total)
            c2.metric("📞 Em ligação", em_lig)
            c3.metric("✅ Disponíveis", ociosos, delta=f"{ocio_pct}% ociosos")
            c4.metric("⏸️ Em pausa", em_pausa)
            c5.metric("📊 Ocupação", f"{round((total - ociosos) / total * 100, 1) if total else 0}%")

        st.divider()
        df_ml = _q(
            "SELECT DISTINCT ON (campanha_id) campanha, mailing_restante_pct "
            "FROM mailing_status WHERE captured_at >= NOW() - INTERVAL '10 minutes' "
            "ORDER BY campanha_id, captured_at DESC"
        )
        if not df_ml.empty:
            st.subheader("📬 Mailing")
            for _, r in df_ml.iterrows():
                st.progress(int(r["mailing_restante_pct"]), text=f"{r['campanha']} — {r['mailing_restante_pct']:.1f}%")

        st.divider()
        df_al = _q("SELECT nivel, mensagem, ts FROM alert_log ORDER BY ts DESC LIMIT 10")
        st.subheader("🔔 Alertas Recentes")
        if df_al.empty:
            st.info("Nenhum alerta.")
        else:
            for _, r in df_al.iterrows():
                icone = {"CRITICO": "🔴", "ATENCAO": "⚠️", "INFO": "ℹ️"}.get(r["nivel"], "📢")
                ts = pd.to_datetime(r["ts"]).strftime("%H:%M:%S")
                st.markdown(f"`{ts}` {icone} **[{r['nivel']}]** {r['mensagem']}")

    # ── Aba 2: Campanhas
    with aba2:
        st.subheader("Desempenho por Campanha")
        sql = (
            "SELECT campanha, MAX(agentes_logados) AS agentes, AVG(ociosidade_pct) AS ociosidade, "
            "AVG(abandono_pct) AS abandono, MIN(mailing_restante_pct) AS mailing_restante, "
            "AVG(pacing_atual) AS pacing_medio FROM campaign_snapshot WHERE DATE(captured_at) = CURRENT_DATE"
        )
        params = {}
        if camp_filtro != "Todas":
            sql += " AND campanha = :camp"
            params["camp"] = camp_filtro
        sql += " GROUP BY campanha ORDER BY campanha"
        df_c = _q(sql, params)
        if not df_c.empty:
            st.dataframe(df_c.round(1), use_container_width=True, hide_index=True)
            fig = px.bar(df_c, x="campanha", y="ociosidade", title="Ociosidade por Campanha (%)",
                         color="ociosidade", color_continuous_scale=["green", "yellow", "red"])
            st.plotly_chart(fig, use_container_width=True)

    # ── Aba 3: Pacing Log
    with aba3:
        st.subheader("Histórico de Ajustes de Pacing")
        df_p = _q(
            "SELECT campanha_nome, pacing_anterior, pacing_novo, motivo, ocupacao_pct, bloqueado, "
            "motivo_bloqueio, ts FROM pacing_audit_log WHERE ts >= NOW() - INTERVAL '24 hours' "
            "ORDER BY ts DESC LIMIT 200"
        )
        if not df_p.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total", len(df_p))
            c2.metric("Efetivados", int((~df_p["bloqueado"]).sum()))
            c3.metric("Bloqueados", int(df_p["bloqueado"].sum()))
            df_p["status"] = df_p["bloqueado"].map({True: "🔒 Bloqueado", False: "✅ Ajustado"})
            st.dataframe(df_p, use_container_width=True, hide_index=True)

    # ── Aba 4: Forecast
    with aba4:
        st.subheader("Previsão de Volume")
        df_fc = _q(
            "SELECT ds, yhat, yhat_lower, yhat_upper, agentes_necessarios FROM forecast_calls "
            "WHERE gerado_em=(SELECT MAX(gerado_em) FROM forecast_calls) ORDER BY ds"
        )
        if not df_fc.empty:
            df_fc["ds"] = pd.to_datetime(df_fc["ds"])
            c1, c2 = st.columns(2)
            c1.metric("Pico previsto", f"{int(df_fc['yhat'].max())} chamadas")
            c2.metric("Agentes no pico", f"{int(df_fc['agentes_necessarios'].max())}")
            fig = px.line(df_fc, x="ds", y="yhat", title="Volume Previsto por Hora")
            st.plotly_chart(fig, use_container_width=True)
            fig2 = px.bar(df_fc, x="ds", y="agentes_necessarios", title="Agentes Necessários",
                          color="agentes_necessarios", color_continuous_scale=["green", "yellow", "red"])
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhuma previsão gerada. Use POST /forecast/gerar")

    # ── Aba 5: Feriados
    with aba5:
        st.subheader("🗓️ Gestão de Feriados e Datas Especiais")
        df_prox = _q(
            "SELECT data, nome, tipo, pausar_mailing, pausar_discagem FROM feriados "
            "WHERE data BETWEEN CURRENT_DATE AND CURRENT_DATE + 30 ORDER BY data"
        )
        if not df_prox.empty:
            st.warning(f"⚠️ **{len(df_prox)} feriado(s) nos próximos 30 dias**")
            for _, r in df_prox.iterrows():
                d = pd.to_datetime(r["data"]).strftime("%d/%m/%Y")
                acoes = []
                if r["pausar_mailing"]:
                    acoes.append("pausa mailing")
                if r["pausar_discagem"]:
                    acoes.append("pausa discagem")
                st.markdown(f"  - **{d}** — {r['nome']} `{r['tipo']}` → {', '.join(acoes) or 'sem pausa'}")

        st.divider()
        st.subheader("Cadastrar novo feriado")
        with st.form("form_feriado", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                data_f = st.date_input("Data", value=date.today())
                nome_f = st.text_input("Nome", placeholder="Ex: Aniversário da cidade")
                tipo_f = st.selectbox("Tipo", ["EMPRESA", "MUNICIPAL", "ESTADUAL", "NACIONAL"])
            with col2:
                uf_f = st.text_input("UF (estadual/municipal)", max_chars=2)
                mun_f = st.text_input("Município")
                obs_f = st.text_input("Observação")
            col3, col4 = st.columns(2)
            with col3:
                pausar_m = st.checkbox("Pausar mailing", value=True)
                pausar_d = st.checkbox("Pausar discagem", value=True)
            with col4:
                pac_esp = st.number_input("Pacing especial (0=sem restrição)", min_value=0.0, max_value=10.0, value=0.0)

            if st.form_submit_button("➕ Adicionar"):
                if nome_f.strip():
                    ok = HolidayService.adicionar_feriado(
                        data_f=data_f, nome=nome_f, tipo=tipo_f,
                        uf=uf_f or None, municipio=mun_f or None,
                        pausar_mailing=pausar_m, pausar_discagem=pausar_d,
                        pacing_especial=pac_esp if pac_esp > 0 else None,
                        observacao=obs_f or None, criado_por="Dashboard",
                    )
                    if ok:
                        st.success(f"✅ '{nome_f}' cadastrado para {data_f.strftime('%d/%m/%Y')}")
                        st.rerun()
                    else:
                        st.error("Erro ao salvar.")
                else:
                    st.error("Informe o nome do feriado.")

        st.divider()
        ano_sel = st.selectbox("Ano", [date.today().year, date.today().year + 1])
        df_fer = _q(
            "SELECT id, data, nome, tipo, uf, pausar_mailing, pausar_discagem FROM feriados "
            "WHERE EXTRACT(YEAR FROM data) = :ano ORDER BY data", {"ano": ano_sel}
        )
        if not df_fer.empty:
            df_fer["data"] = pd.to_datetime(df_fer["data"]).dt.strftime("%d/%m/%Y")
            df_fer["pausar_mailing"] = df_fer["pausar_mailing"].map({True: "✅", False: "❌"})
            df_fer["pausar_discagem"] = df_fer["pausar_discagem"].map({True: "✅", False: "❌"})
            st.dataframe(df_fer, use_container_width=True, hide_index=True)
            id_rem = st.number_input("ID para remover (0=nenhum)", min_value=0, step=1)
            if st.button("🗑️ Remover") and id_rem > 0:
                if HolidayService.remover_feriado(int(id_rem)):
                    st.success(f"Feriado id={id_rem} removido.")
                    st.rerun()
                else:
                    st.error("ID não encontrado.")

    # ── Aba 6: Auditoria
    with aba6:
        st.subheader("🔍 Auditoria Operacional")
        if st.button("▶️ Executar auditoria"):
            with st.spinner("Executando..."):
                resultado = AuditService.run_audit()
            st.success("Concluída!")
            st.json(resultado)

        st.divider()
        st.subheader("Agentes sem produção (>30 min logados)")
        df_imp = _q(
            "SELECT a.nome, a.campanha, ROUND(EXTRACT(EPOCH FROM (NOW()-a.login_em))/60) AS min_logado, "
            "COALESCE(l.ligacoes,0) AS ligacoes FROM agents a LEFT JOIN "
            "(SELECT agente_id, COUNT(*) AS ligacoes FROM calls WHERE DATE(iniciada_em)=CURRENT_DATE "
            "GROUP BY agente_id) l ON a.agente_id=l.agente_id "
            "WHERE a.captured_at>=NOW()-INTERVAL '5 minutes' AND LOWER(a.status) NOT IN ('paused','offline') "
            "AND COALESCE(l.ligacoes,0)=0 AND EXTRACT(EPOCH FROM (NOW()-a.login_em))/60>30"
        )
        if df_imp.empty:
            st.success("Nenhum agente improdutivo.")
        else:
            st.warning(f"{len(df_imp)} agente(s) improdutivo(s)")
            st.dataframe(df_imp, use_container_width=True, hide_index=True)

    # ── Aba 7: Inteligência de Discagem
    with aba7:
        st.subheader("🧠 Melhor Janela de Discagem por DDD")
        if DISCAGEM.modelo is None:
            st.info("Modelo ainda não treinado. Rode POST /discagem/treinar ou aguarde o job diário às 02h.")
        else:
            ddd_input = st.text_input("DDD", value="11", max_chars=2)
            if st.button("🔎 Consultar melhores janelas"):
                janelas = DISCAGEM.melhor_janela(ddd_input, top_n=5)
                if janelas:
                    st.dataframe(pd.DataFrame(janelas), use_container_width=True, hide_index=True)
                else:
                    st.warning("Sem previsão disponível para esse DDD.")

    if auto_refresh:
        time.sleep(30)
        st.rerun()
