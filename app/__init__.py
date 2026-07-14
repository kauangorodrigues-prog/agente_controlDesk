"""Pacote `app` — arquitetura modular do Agente IA Control Desk (Fase 6).

Extração incremental e retrocompatível do módulo único `agente_ia_control_desk`,
que permanece como fachada (mantém entrypoints, celery_app, scripts e testes).

Camadas-alvo (preenchidas de forma incremental, sem perder funcionalidade):

    app/
    ├── config.py         # configuração (Config, CFG)
    ├── core/             # logging, resiliência, cache, banco
    ├── utils/            # validadores e helpers puros
    ├── repositories/     # acesso a dados (Repository Pattern)
    ├── integrations/     # clientes de discador/CRM
    ├── services/         # ETL, ocupação, pacing, holiday, mailing
    ├── forecasting/      # previsão (ensemble)
    ├── ai/               # propensão, decisão, uplift
    ├── scheduler/        # jobs, fila
    ├── monitoring/       # métricas e health
    ├── alerts/           # webhooks
    └── api/              # FastAPI

Princípios (M20): SOLID, separação de responsabilidades, dependências apenas
"para baixo" (camadas core/utils não conhecem as camadas superiores).
"""
