-- ============================================================
-- Agente IA Control Desk — Schema PostgreSQL
-- ============================================================
-- Idempotente: pode ser executado várias vezes com segurança
-- (tudo usa IF NOT EXISTS). Em bancos já existentes, tabelas
-- presentes não são alteradas.
--
-- Aplicar:  psql "$DATABASE_URL" -f db/schema.sql
-- ============================================================


-- ------------------------------------------------------------
-- 1. Tabelas de configuração / referência (OBRIGATÓRIAS)
-- ------------------------------------------------------------
-- Escritas/lidas via SQL cru pela aplicação. Precisam existir
-- ANTES de subir o sistema, senão autenticação, feriados,
-- auditoria de pacing e persistência de alertas falham.

CREATE TABLE IF NOT EXISTS api_users (
    id          SERIAL PRIMARY KEY,
    username    TEXT    NOT NULL UNIQUE,
    hashed_pw   TEXT    NOT NULL,
    role        TEXT    NOT NULL DEFAULT 'operador',   -- 'admin' | 'operador'
    ativo       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS campaign_config (
    id                SERIAL PRIMARY KEY,
    campanha_id       TEXT NOT NULL UNIQUE,
    campanha_nome     TEXT,
    ativo             BOOLEAN NOT NULL DEFAULT TRUE,
    hora_inicio       TEXT DEFAULT '08:00',
    hora_fim          TEXT DEFAULT '21:00',
    hora_fim_sabado   TEXT DEFAULT '16:00',
    permitir_domingo  BOOLEAN NOT NULL DEFAULT FALSE,
    uf_restricao      VARCHAR(2),
    pacing_min        DOUBLE PRECISION DEFAULT 1.0,
    pacing_max        DOUBLE PRECISION DEFAULT 8.0,
    pausar_feriados   BOOLEAN NOT NULL DEFAULT TRUE,
    atualizado_em     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feriados (
    id               SERIAL PRIMARY KEY,
    data             DATE NOT NULL,
    nome             TEXT NOT NULL,
    tipo             TEXT NOT NULL DEFAULT 'EMPRESA',  -- NACIONAL|ESTADUAL|MUNICIPAL|EMPRESA
    uf               VARCHAR(2),
    municipio        TEXT,
    pausar_mailing   BOOLEAN NOT NULL DEFAULT TRUE,
    pausar_discagem  BOOLEAN NOT NULL DEFAULT TRUE,
    pacing_especial  DOUBLE PRECISION,
    observacao       TEXT,
    criado_por       TEXT DEFAULT 'USUARIO',
    criado_em        TIMESTAMP NOT NULL DEFAULT NOW()
);
-- Índice único usado pelo upsert de HolidayService.adicionar_feriado().
-- Usa COALESCE porque uf/municipio são NULL em feriados nacionais e o
-- Postgres trata NULLs como DISTINTOS num UNIQUE comum — o que permitiria
-- duplicatas a cada sincronização anual. Com COALESCE(...,'') o conflito
-- é detectado corretamente.
CREATE UNIQUE INDEX IF NOT EXISTS uq_feriado
    ON feriados (data, tipo, COALESCE(uf, ''), COALESCE(municipio, ''));
CREATE INDEX IF NOT EXISTS idx_feriados_data ON feriados (data);

CREATE TABLE IF NOT EXISTS pacing_audit_log (
    id               SERIAL PRIMARY KEY,
    campanha_id      TEXT,
    campanha_nome    TEXT,
    pacing_anterior  DOUBLE PRECISION,
    pacing_novo      DOUBLE PRECISION,
    motivo           TEXT,
    ocupacao_pct     DOUBLE PRECISION,
    bloqueado        BOOLEAN NOT NULL DEFAULT FALSE,
    motivo_bloqueio  TEXT,
    ts               TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pacing_audit_ts   ON pacing_audit_log (ts);
CREATE INDEX IF NOT EXISTS idx_pacing_audit_camp ON pacing_audit_log (campanha_id);

CREATE TABLE IF NOT EXISTS alert_log (
    id         SERIAL PRIMARY KEY,
    chave      TEXT,
    nivel      TEXT,
    mensagem   TEXT,
    canal      TEXT DEFAULT 'webhook',
    enviado    BOOLEAN NOT NULL DEFAULT FALSE,
    ts         TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alert_ts ON alert_log (ts);


-- ------------------------------------------------------------
-- 2. Tabela analítica gerada pela aplicação
-- ------------------------------------------------------------
-- forecast_calls recebe append via pandas.to_sql. As colunas
-- abaixo casam exatamente com o DataFrame do ForecastService.

CREATE TABLE IF NOT EXISTS forecast_calls (
    id                   SERIAL PRIMARY KEY,
    ds                   TIMESTAMP,
    yhat                 DOUBLE PRECISION,
    yhat_lower           DOUBLE PRECISION,
    yhat_upper           DOUBLE PRECISION,
    agentes_necessarios  INTEGER,
    gerado_em            TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_forecast_gerado ON forecast_calls (gerado_em);


-- ------------------------------------------------------------
-- 3. Tabelas-espelho do ETL (criadas pelo ETL se ausentes)
-- ------------------------------------------------------------
-- O ETLService usa pandas.to_sql(..., if_exists='append'), que
-- cria estas tabelas na primeira execução com as colunas
-- retornadas pela API do seu discador/CRM. As definições abaixo
-- garantem tipos corretos e os índices exigidos pelas consultas
-- por janela de tempo (captured_at / iniciada_em).
--
-- IMPORTANTE: se a sua API retornar colunas ADICIONAIS, o append
-- do pandas falha até que elas existam aqui — acrescente-as.
-- (Observação: o ETL grava também a coluna etl_ts; as consultas
--  filtram por captured_at, que deve vir da própria API de origem.)

-- captured_at tem DEFAULT NOW(): quando a API de origem não fornece a
-- coluna, o instante da ingestão preenche o filtro por janela de tempo
-- (as consultas de ocupação/auditoria/mailing filtram por captured_at).
CREATE TABLE IF NOT EXISTS agents (
    agente_id     TEXT,
    nome          TEXT,
    status        TEXT,
    campanha      TEXT,
    login_em      TIMESTAMP,
    pausa_inicio  TIMESTAMP,
    captured_at   TIMESTAMP DEFAULT NOW(),
    etl_ts        TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agents_captured ON agents (captured_at);
CREATE INDEX IF NOT EXISTS idx_agents_agente   ON agents (agente_id);

CREATE TABLE IF NOT EXISTS calls (
    call_id        TEXT,
    status         TEXT,
    telefone       TEXT,
    ddd            TEXT,
    agente_id      TEXT,
    campanha_id    TEXT,
    tipo_resultado TEXT,
    iniciada_em    TIMESTAMP,
    etl_ts         TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_calls_iniciada ON calls (iniciada_em);
CREATE INDEX IF NOT EXISTS idx_calls_agente   ON calls (agente_id);
CREATE INDEX IF NOT EXISTS idx_calls_camp     ON calls (campanha_id);

CREATE TABLE IF NOT EXISTS campaign_snapshot (
    campanha_id          TEXT,
    campanha             TEXT,
    status               TEXT,
    pacing_atual         DOUBLE PRECISION,
    mailing_restante_pct DOUBLE PRECISION,
    ocupacao_pct         DOUBLE PRECISION,
    ociosidade_pct       DOUBLE PRECISION,
    abandono_pct         DOUBLE PRECISION,
    agentes_logados      INTEGER,
    tipo_resultado       TEXT,
    captured_at          TIMESTAMP DEFAULT NOW(),
    etl_ts               TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_snapshot_captured ON campaign_snapshot (captured_at);
CREATE INDEX IF NOT EXISTS idx_snapshot_camp     ON campaign_snapshot (campanha_id);

CREATE TABLE IF NOT EXISTS mailing_status (
    campanha_id          TEXT,
    campanha             TEXT,
    mailing_restante_pct DOUBLE PRECISION,
    captured_at          TIMESTAMP DEFAULT NOW(),
    etl_ts               TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mailing_status_captured ON mailing_status (captured_at);

CREATE TABLE IF NOT EXISTS customers (
    cpf                TEXT,
    telefone           TEXT,
    telefone_limpo     TEXT,
    ddd                TEXT,
    ativo              BOOLEAN DEFAULT TRUE,
    days_delay         DOUBLE PRECISION,
    previous_cpc       DOUBLE PRECISION,
    phone_score        DOUBLE PRECISION,
    faixa_atraso_dias  INTEGER,
    melhor_hora_inicio INTEGER,
    melhor_hora_fim    INTEGER,
    promessa_quebrada  BOOLEAN,
    captured_at        TIMESTAMP DEFAULT NOW(),
    etl_ts             TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_customers_cpf ON customers (cpf);

CREATE TABLE IF NOT EXISTS collector_promessas (
    promessa_id    TEXT,
    cpf            TEXT,
    campanha_id    TEXT,
    valor          DOUBLE PRECISION,
    data_promessa  DATE,
    status         TEXT,
    etl_ts         TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_promessas_cpf ON collector_promessas (cpf);


-- NOTA: a tabela `mailing_scored` é totalmente gerenciada pela
-- aplicação (MailingScoreService usa to_sql if_exists='replace',
-- recriando-a a cada execução), portanto não é definida aqui.


-- ------------------------------------------------------------
-- 4. Uplift (medição tratado × controle)
-- ------------------------------------------------------------
-- Prova o ganho de recuperação de um experimento comparando o grupo
-- tratado (recebe a priorização) com o grupo de controle.

CREATE TABLE IF NOT EXISTS uplift_experimentos (
    id            SERIAL PRIMARY KEY,
    nome          TEXT NOT NULL UNIQUE,
    descricao     TEXT,
    pct_controle  DOUBLE PRECISION NOT NULL DEFAULT 0.2,  -- fração no controle (0..1)
    data_inicio   DATE,
    data_fim      DATE,
    ativo         BOOLEAN NOT NULL DEFAULT TRUE,
    criado_por    TEXT DEFAULT 'API',
    criado_em     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS uplift_atribuicoes (
    id            SERIAL PRIMARY KEY,
    experimento   TEXT NOT NULL,
    cpf           TEXT NOT NULL,
    campanha_id   TEXT,
    grupo         TEXT NOT NULL,           -- 'tratado' | 'controle'
    atribuido_em  TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_uplift_atrib UNIQUE (experimento, cpf)
);
CREATE INDEX IF NOT EXISTS idx_uplift_atrib_exp ON uplift_atribuicoes (experimento);
CREATE INDEX IF NOT EXISTS idx_uplift_atrib_cpf ON uplift_atribuicoes (cpf);


-- ------------------------------------------------------------
-- 5. Dead Letter Queue (resiliência de jobs — Fase 2)
-- ------------------------------------------------------------
-- Recebe falhas terminais de jobs (após retries/timeout) para
-- inspeção e reprocessamento manual: falha → DLQ → webhook → log.

CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id              SERIAL PRIMARY KEY,
    origem          TEXT NOT NULL,       -- nome do job/operação
    correlation_id  TEXT,
    erro            TEXT,
    payload         TEXT,
    tentativas      INTEGER,
    criado_em       TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dlq_criado ON dead_letter_queue (criado_em);
CREATE INDEX IF NOT EXISTS idx_dlq_origem ON dead_letter_queue (origem);
