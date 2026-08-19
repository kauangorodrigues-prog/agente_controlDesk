# Conformidade LGPD (Lei 13.709/2018)

Este documento mapeia como a plataforma atende aos principais dispositivos da
Lei Geral de Proteção de Dados. **Não substitui parecer jurídico** — é a
descrição técnica dos controles implementados.

## Papéis

- **Controlador**: `DATA_CONTROLLER_NAME` (configurável por env).
- **Encarregado (DPO)**: `DPO_EMAIL` — divulgado no aviso de privacidade público.
- **Operadores**: colaboradores autenticados, com acesso mínimo por RBAC.

## Princípios (art. 6º) e como são atendidos

| Princípio               | Implementação |
| ----------------------- | ------------- |
| Finalidade              | `ConsentRecord.purpose` registra a finalidade de cada tratamento |
| Adequação / Necessidade | Minimização: documentos exibidos mascarados (`document_masked`) |
| Livre acesso            | `GET /api/lgpd/export/{id}` e canal de requisição do titular |
| Transparência           | Scoring **explicável**; aviso de privacidade público |
| Segurança               | bcrypt, JWT, cabeçalhos de segurança, HTTPS em produção |
| Prevenção               | Validação estrita de entrada (Pydantic) |
| Responsabilização       | Trilha de auditoria imutável (`AuditLog`) |

## Bases legais (art. 7º)

Registradas em `ConsentRecord.legal_basis`:
`consentimento`, `legitimo_interesse`, `obrigacao_legal`,
`execucao_contrato`, `protecao_credito`.

> Cobrança de crédito costuma apoiar-se em **legítimo interesse** e
> **execução de contrato**; a plataforma permite registrar a base adequada por
> finalidade.

## Consentimento (art. 8º)

- `POST /api/lgpd/consents` — registra consentimento/base com finalidade e canal.
- `POST /api/lgpd/consents/{id}/revoke` — revogação a qualquer tempo (art. 8º §5º).
- `GET  /api/lgpd/consents/{debtor_id}` — histórico do titular.

## Direitos do titular (art. 18)

Canal **público** (sem login) para o titular exercer seus direitos:

```
POST /api/lgpd/requests
{ "requester_document": "000.000.000-00", "request_type": "acesso" }
```

Tipos: `acesso`, `correcao`, `exclusao`, `portabilidade`, `anonimizacao`,
`revogacao`. As requisições são triadas pela administração
(`GET/PATCH /api/lgpd/requests`) com controle de status
(`recebida → em_analise → concluida/recusada`).

**Verificação de identidade**: ao abrir a requisição, o titular informa o
e-mail; o sistema compara com o cadastro e marca `identity_verified`.
Requisições não verificadas devem passar por conferência manual de identidade
antes de qualquer ação sobre os dados — evitando divulgação indevida a terceiros.

### Acesso e portabilidade (art. 18, II e V)

`GET /api/lgpd/export/{debtor_id}` gera relatório estruturado com todos os dados
do titular, suas dívidas, pagamentos e consentimentos — pronto para entrega em
formato interoperável (JSON).

### Eliminação / anonimização (arts. 16 e 18, IV)

`POST /api/lgpd/anonymize/{debtor_id}` executa **anonimização irreversível** do
PII (nome, documento, contato) via pseudônimo derivado de hash, **preservando os
registros financeiros** necessários ao cumprimento de obrigação legal e ao
exercício regular de direitos (exceção do art. 16). A ação é auditada.

## Retenção

`LGPD_RETENTION_DAYS` (padrão: 1825 dias / 5 anos) documenta o prazo de guarda
associado a obrigações legais de cobrança e contábeis.

## Segurança da informação (art. 46)

- **Criptografia de PII em repouso**: CPF/CNPJ são cifrados no banco com
  Fernet (AES-128 + HMAC). A busca por documento usa um **índice cego**
  (HMAC-SHA256), sem armazenar o valor em claro. Ver `app/core/crypto.py`.
- Senhas com **bcrypt** (custo configurável).
- Autenticação **JWT** com expiração + **proteção contra brute-force**
  (bloqueio temporário após N tentativas — `app/core/ratelimit.py`).
- **Validação de segredos em produção**: a aplicação recusa iniciar com
  chaves padrão de desenvolvimento quando `APP_ENV=production`.
- **RBAC** hierárquico + escopo por setor (acesso mínimo necessário).
- Cabeçalhos de segurança (incl. **HSTS** em produção) e CORS restrito.
- **Auditoria** de login, criação/edição de usuários, exportações, anonimizações
  e requisições de titulares.

## Relatório de impacto e incidentes

O setor de **Infraestrutura** mantém registro de incidentes (`/api/infraestrutura/incidents`),
que pode subsidiar a comunicação de incidentes de segurança à ANPD e aos
titulares (art. 48) quando aplicável.
