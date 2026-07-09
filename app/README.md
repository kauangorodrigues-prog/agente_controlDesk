# NexusAI Control Desk

Uma aplicação completa de **Service Desk / ITSM com IA** — gestão de tickets,
incidentes, dashboard operacional, relatórios e um assistente virtual de suporte
técnico. Totalmente **self-contained**: roda sozinha, sem depender de nenhum
serviço externo (banco de dados embutido em SQLite e autenticação local).

![stack](https://img.shields.io/badge/React-19-61DAFB) ![stack](https://img.shields.io/badge/Vite-7-646CFF) ![stack](https://img.shields.io/badge/tRPC-11-2596BE) ![stack](https://img.shields.io/badge/SQLite-embutido-003B57) ![license](https://img.shields.io/badge/license-MIT-green)

## ✨ Funcionalidades

- **Dashboard** — estatísticas em tempo real, tendência de tickets, distribuição
  por categoria/status e monitor de status dos sistemas.
- **Tickets** — CRUD completo com busca, filtros por status/prioridade e paginação.
- **Incidentes** — registro e acompanhamento de incidentes com impacto e prioridade.
- **Chat IA** — assistente virtual de suporte de TI que **consulta a Base de
  Conhecimento** e cita o artigo relevante na resposta, além de criar ticket a
  partir da conversa.
- **Base de Conhecimento** — artigos de suporte com busca, filtro por categoria,
  contagem de visualizações e CRUD completo (Markdown básico). Integrada ao Chat IA.
- **Equipe / Usuários** — diretório de membros com estatísticas (total,
  administradores, ativos nos últimos 30 dias); administradores podem criar
  usuários, alterar papéis (admin/usuário) e remover contas, com proteção contra
  auto-exclusão/rebaixamento.
- **Relatórios** — volume de tickets, tempo de resolução, distribuição de
  prioridade e resumo executivo.
- **Configurações** — perfil, notificações, aparência e segurança.
- **Autenticação local** — cadastro e login por e-mail/senha (sessão via JWT em
  cookie httpOnly). Sem dependência de provedores OAuth externos.

## 🚀 Como rodar

Pré-requisitos: **Node.js 20+**.

```bash
cd app
npm install        # instala as dependências
npm run dev        # inicia em http://localhost:3000
```

No primeiro boot o app cria automaticamente o banco SQLite em `data/controldesk.db`,
cria a estrutura das tabelas e popula dados de demonstração (tickets, incidentes,
conversa de chat e uma conta de administrador).

### Conta padrão

| E-mail                | Senha      | Papel |
| --------------------- | ---------- | ----- |
| `admin@nexusai.com`   | `admin123` | admin |

Você também pode criar novas contas pela tela de login (aba **Criar conta**).

### Produção

```bash
npm run build      # gera o front-end + bundle do servidor em dist/
npm start          # NODE_ENV=production, serve em http://localhost:3000
```

## ⚙️ Configuração (opcional)

Tudo funciona sem configuração. Para customizar, copie `.env.example` para `.env`:

| Variável       | Padrão                    | Descrição                                            |
| -------------- | ------------------------- | ---------------------------------------------------- |
| `APP_SECRET`   | *(dev secret)*            | Segredo usado para assinar o JWT de sessão.          |
| `DATABASE_URL` | `data/controldesk.db`     | Caminho do arquivo SQLite (ou URL `sqlite://`).      |
| `OWNER_EMAIL`  | `admin@nexusai.com`       | E-mail promovido a `admin` no primeiro cadastro.     |
| `PORT`         | `3000`                    | Porta do servidor em produção.                       |

## 🧱 Arquitetura

```
app/
├── api/                 # Backend (Hono + tRPC)
│   ├── boot.ts          # Entry point; inicializa o DB e monta as rotas
│   ├── router.ts        # Composição dos routers tRPC
│   ├── *-router.ts      # auth, dashboard, ticket, incident, chat, report, kb
│   ├── kimi/            # Sessão JWT (assinatura/verificação) + auth por cookie
│   ├── lib/             # env, password (scrypt), cookies, http, vite
│   └── queries/         # Conexão SQLite (Drizzle) e queries de usuários
├── db/
│   ├── schema.ts        # Schema Drizzle (SQLite)
│   └── seed.ts          # Seed idempotente (roda no boot)
├── contracts/           # Constantes, erros e tipos compartilhados
├── src/                 # Frontend (React 19 + Vite + shadcn/ui + Tailwind)
│   ├── pages/           # Dashboard, Tickets, Incidentes, ChatIA, Relatorios, ...
│   ├── components/      # MainLayout + biblioteca de UI (shadcn)
│   ├── hooks/           # useAuth, use-mobile
│   └── providers/       # Provider tRPC/React Query
└── data/                # Banco SQLite gerado em runtime (ignorado pelo git)
```

**Stack:** React 19 · Vite 7 · TypeScript · tRPC 11 · TanStack Query · Hono ·
Drizzle ORM · better-sqlite3 · Tailwind CSS 3 · shadcn/ui · Recharts.

## 📜 Licença

Distribuído sob a licença **MIT**. Veja [LICENSE](./LICENSE).
