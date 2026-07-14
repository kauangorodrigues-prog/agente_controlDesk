# agente_controlDesk

Sistema de Control Desk com IA para operações de cobrança e contact center:
monitoramento em tempo real, ajuste automático de *pacing*, scoring de mailing,
forecast operacional, auditoria contínua e integração com discadores/CRMs
(Olos, EasyCollector e similares). 🤖📊📞

---

## Visão geral

Uma única aplicação (`agente_ia_control_desk.py`) que roda em três modos:

| Modo | Comando | O que faz |
|---|---|---|
| **Standalone** | `python agente_ia_control_desk.py` | Sobe o scheduler e roda todos os jobs em background |
| **API** | `python agente_ia_control_desk.py api` | Expõe a API FastAPI (com o scheduler no lifespan) |
| **Dashboard** | `streamlit run agente_ia_control_desk.py dashboard` | Painel operacional em Streamlit |

### Serviços internos

- **ETLService** — ingere agentes, chamadas, snapshots de campanha, mailing, clientes e promessas do discador/CRM.
- **OccupancyService** — calcula ocupação/ociosidade e detecta pausas longas.
- **PacingService** — ajusta o *pacing* por campanha respeitando guardrails de horário/feriado, com trilha de auditoria.
- **HolidayService** — gestão de feriados (nacionais/estaduais/municipais/empresa) e janelas de discagem.
- **MailingScoreService** — valida CPF/telefone e calcula o score de priorização de discagem.
- **ForecastService** — previsão de volume de chamadas por **ensemble** (sazonal + EWMA + Prophet se disponível), com feature de feriado.
- **PropensityModel** — modelo de propensão a pagar (Gradient Boosting) com treino/inferência, versionamento e rollback; alimenta a priorização do mailing (cai para o heurístico sem modelo).
- **DecisionEngine** — recomendações operacionais por KPI (acelerar/desacelerar, repor mailing), humano no loop.
- **AuditService** — auditoria operacional (agentes improdutivos, campanhas paradas, mailing crítico).
- **ReportService** — relatórios intraday em Excel + resumo por webhook.
- **UpliftService** — mede o ganho de recuperação com grupo de controle (tratado × controle): atribuição determinística e estável por CPF, e relatório com uplift absoluto/relativo e teste de significância (duas proporções).

### Medição de uplift (tratado × controle)

Fluxo para provar ROI com grupo de controle — a métrica central da tese:

1. `POST /uplift/experimentos` — cria o experimento com `pct_controle` (ex.: `0.2`).
2. `POST /uplift/{exp}/atribuir` — atribui a carteira; cada CPF cai de forma **determinística e estável** em `tratado` ou `controle` (hash de `experimento+cpf`), então re-rodar não embaralha os grupos.
3. `GET /uplift/{exp}/relatorio` — compara a taxa de recuperação dos dois grupos e retorna `uplift_abs_pp`, `uplift_rel_pct`, `z`, `p_valor` e `significante_95`.

---

## Requisitos

- Python 3.10+
- PostgreSQL 13+
- (Opcional) Docker + Docker Compose

---

## Início rápido com Docker

```bash
cp .env.example .env          # ajuste as variáveis (senha do banco, tokens, JWT_SECRET_KEY)
docker compose up --build -d  # sobe Postgres (schema+seed aplicados) e a API
docker compose exec api python scripts/create_user.py -u admin -r admin
```

- API: <http://localhost:8000> · Docs interativas: <http://localhost:8000/docs>
- O `db/schema.sql` e o `db/seed_data.sql` são aplicados automaticamente na primeira subida do volume do Postgres.

---

## Instalação manual

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # ajuste as variáveis

# Crie o schema e (opcionalmente) o seed de exemplo:
export DATABASE_URL="postgresql://postgres:senha@localhost:5432/control_desk"
psql "$DATABASE_URL" -f db/schema.sql
psql "$DATABASE_URL" -f db/seed_data.sql   # opcional

# Cadastre o primeiro usuário da API (necessário para autenticar):
python scripts/create_user.py --username admin --role admin
```

### Executando

```bash
python agente_ia_control_desk.py            # standalone (scheduler)
python agente_ia_control_desk.py api        # API FastAPI  -> :8000
streamlit run agente_ia_control_desk.py dashboard   # dashboard -> :8501
```

> Há um `Makefile` com atalhos: `make install`, `make schema`, `make api`,
> `make dashboard`, `make create-user`, `make test`, `make docker-up`.

---

## Autenticação

A API usa JWT (OAuth2 *password flow*). Obtenha um token e use-o como *bearer*:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=SUASENHA" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8000/ocupacao -H "Authorization: Bearer $TOKEN"
```

Rotas de escrita de feriados exigem `role=admin`.

### Principais endpoints

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/token` | Login (retorna JWT) |
| GET  | `/` , `/metrics` | Health simples e métricas Prometheus |
| GET  | `/health`, `/health/{database,jobs,apis,ia}` | Health checks detalhados (públicos) |
| POST | `/etl/run` | Dispara o ETL |
| GET  | `/ocupacao`, `/ocupacao/campanhas` | Ocupação em tempo real |
| POST | `/pacing/ajustar` · GET `/pacing/historico` | Pacing e auditoria |
| GET  | `/mailing/top` · POST `/mailing/processar` | Mailing priorizado |
| GET/POST/DELETE | `/feriados...` | Gestão de feriados |
| GET  | `/forecast` · POST `/forecast/gerar` | Previsão de volume |
| POST | `/auditoria/executar` | Auditoria operacional |
| GET  | `/alertas` | Histórico de alertas |
| GET/POST | `/uplift/experimentos` | Lista/cria experimentos de uplift |
| POST | `/uplift/{exp}/atribuir` | Atribui carteira a tratado/controle |
| GET  | `/uplift/{exp}/relatorio` | Relatório de uplift (tratado × controle) |

---

## Jobs agendados

| Job | Frequência |
|---|---|
| ETL | a cada 5 min |
| Ocupação | a cada 1 min |
| Pacing | a cada 2 min |
| Mailing score | a cada 1 h |
| Auditoria | a cada 30 min |
| Relatório intraday | a cada hora cheia |
| Forecast | 07h e 13h |
| Retomada pós-feriado | 07h55 |
| Sync feriados nacionais | 01/jan 00h05 |

Fuso: `America/Sao_Paulo`.

---

## Testes

```bash
pip install pytest
pytest -q
```

Os testes cobrem a lógica pura (validação de CPF/telefone, score de mailing,
cálculo de pacing) e não dependem de banco de dados.

---

## Estrutura do projeto

```
.
├── agente_ia_control_desk.py   # fachada: entrypoints + reexporta a API pública
├── app/                        # pacote modular (Fase 6, extração incremental)
│   ├── config.py               #   Config, CFG
│   ├── core/resilience.py      #   timeout, retry, circuit breaker
│   ├── core/cache.py           #   MemoryCache/RedisCache, cache_get_or_set
│   ├── core/database.py        #   engine/réplica, get_db, executar_query/comando
│   └── utils/validators.py     #   CPF/telefone/tempo (puro)
├── celery_app.py               # worker Celery opcional (Fase 3)
├── .github/workflows/ci.yml    # CI (pytest a cada push/PR)
├── db/
│   ├── schema.sql              # DDL idempotente (todas as tabelas)
│   └── seed_data.sql           # dados de exemplo
├── scripts/
│   └── create_user.py          # cadastro de usuários da API (bcrypt)
├── tests/
│   ├── test_core.py            # testes das funções puras
│   ├── test_config_security.py # validação de segurança + build do app
│   ├── test_uplift.py          # estatística e atribuição de uplift
│   ├── test_observability.py   # logging JSON, registro de jobs, health
│   ├── test_resilience.py      # retry, circuit breaker, timeout, DLQ
│   ├── test_etl.py             # UPSERT idempotente, dedup, watermark
│   ├── test_cache.py           # cache TTL, get_or_set, invalidação
│   ├── test_queue.py           # fila de prioridade, execução sync/enfileirada
│   ├── test_db.py              # read replica, paginação, streaming, ETL paralelo
│   ├── test_ia.py              # propensão, decisão, ensemble de forecast
│   └── test_app_package.py     # layout modular (Fase 6) + fachada
├── docs/
│   └── estrategia-cobra-ai.md  # documento estratégico
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── Makefile
```

---

## Configuração

Todas as configurações vêm de variáveis de ambiente (ver `.env.example`):
banco, tokens de discador/cobrador, webhook/e-mail de alertas, segredo JWT,
CORS, limites operacionais e guardrails de pacing.

**Segurança em produção:** com `AMBIENTE=production`, o app faz uma validação
no startup e **se recusa a subir** se `JWT_SECRET_KEY` ou `POSTGRES_PASSWORD`
ainda estiverem com os valores padrão, ou avisa se o CORS estiver liberado
para todas as origens. Em desenvolvimento essas pendências viram apenas
`WARNING` no log. Defina `CORS_ORIGINS` com os domínios do seu frontend em
produção (em vez de `*`).

## Observabilidade (Enterprise)

- **Health checks** — `GET /health` (visão geral: banco, scheduler, jobs, CPU/RAM/threads), além de `/health/database`, `/health/jobs` (estado, última execução, tempo médio, falhas, taxa de sucesso por job), `/health/apis` (reachability do discador/cobrador) e `/health/ia` (forecast + scorer). São públicos, próprios para *liveness/readiness*.
- **Métricas Prometheus** — `GET /metrics` inclui `cd_requests_total`, `cd_job_runs_total{job,status}` e `cd_job_duration_seconds`. Os jobs são instrumentados no próprio wrapper `_safe_run` (sem alterar a lógica dos serviços).
- **Logs estruturados** — defina `LOG_FORMAT=json` para logs em JSON com `correlation_id` (e campos extras como `job_id`, `campaign_id`). O padrão (`plain`) mantém o formato legível de sempre. Toda requisição HTTP recebe/gera um `X-Request-ID`, propagado aos logs e devolvido no cabeçalho da resposta.

> Tudo acima é **aditivo e retrocompatível**: nenhum endpoint ou comportamento existente mudou. Faz parte da Fase 1 da evolução Enterprise (observabilidade e prontidão para produção).

## Resiliência de jobs (Fase 2)

Toolkit reutilizável, aplicado ao wrapper `_safe_run` que já envolve todos os jobs:

- **Timeout** (`JOB_TIMEOUT_SEG`, padrão 900s) — nenhum job fica preso indefinidamente. Limitação honesta: Python não mata threads à força; em timeout paramos de esperar e sinalizamos.
- **Retry exponencial** (`retry_call`) — desligado por padrão (`JOB_MAX_RETRIES=0`) porque nem todo job é idempotente (o ETL atual faz `append`); habilite por job quando for seguro. O I/O HTTP também pode usá-lo.
- **Circuit Breaker** (`CircuitBreaker`, CLOSED→OPEN→HALF_OPEN) para proteger dependências instáveis.
- **Dead Letter Queue** — falha terminal de job vai para a tabela `dead_letter_queue`, dispara alerta `CRITICO` (throttled) e loga: **falha → DLQ → webhook → log**. Inspecione em `GET /dlq` (autenticado) e veja o total em `/health/jobs`.

Configurável via `.env` (`JOB_TIMEOUT_SEG`, `JOB_MAX_RETRIES`, `RETRY_BASE_SEG`, `CB_FAIL_THRESHOLD`, `CB_RESET_SEG`).

## ETL idempotente (Melhoria 1)

- **UPSERT idempotente** — para tabelas com chave natural (`calls`→`call_id`, `customers`→`cpf`, `collector_promessas`→`promessa_id`), o ETL faz `INSERT … ON CONFLICT DO UPDATE` via `PostgresRepository` (Repository Pattern), com **dedup dentro do lote**. Nunca insere o mesmo registro duas vezes.
- **Fallback seguro** — se o índice único ainda não existir (base legada), cai automaticamente para o `append` de antes e avisa nos logs. **Sem perda de dados, sem regressão.** Habilite a idempotência rodando `db/schema.sql` (cria os índices únicos).
- **Watermark / CDC** — a ingestão de `calls` é **incremental**: busca só registros novos desde o último `iniciada_em` processado (tabela `etl_watermark`), com *fallback* para D-1.
- **Retenção de histórico** — `ETL.compactar_snapshots` remove snapshots antigos (job diário 03:20), **desligado por padrão** (`ETL_RETENCAO_DIAS=0`).
- **Segurança** — identificadores SQL (tabela/coluna) são validados por regex contra injeção antes de compor o UPSERT.

Configurável via `.env` (`ETL_UPSERT`, `ETL_RETENCAO_DIAS`).

## Filas & Cache (Fase 3)

**Degradação graciosa:** sem `REDIS_URL`/`CELERY_BROKER_URL`, a app usa **cache em memória** e **fila de prioridade in-process** — funciona sem infra externa. Definir as variáveis habilita Redis e Celery sem mudar código.

- **Cache (Melhoria 13)** — `CACHE` com backend Redis ou memória (fallback). Aplicado a leituras repetidas: `campaign_config` (TTL curto no ciclo de pacing) e listagem de `feriados` (com **invalidação por versão** ao criar/remover). Helper `cache_get_or_set`.
- **Filas (Melhoria 3)** — cada job pode rodar **imediatamente**, **via fila** (com prioridade `CRITICAL|HIGH|NORMAL|LOW`), **manualmente** (API) ou **por scheduler**. Backend in-process por padrão; roteia para **Celery** (Redis/RabbitMQ) quando `CELERY_BROKER_URL` está definido (`celery_app.py` + serviço `worker` no compose). Os jobs reutilizam o wrapper resiliente `_safe_run` (timeout/retry/DLQ/métricas).

Endpoints: `GET /jobs` (lista + estado da fila), `POST /jobs/{nome}/executar` (sync), `POST /jobs/{nome}/enfileirar?prioridade=HIGH`.

Configurável via `.env` (`REDIS_URL`, `CACHE_TTL_SEG`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `QUEUE_WORKERS`). O `docker compose up` sobe também **Redis** e um **worker Celery**.

## Banco & paralelismo (Fase 4)

Endurecimento do acesso a dados e paralelização do I/O, tudo com fallback para o comportamento atual.

- **Read replica** — `DATABASE_REPLICA_URL` roteia leituras (`executar_query`, `ler_dataframe`, ocupação) para a réplica; sem ela, tudo usa a primária (`engine_leitura is engine`). Escritas sempre na primária.
- **Pool & statement timeout** — `POSTGRES_POOL_SIZE`/`POSTGRES_MAX_OVERFLOW` e `DB_STATEMENT_TIMEOUT_MS` (aborta consultas presas).
- **Retry de leitura** — `executar_query` reexecuta **apenas em desconexão real** (`connection_invalidated`), nunca em `statement_timeout`/erro de query (evitaria só ampliar carga).
- **Repository** — `PostgresRepository` ganha `paginar` (LIMIT/OFFSET com detecção de próxima página), `stream_query` (cursor server-side para grandes volumes) e `bulk_insert`. `/dlq` já é paginado (`?pagina=&por_pagina=`).
- **ETL paralelo (M2)** — a coleta HTTP das 6 fontes roda em paralelo (`ETL_PARALELO`), reduzindo o tempo de parede do ETL; a persistência segue sequencial e isolada por fonte.

> Nota de escopo: **não** foi feita uma reescrita async total (aiohttp/async SQLAlchemy). O design síncrono (APScheduler, `pd.read_sql`, `to_sql`, rotas sync que já rodam em threadpool) é preservado; o ganho de tempo vem da paralelização do I/O onde importa, sem risco de regressão.

Configurável via `.env` (`POSTGRES_POOL_SIZE`, `POSTGRES_MAX_OVERFLOW`, `DB_STATEMENT_TIMEOUT_MS`, `DB_READ_RETRY`, `DATABASE_REPLICA_URL`, `ETL_PARALELO`).

## IA preditiva (Fase 5)

Degradação graciosa: sem `scikit-learn` (ou sem modelo ativo), o scoring usa o heurístico e o forecast usa sazonal+EWMA — nada quebra.

- **Modelo de propensão a pagar (M10)** — `PropensityModel` treina um Gradient Boosting sobre o histórico (rótulo = recuperado/tem acordo), com **versionamento** (tabela `model_registry` + artefatos `.joblib` em `IA_MODELO_DIR`) e **rollback** (ativar uma versão anterior). A inferência entra no `MailingScoreService`: quando há modelo ativo, o mailing é ordenado por `score_final` (propensão); senão, pelo `score_discagem` heurístico (preservado). Endpoints: `GET /ia/status`, `POST /ia/treinar`, `GET /ia/modelos`, `POST /ia/modelos/{versao}/ativar`.
- **Forecast ensemble (M11)** — `ForecastService` combina **sazonal + EWMA + Prophet** (se instalado), com feature de **feriado**; persiste as colunas base (schema estável) e retorna também `metodo`/`feriado`.
- **Motor de decisão (M12)** — `GET /ia/decisoes` recomenda, por KPIs, **acelerar/desacelerar** pacing, **repor mailing** e priorizações (humano no loop — recomenda, não aplica).

Treino re-executado semanalmente (domingo 04:10) e disponível como job (`ia_treino`) na fila. Configurável via `.env` (`IA_MODELO_DIR`, `IA_MIN_AMOSTRAS`).

## Arquitetura modular (Fase 6)

Refatoração **incremental e retrocompatível** do módulo único para o pacote `app/` (SOLID, separação de responsabilidades). `agente_ia_control_desk.py` permanece como **fachada** que reexporta a API pública — entrypoints (`python … api`, `uvicorn …:app`), `celery_app.py`, `scripts/` e todos os testes seguem funcionando sem alteração.

Já extraídos (camadas de menor acoplamento, com dependências apenas "para baixo"): `app/config.py` (Config/CFG), `app/core/resilience.py` (timeout/retry/circuit breaker), `app/core/cache.py` (cache com fallback), `app/core/database.py` (engine/réplica, `get_db`, `executar_query/comando`, `ler_dataframe`) e `app/utils/validators.py` (CPF/telefone/tempo, puro). A fachada reexporta os **mesmos objetos** (CFG, CACHE, engine) — estado compartilhado preservado. As camadas seguintes (repositórios, integrações, serviços, IA, API) são movidas nos próximos passos, sempre mantendo a suíte verde e a fachada estável.

## Integração contínua

O workflow `.github/workflows/ci.yml` roda `pytest` a cada push/PR
(instalando `requirements.txt`), validando a lógica pura, a construção do
app FastAPI e a validação de segurança de configuração.
