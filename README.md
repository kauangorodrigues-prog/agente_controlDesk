# agente_controlDesk
Sistema de Control Desk com IA para operações de cobrança e contact center, oferecendo monitoramento em tempo real, ajuste automático de pacing, scoring de mailing, forecast operacional, auditoria contínua e integração com Olos e EasyCollector. 🤖📊📞

## Arquitetura

O agente é um pacote Python (`control_desk/`) com três formas de execução:

| Modo | Comando | Descrição |
|---|---|---|
| Standalone | `python main.py` | Scheduler interno (APScheduler) rodando ETL, monitoramento de ociosidade, pacing, mailing, auditoria, relatórios e forecast em background. Expõe health check em `http://localhost:8080/health`. |
| API | `python main.py api` | Sobe a API REST (FastAPI + JWT) na porta `:8000`, com documentação interativa em `/docs`. O scheduler roda embutido no ciclo de vida da API. |
| Dashboard | `streamlit run dashboard_app.py` | Painel visual (Streamlit) com abas de tempo real, campanhas, log de pacing, forecast, feriados, auditoria e inteligência de discagem. |

### Principais módulos (`control_desk/`)

- **config.py** — configuração central via `.env` (banco, Olos, EasyCollector, alertas, JWT, guardrails de pacing).
- **db.py** — engine SQLAlchemy com `pool_pre_ping`/`pool_recycle`.
- **alerts.py** — alertas Teams/Email com throttle por chave e fila de reenvio (dead letter queue).
- **circuit_breaker.py** / **clients.py** — clientes do Olos e do EasyCollector com retry, circuit breaker e cache de snapshot (TTL).
- **etl.py** — ingestão periódica de agentes, chamadas, campanhas, mailing e carteira.
- **occupancy.py** — monitor de ociosidade/pausas em tempo real, com alertas automáticos.
- **holidays.py** / **pacing.py** — guardrails de horário/feriado e ajuste automático de pacing por campanha.
- **mailing.py** — validação de CPF/telefone e scoring de priorização de discagem.
- **discagem.py** — modelo de ML (GradientBoosting) que aprende a melhor janela de horário/dia por DDD para maximizar CPC, persistido em disco.
- **audit.py** — auditoria operacional (agentes improdutivos, campanhas paradas, mailing crítico).
- **reports.py** — relatório intraday em Excel (campanhas, produção por operador, timeline hora-a-hora) + envio por e-mail.
- **forecast.py** — previsão de volume de chamadas (Prophet, com fallback automático por média móvel).
- **scheduler.py** / **health.py** — orquestração dos jobs e health check HTTP.
- **api.py** / **dashboard.py** — API FastAPI e dashboard Streamlit (opcionais).

## Como executar

```bash
pip install -r requirements.txt
cp .env.example .env   # preencha com suas credenciais reais
python main.py          # modo standalone
# ou
python main.py api      # API REST em :8000
# ou
streamlit run dashboard_app.py   # dashboard visual
```

## web/ — Control Desk IA (helpdesk interno)

Além do agente Python, o repositório inclui em `web/` uma aplicação separada
de service desk de TI (tickets, incidentes, chat com IA, relatórios e
dashboard), construída em React 19 + Vite + Hono + tRPC + Drizzle/MySQL, com
login via OAuth (Kimi). É um produto independente do agente de call center
acima — ver `web/README.md` para detalhes e instruções de execução
(`npm install`, configurar `web/.env` a partir de `web/.env.example` com um
MySQL e credenciais OAuth, depois `npm run dev`, `npm run build` ou
`npm start`).
