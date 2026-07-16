# Conformidade LGPD — Agente IA Control Desk

Este documento descreve os controles de proteção de dados pessoais implementados
no sistema, mapeados aos dispositivos da **Lei nº 13.709/2018 (LGPD)**. O sistema
trata dados pessoais de titulares em cobrança/call center (CPF, nome, telefone,
e-mail), o que exige os controles abaixo.

Implementação: módulo [`lgpd.py`](../lgpd.py), tabelas em
[`sql/lgpd_tables.sql`](../sql/lgpd_tables.sql) e endpoints `/lgpd/*` em
`projeto_git.py`.

## Mapa artigo → implementação

| Dispositivo LGPD | Controle no sistema |
|---|---|
| Art. 6º (necessidade, segurança) | Mascaramento de PII nas respostas (`/mailing/top` mascara por padrão); redação de CPF/telefone/e-mail nos logs (`RedactingFilter`). |
| Arts. 7º e 10 (bases legais) | Registro de base legal por campanha/finalidade: `GET/POST /lgpd/base-legal`, tabela `lgpd_base_legal`. |
| Art. 18, I e II (confirmação e acesso) | `GET /lgpd/titular/confirmacao?cpf=` — retorna existência de tratamento e dados **mascarados**. |
| Art. 18, V (portabilidade) | `GET /lgpd/titular/dados?cpf=` — exportação dos dados reais (restrito a admin, com registro de acesso). |
| Art. 18, IV (anonimização) | `POST /lgpd/titular/anonimizar` — remove a identificabilidade preservando a linha para estatística. |
| Art. 18, VI (eliminação) | `POST /lgpd/titular/eliminar` — apaga os registros do titular nas fontes configuradas. |
| Art. 37 (registro das operações) | Toda operação sobre dado pessoal é gravada em `lgpd_acesso_log` (com **hash** do CPF, nunca em claro). |
| Arts. 15 e 16 (término/descarte) | Política de retenção: `POST /lgpd/retencao/aplicar`, função `aplicar_retencao`. |

## Princípios aplicados

- **Minimização / pseudonimização**: as trilhas guardam apenas o `SHA-256` salgado
  do CPF (`LGPD_HASH_SALT`), nunca o CPF em claro.
- **Necessidade / need-to-know**: PII vem mascarada por padrão. A exposição em claro
  (`/mailing/top?desmascarar=true`) exige perfil `admin` e é registrada em
  `lgpd_acesso_log`.
- **Segurança de identificadores**: nomes de tabelas/colunas das fontes de PII são
  validados contra `^[A-Za-z_][A-Za-z0-9_]*$` antes de compor SQL, evitando injeção.
- **Prestação de contas**: anonimização, eliminação e retenção são registradas no
  livro-razão `lgpd_titular_evento`; requisições de titular recebem protocolo em
  `lgpd_requisicao_titular`.

## Configuração (variáveis de ambiente)

| Variável | Padrão | Descrição |
|---|---|---|
| `LGPD_HASH_SALT` | *(vazio)* | Salt do hash de CPF. **Defina em produção.** |
| `LGPD_RETENCAO_DIAS` | `1825` | Prazo de retenção (dias) antes do descarte. Ajuste à política jurídica. |
| `LGPD_FONTES_PII` | *(padrão do módulo)* | JSON com as fontes de dados pessoais. |

Exemplo de `LGPD_FONTES_PII`:

```json
[
  {"tabela": "mailing_scored", "coluna_cpf": "cpf",
   "colunas_pii": ["cpf", "nome", "telefone", "email"], "coluna_data": "captured_at"}
]
```

Se não configurado, usa `FONTES_PII_PADRAO` (`mailing_scored`). **Ajuste ao schema
real** — as operações de titular/retenção só alcançam as fontes listadas aqui.

## Instalação

```bash
psql "$DATABASE_URL" -f sql/lgpd_tables.sql
export LGPD_HASH_SALT="<segredo-forte>"
```

## Runbook — requisição de titular (art. 18)

1. **Confirmação/acesso**: `GET /lgpd/titular/confirmacao?cpf=<cpf>`.
2. **Portabilidade**: `GET /lgpd/titular/dados?cpf=<cpf>` (admin).
3. **Anonimização**: `POST /lgpd/titular/anonimizar` `{"cpf":"...","justificativa":"..."}`.
4. **Eliminação**: `POST /lgpd/titular/eliminar` `{"cpf":"...","justificativa":"..."}`.

Cada operação retorna um `protocolo` e fica registrada nas trilhas. A retenção pode
ser executada sob demanda via `POST /lgpd/retencao/aplicar` ou agendada como job.

> **Observação jurídica**: eliminação pode conflitar com a guarda obrigatória para
> defesa em processo (art. 16, I e III). Avalie com o jurídico antes de eliminar;
> em geral a **anonimização** é preferível quando há dever de guarda.
