# Deploy em produção (Vercel + Supabase)

Guia para publicar a plataforma com **frontend + backend na Vercel** e
**PostgreSQL no Supabase**. O código já está preparado: entrypoint serverless
(`backend/api/index.py`), `backend/vercel.json`, rate-limit persistente no banco
e endpoint de bootstrap para inicializar o banco remoto.

> Os valores de segredos (chaves, senhas) **não** ficam versionados. Gere-os com
> `python -c "import secrets; print(secrets.token_urlsafe(48))"` e configure-os
> apenas como variáveis de ambiente na Vercel.

## Arquitetura

```
[ Frontend (Vite/React, estático) ]  →  [ Backend (FastAPI serverless) ]  →  [ PostgreSQL ]
            Vercel                                Vercel                        Supabase
```

## 1. Banco de dados (Supabase)

1. Crie um projeto PostgreSQL (região sugerida: `sa-east-1` / São Paulo).
2. Crie um papel de aplicação (SQL Editor):
   ```sql
   CREATE ROLE app_user LOGIN PASSWORD '<senha-forte>';
   GRANT USAGE, CREATE ON SCHEMA public TO app_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;
   ```
3. Copie a **connection string do pooler** (Project Settings → Database →
   *Connection pooling*). Use o **Session pooler** (porta 5432, IPv4) — ideal para
   serverless. Formato:
   ```
   postgresql+psycopg://app_user.<project-ref>:<senha>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
   ```
   > Se usar o *Transaction pooler* (porta 6543), acrescente o desligamento de
   > prepared statements no driver. O Session pooler evita esse ajuste.

## 2. Backend na Vercel

1. **Import Project** → selecione o repositório GitHub.
2. **Root Directory**: `backend`.
3. Framework preset: *Other* (o `vercel.json` já roteia tudo para `api/index.py`).
4. **Environment Variables** (Production):

   | Chave | Valor |
   | --- | --- |
   | `APP_ENV` | `production` |
   | `DATABASE_URL` | connection string do passo 1 |
   | `JWT_SECRET_KEY` | (segredo forte) |
   | `DATA_ENCRYPTION_KEY` | (segredo forte) |
   | `DATA_INDEX_KEY` | (segredo forte) |
   | `BOOTSTRAP_TOKEN` | (token para inicialização única) |
   | `FIRST_ADMIN_EMAIL` | e-mail do admin master |
   | `FIRST_ADMIN_PASSWORD` | senha forte do admin |
   | `CORS_ORIGINS` | URL do frontend (passo 3) |

5. **Deploy**. Anote a URL do backend (ex.: `https://<app>-api.vercel.app`).
6. Teste: `GET https://<backend>/health` → `{"status":"ok"}`.

## 3. Frontend na Vercel

1. **Import Project** → mesmo repositório.
2. **Root Directory**: `frontend`. Framework: *Vite* (auto-detectado).
3. **Environment Variables**: `VITE_API_URL` = URL do backend (passo 2).
4. **Deploy**. Anote a URL do frontend.
5. Volte ao backend e ajuste `CORS_ORIGINS` para a URL do frontend; redeploy.

## 4. Inicialização do banco (uma única vez)

Cria o schema e popula os dados de demonstração via endpoint protegido:

```bash
curl -X POST https://<backend>/api/system/bootstrap \
  -H "X-Bootstrap-Token: <BOOTSTRAP_TOKEN>"
# → {"ok": true, "users": 6, "debtors": 60}
```

Depois, **remova a variável `BOOTSTRAP_TOKEN`** (ou deixe-a vazia) e faça redeploy
para desabilitar o endpoint.

## 5. Verificação

- `https://<frontend>` → login com `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD`.
- Visão Geral deve exibir os indicadores (dados do seed).
- `GET https://<backend>/metrics` → métricas operacionais.

## Notas de produção

- **Migrations**: o repositório usa Alembic (`alembic upgrade head`). O bootstrap
  cria o schema via `create_all` (idêntico às migrations, verificado por teste de
  drift) para simplificar a inicialização serverless.
- **Segredos**: nunca versione. Configure só na Vercel. Em `APP_ENV=production`, a
  aplicação recusa iniciar com chaves padrão de desenvolvimento.
- **SMTP** (régua de e-mail): defina `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` para
  envio real; sem isso, opera em modo simulado.
