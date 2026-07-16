-- ============================================================================
-- Estruturas de conformidade LGPD (Lei nº 13.709/2018) — PostgreSQL
-- Executar uma vez no banco da aplicação (control_desk).
-- ============================================================================

-- Registro da base legal por campanha/finalidade (arts. 7º e 10).
CREATE TABLE IF NOT EXISTS lgpd_base_legal (
    id          SERIAL PRIMARY KEY,
    campanha    TEXT        NOT NULL,
    finalidade  TEXT        NOT NULL,
    base_legal  TEXT        NOT NULL,
    observacao  TEXT,
    vigente     BOOLEAN     NOT NULL DEFAULT TRUE,
    criado_por  TEXT,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_base_legal_campanha_finalidade UNIQUE (campanha, finalidade)
);

-- Registro das operações de acesso a dados pessoais (art. 37).
-- Guarda apenas o hash do CPF (pseudonimização) — nunca o CPF em claro.
CREATE TABLE IF NOT EXISTS lgpd_acesso_log (
    id            BIGSERIAL   PRIMARY KEY,
    ts            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    usuario       TEXT,
    acao          TEXT        NOT NULL,
    recurso       TEXT,
    cpf_hash      TEXT,
    justificativa TEXT,
    ip            TEXT
);
CREATE INDEX IF NOT EXISTS ix_lgpd_acesso_ts       ON lgpd_acesso_log (ts DESC);
CREATE INDEX IF NOT EXISTS ix_lgpd_acesso_cpf_hash ON lgpd_acesso_log (cpf_hash);

-- Protocolo/rastreio das requisições do titular (art. 18).
CREATE TABLE IF NOT EXISTS lgpd_requisicao_titular (
    id            BIGSERIAL   PRIMARY KEY,
    protocolo     TEXT        NOT NULL UNIQUE,
    tipo          TEXT        NOT NULL,   -- confirmacao | acesso | portabilidade | anonimizacao | eliminacao | correcao
    cpf_hash      TEXT,
    status        TEXT        NOT NULL DEFAULT 'recebida',  -- recebida | em_andamento | concluida | negada
    solicitado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atendido_em   TIMESTAMPTZ,
    solicitante   TEXT,
    observacao    TEXT
);
CREATE INDEX IF NOT EXISTS ix_lgpd_req_cpf_hash ON lgpd_requisicao_titular (cpf_hash);
CREATE INDEX IF NOT EXISTS ix_lgpd_req_status   ON lgpd_requisicao_titular (status);

-- Livro-razão de eventos irreversíveis (anonimização / eliminação / retenção).
CREATE TABLE IF NOT EXISTS lgpd_titular_evento (
    id            BIGSERIAL   PRIMARY KEY,
    ts            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tipo          TEXT        NOT NULL,   -- anonimizacao | eliminacao | retencao
    cpf_hash      TEXT,
    fontes        JSONB,
    executado_por TEXT
);
CREATE INDEX IF NOT EXISTS ix_lgpd_evento_ts  ON lgpd_titular_evento (ts DESC);
CREATE INDEX IF NOT EXISTS ix_lgpd_evento_cpf ON lgpd_titular_evento (cpf_hash);
