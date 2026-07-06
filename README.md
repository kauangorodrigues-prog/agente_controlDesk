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
- **alo_analyzer.py** — analisador de qualidade das ligações entregues pela operadora (ALO / NÃO ALO). Classifica cada chamada (ALO REAL, NÃO ALO, URA, CAIXA POSTAL, SECRETÁRIA, MUDO, RUÍDO, OCUPADO, OPERADORA, DISCADOR) combinando transcrição, contexto e metadados (CDR/SIP/AMD), detecta atraso na entrega, falso ALO / falso NÃO ALO, calcula métricas de tempo, score final (0-100) e recomendações. Usa Claude (`claude-opus-4-8`, saída JSON estruturada) quando `ANTHROPIC_API_KEY` está configurada, com **fallback automático para uma heurística offline** — ver seção abaixo.
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

## Analisador de ligações ALO / NÃO ALO

O módulo `control_desk/alo_analyzer.py` avalia **exclusivamente a qualidade da
ligação entregue pela operadora ao discador** (não avalia o operador humano).
Para cada ligação responde às 13 tarefas do prompt-mestre: houve ALO?, grau de
confiança, classificação, justificativa, quem desligou, atraso na entrega e seu
prejuízo, entrega da operadora, indícios de falha, probabilidade de a falha ser
da operadora/discador/agente e evidências — além de métricas de tempo, score
final e recomendações.

Dois modos, com *fallback* transparente:

- **IA (Claude)** — quando o pacote `anthropic` está instalado e
  `ANTHROPIC_API_KEY` está definida (`ALO_USAR_IA=true`, padrão). Usa
  `claude-opus-4-8` com saída estruturada em JSON.
- **Heurística offline** — regras sobre palavras-chave de ALO, marcadores de
  não-ALO e metadados (CDR/SIP/AMD). É o *fallback* automático sem chave, sem
  rede ou em caso de erro da API. Roda sem dependências externas.

Uso via código:

```python
from control_desk.alo_analyzer import ANALISADOR, Ligacao, Turno

lig = Ligacao(
    operadora="Claro", amd="Humano", duracao_total_seg=38,
    tempo_ate_conexao_seg=4.3, tempo_silencio_seg=2.8, transferencia=True,
    turnos=[
        Turno("Cliente", "Alô?", inicio_seg=1.2),
        Turno("Cliente", "Tem alguém aí?", inicio_seg=4.5),
        Turno("Agente", "Boa tarde, falo com a senhora Maria?", inicio_seg=6.0),
    ],
)
resultado = ANALISADOR.analisar(lig)      # respeita ALO_USAR_IA
print(resultado.to_dict())
```

### Integração com o discador (Olos) e persistência

O módulo `control_desk/alo_service.py` liga o analisador aos conectores e ao
banco: puxa CDR + transcrição do Olos (`OlosClient.get_call` /
`get_call_transcription` / `get_calls_para_alo`), mapeia cada registro em uma
`Ligacao` (tolerando variações de nome de campo entre versões da API),
analisa, persiste na tabela `alo_analises` (criada automaticamente) e agrega
estatísticas por classificação e por operadora. Sem banco configurado a análise
ainda roda — apenas não persiste. O scheduler roda o lote a cada 15 minutos
(job `alo`).

### Endpoints da API (modo `python main.py api`)

Todos autenticados via JWT (`Authorization: Bearer <token>`), tag **ALO** em
`/docs`:

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/alo/analisar` | Analisa uma ligação enviada no corpo (metadados + `transcricao` ou `turnos`). |
| `GET`  | `/alo/call/{call_id}` | Puxa a chamada do Olos, analisa e persiste. |
| `POST` | `/alo/processar` | Processa em lote as chamadas recentes (`?desde=YYYY-MM-DD&limite=200`). |
| `GET`  | `/alo/historico` | Últimas análises (`?classificacao=&operadora=&limite=`). |
| `GET`  | `/alo/estatisticas` | Agregados por classificação/operadora (`?dias=1`). |

```bash
curl -X POST http://localhost:8000/alo/analisar \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"operadora":"Claro","amd":"Humano","turnos":[{"falante":"cliente","texto":"Alô","inicio_seg":1.2}]}'
```

No dashboard Streamlit, a aba **📞 ALO** mostra score médio, ALO real, atrasos,
falsos positivos/negativos, distribuição por classificação e qualidade por
operadora, com botão para processar o lote sob demanda.

Testes (offline, determinísticos): `python -m tests.test_alo_analyzer` e
`python -m tests.test_alo_service`.

## web/ — Control Desk IA (helpdesk interno)

Além do agente Python, o repositório inclui em `web/` uma aplicação separada
de service desk de TI (tickets, incidentes, chat com IA, relatórios e
dashboard), construída em React 19 + Vite + Hono + tRPC + Drizzle/MySQL, com
login via OAuth (Kimi). É um produto independente do agente de call center
acima — ver `web/README.md` para detalhes e instruções de execução
(`npm install`, configurar `web/.env` a partir de `web/.env.example` com um
MySQL e credenciais OAuth, depois `npm run dev`, `npm run build` ou
`npm start`).
