# ControlDesk · Cobranças SaaS

Plataforma **SaaS completa de cobrança de dívidas** (carteiras **ativas**,
**consignados**, **concierge** e **bancárias**), construída para operação de
larga escala, com **backend + API + front-end + banco de dados** totalmente
conectados e **conformidade LGPD** integrada.

> Evolução do agente original de _Control Desk_ (IA para operações de cobrança e
> contact center) para uma plataforma multi-setorial com governança de dados.

---

## ✨ Visão geral

| Camada         | Stack                                             |
| -------------- | ------------------------------------------------- |
| **Front-end**  | React 18 + TypeScript + Vite + React Router       |
| **API/Back-end** | FastAPI + SQLAlchemy 2 + Pydantic v2 (Python 3.11) |
| **Banco**      | SQLite (dev, zero-config) · PostgreSQL (produção) |
| **Auth**       | JWT (OAuth2) + bcrypt + RBAC hierárquico          |
| **Migrations** | Alembic (schema versionado, validado em PostgreSQL) |
| **Infra**      | Docker + docker-compose + nginx + CI (GitHub Actions) |
| **Testes**     | pytest (22 testes: API, RBAC, LGPD, segurança, migrations) |

### Setores da plataforma

- **Control Desk** — monitoramento operacional, pacing, mailing e campanhas
- **Planejamento** — forecast e metas por carteira
- **MIS** — indicadores agregados e business intelligence
- **Desenvolvimento** — board de features e histórico de deploys
- **Infraestrutura** — incidentes e saúde dos sistemas

### Papéis (cadastro de usuários)

`diretoria` › `gerencia` › `administracao` (hierarquia crescente de privilégios),
cada um com acesso configurável por setor.

---

## 🚀 Como rodar

### Opção A — Docker (stack completa: Postgres + API + Front)

```bash
docker compose up --build
```

- Front-end: <http://localhost:8080>
- API + Swagger: <http://localhost:8000/docs>

### Opção B — Local (desenvolvimento)

**1. Backend** (porta 8000, banco SQLite automático)

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head      # aplica as migrations (schema)
python -m app.seed        # popula dados de demonstração
uvicorn app.main:app --reload
```

> Em desenvolvimento com SQLite, `python -m app.seed` também cria o schema
> automaticamente. Em produção/PostgreSQL, use sempre `alembic upgrade head`.

**2. Front-end** (porta 5173, com proxy para a API)

```bash
cd frontend
npm install
npm run dev
```

Abra <http://localhost:5173>.

### Credenciais de demonstração

| E-mail                               | Senha           | Papel         |
| ------------------------------------ | --------------- | ------------- |
| `admin@controldesk.example.com`      | `Admin@123456`  | diretoria     |
| `diretoria@controldesk.example.com`  | `Diretoria@123` | diretoria     |
| `gerencia@controldesk.example.com`   | `Gerencia@123`  | gerencia      |
| `operacao@controldesk.example.com`   | `Operacao@123`  | administracao |

---

## 🧪 Testes e qualidade

```bash
cd backend
python -m pytest            # 15 testes: auth, cobrança, RBAC e LGPD

cd ../frontend
npm run build               # type-check (tsc) + build de produção
```

---

## 🔐 LGPD — Conformidade

O módulo LGPD (`/api/lgpd`) cobre os principais requisitos da Lei 13.709/2018.
Veja **[docs/LGPD.md](docs/LGPD.md)** para o detalhamento por artigo. Destaques:

- **Aviso de privacidade público** (`GET /api/lgpd/privacy-notice`)
- **Consentimento e base legal** por finalidade (arts. 7º e 8º)
- **Direitos do titular** — acesso, correção, exclusão, portabilidade,
  anonimização e revogação (art. 18), com **canal público de requisição**
- **Anonimização irreversível** preservando integridade contábil (art. 16)
- **Exportação de dados** (acesso e portabilidade)
- **Trilha de auditoria** de todas as operações sensíveis (art. 37)
- **Minimização de dados** — documentos exibidos sempre mascarados
- **Criptografia de CPF/CNPJ em repouso** (Fernet) com busca por índice cego
- **Proteção de login** contra brute-force + validação de segredos em produção

---

## 📚 Documentação

- [docs/ARQUITETURA.md](docs/ARQUITETURA.md) — arquitetura e decisões técnicas
- [docs/LGPD.md](docs/LGPD.md) — conformidade legal detalhada
- [docs/API.md](docs/API.md) — referência dos endpoints

---

## 🗂️ Estrutura

```
.
├── backend/            # API FastAPI
│   ├── app/
│   │   ├── core/       # config, db, segurança, RBAC, deps
│   │   ├── models/     # ORM (SQLAlchemy)
│   │   ├── schemas/    # validação (Pydantic)
│   │   ├── routers/    # endpoints por setor/domínio
│   │   ├── services/   # auditoria, scoring, LGPD
│   │   ├── seed.py     # dados de demonstração
│   │   └── main.py
│   └── tests/          # pytest
├── frontend/           # SPA React + Vite
│   └── src/
│       ├── api/        # cliente HTTP + hooks
│       ├── context/    # autenticação
│       ├── components/ # layout + UI
│       └── pages/      # telas por setor
├── docs/
└── docker-compose.yml
```
