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
- **ForecastService** — previsão de volume de chamadas (Prophet, com fallback estatístico).
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
├── agente_ia_control_desk.py   # aplicação (API + scheduler + dashboard + serviços)
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
│   └── test_observability.py   # logging JSON, registro de jobs, health
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

## Integração contínua

O workflow `.github/workflows/ci.yml` roda `pytest` a cada push/PR
(instalando `requirements.txt`), validando a lógica pura, a construção do
app FastAPI e a validação de segurança de configuração.
