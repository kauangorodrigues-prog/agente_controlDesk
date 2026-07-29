# Arquitetura

## Visão em camadas

```
┌───────────────────────────────────────────────────────────┐
│  Front-end (React + Vite)  —  SPA, RBAC visual por setor    │
│  · AuthContext (JWT)  · api/client  · páginas por setor      │
└───────────────▲───────────────────────────────────────────┘
                │  HTTP/JSON (proxy /api → :8000)
┌───────────────┴───────────────────────────────────────────┐
│  API (FastAPI)                                             │
│  routers → deps (auth/RBAC) → services → models (ORM)      │
│  · middleware de segurança  · auditoria  · scoring         │
└───────────────▲───────────────────────────────────────────┘
                │  SQLAlchemy 2.x
┌───────────────┴───────────────────────────────────────────┐
│  Banco de Dados  —  SQLite (dev)  /  PostgreSQL (prod)     │
└───────────────────────────────────────────────────────────┘
```

## Backend — organização

- **`core/`** — infraestrutura transversal
  - `config.py` — configurações via env (12-factor)
  - `database.py` — engine, sessão e `Base` declarativa
  - `security.py` — bcrypt + JWT
  - `rbac.py` — enums de papéis/setores e hierarquia
  - `deps.py` — dependencies (`get_current_user`, `require_role`, `require_sector`)
- **`models/`** — entidades ORM (usuários, devedores, dívidas, pagamentos,
  campanhas, forecast, incidentes, features, auditoria, LGPD)
- **`schemas/`** — contratos de entrada/saída validados (Pydantic v2)
- **`routers/`** — um módulo por domínio/setor, todos sob `/api`
- **`services/`** — regras reutilizáveis: `audit`, `scoring`, `lgpd`

### Fluxo de autorização

1. `get_current_user` decodifica o JWT e carrega o usuário ativo.
2. `require_role(min)` valida a hierarquia `administracao < gerencia < diretoria`.
3. `require_sector(setor)` valida o acesso ao setor (diretoria acessa todos).

### Auditoria

Toda operação sensível chama `services.audit.record(...)`, gravando ator, ação,
entidade, IP e timestamp — atendendo ao princípio de _accountability_ (LGPD).

## Modelo de dados (resumo)

```
User 1─* SectorAccess
Debtor 1─* Debt 1─* Payment
                └─* PaymentAgreement
Debtor 1─* ConsentRecord
Debtor 1─* DataSubjectRequest
Campaign 1─* PacingSnapshot
Forecast · Goal · Incident · SystemHealthCheck · Feature · Deployment · AuditLog
```

## Decisões técnicas

- **SQLite por padrão** para permitir `git clone → rodar → testar` sem
  dependências externas; a mesma camada ORM roda em **PostgreSQL** apenas
  trocando `DATABASE_URL`.
- **RBAC hierárquico + por setor** separa cargo (poder) de área (escopo).
- **Scoring heurístico explicável** (não caixa-preta), alinhado ao princípio de
  transparência da LGPD.
- **Cabeçalhos de segurança** (`X-Frame-Options`, `nosniff`, etc.) aplicados por
  middleware global.

## Escalabilidade

- API _stateless_ (JWT) → escala horizontal atrás de load balancer.
- Banco relacional com índices nos campos de busca/filtro.
- Front-end estático servido por CDN/nginx.
- Serviços isolados (`services/`) prontos para virar workers/filas assíncronas.
