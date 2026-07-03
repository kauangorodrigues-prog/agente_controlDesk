# agente_controlDesk
Sistema de Control Desk com IA para operações de cobrança e contact center, oferecendo monitoramento em tempo real, ajuste automático de pacing, scoring de mailing, forecast operacional, auditoria contínua e integração com Olos e EasyCollector. 🤖📊📞

## 🖥️ Frontend — ATLAS

Interface web completa, dinâmica e responsiva (tema **preto & laranja**, inspirado
no sistema **ATLAS** da Roveri Cobrança) em `frontend/`. Não requer etapa de build.

```bash
pip install -r requirements.txt

# Backend + frontend unificados — o app é servido DIRETO NA RAIZ "/"
python projeto_git.py api          # → http://localhost:8000/      (app ATLAS)
#                                     http://localhost:8000/docs   (API / Swagger)
#                                     http://localhost:8000/health (status JSON)

# Ou frontend standalone (modo demonstração, login admin/admin)
cd frontend && python -m http.server 8137   # → http://localhost:8137/
```

> **Acesso por porta encaminhada (GitHub Codespaces / proxy):** o app é
> montado **na raiz `/`** (sem redirecionamentos nem subpaths), então basta
> abrir a URL da porta 8000 encaminhada que a interface carrega direto.
> Use o login de demonstração **`admin` / `admin`** caso não haja banco
> PostgreSQL configurado. O `uvicorn` sobe em `0.0.0.0` (necessário para o
> encaminhamento de porta).

O FastAPI serve o frontend na raiz `/` (e também em `/app/` como alias),
expondo toda a API (ocupação, pacing, mailing, forecast, feriados, auditoria,
alertas) consumida pela interface. Consulte
[`frontend/README.md`](frontend/README.md) para detalhes.
