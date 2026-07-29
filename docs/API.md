# Referência da API

Base URL: `/api` · Documentação interativa: `GET /docs` (Swagger) e `/redoc`.

Autenticação: `Authorization: Bearer <token>` (obtido no login). Papéis:
`administracao < gerencia < diretoria`.

## Sistema

| Método | Rota      | Descrição            |
| ------ | --------- | -------------------- |
| GET    | `/`       | Metadados do serviço |
| GET    | `/health` | Health check         |

## Autenticação — `/api/auth`

| Método | Rota      | Acesso   | Descrição                         |
| ------ | --------- | -------- | --------------------------------- |
| POST   | `/login`  | público  | Login via JSON `{email, password}`|
| POST   | `/token`  | público  | Login OAuth2 (Swagger Authorize)  |
| GET    | `/me`     | autenticado | Usuário corrente               |

## Usuários — `/api/users`

| Método | Rota          | Acesso     | Descrição              |
| ------ | ------------- | ---------- | ---------------------- |
| GET    | `/`           | gerencia+  | Lista usuários         |
| POST   | `/`           | gerencia+  | Cria usuário           |
| GET    | `/{id}`       | próprio/gerencia+ | Detalhe         |
| PATCH  | `/{id}`       | gerencia+  | Atualiza usuário       |
| DELETE | `/{id}`       | diretoria  | Desativa (soft delete) |

## Cobrança — `/api/collection`

| Método | Rota           | Descrição                       |
| ------ | -------------- | ------------------------------- |
| GET    | `/debtors`     | Lista/busca devedores           |
| POST   | `/debtors`     | Cadastra devedor                |
| GET    | `/debts`       | Lista dívidas (filtros)         |
| POST   | `/debts`       | Cria dívida (com scoring)       |
| POST   | `/agreements`  | Cria acordo (parcelas/desconto) |
| POST   | `/payments`    | Registra pagamento              |
| GET    | `/interactions`| Histórico de contatos/tabulação |
| POST   | `/interactions`| Registra contato (tabulação)    |

## Setores

- **Control Desk** — `/api/control-desk`: `GET /monitor`, `GET/POST /campaigns`,
  `POST /campaigns/{id}/pacing`, `POST /snapshots`
- **Planejamento** — `/api/planejamento`: `GET/POST /forecasts`, `GET/POST /goals`
- **MIS** — `/api/mis`: `GET /overview`, `GET /by-portfolio`, `GET /by-status`
- **Desenvolvimento** — `/api/desenvolvimento`: `GET/POST /features`,
  `PATCH /features/{id}/status`, `GET/POST /deployments`
- **Infraestrutura** — `/api/infraestrutura`: `GET/POST /incidents`,
  `POST /incidents/{id}/resolve`, `GET /health`

> Todos os endpoints de setor exigem que o usuário tenha acesso ao respectivo
> setor (diretoria acessa todos).

## LGPD — `/api/lgpd`

| Método | Rota                     | Acesso        | Descrição                    |
| ------ | ------------------------ | ------------- | ---------------------------- |
| GET    | `/privacy-notice`        | público       | Aviso de privacidade         |
| POST   | `/requests`              | público       | Titular abre requisição      |
| GET    | `/requests`              | administracao+| Lista requisições            |
| PATCH  | `/requests/{id}`         | administracao+| Atualiza status              |
| POST   | `/consents`              | autenticado   | Registra consentimento       |
| POST   | `/consents/{id}/revoke`  | autenticado   | Revoga consentimento         |
| GET    | `/consents/{debtor_id}`  | autenticado   | Histórico de consentimentos  |
| GET    | `/export/{debtor_id}`    | administracao+| Exporta dados (acesso/portab.)|
| POST   | `/anonymize/{debtor_id}` | gerencia+     | Anonimiza titular            |
| GET    | `/audit-logs`            | gerencia+     | Trilha de auditoria          |

## Exemplo — login e chamada autenticada

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@controldesk.example.com","password":"Admin@123456"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s localhost:8000/api/mis/overview -H "Authorization: Bearer $TOKEN"
```
