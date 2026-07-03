# agente_controlDesk
Sistema de Control Desk com IA para operações de cobrança e contact center, oferecendo monitoramento em tempo real, ajuste automático de pacing, scoring de mailing, forecast operacional, auditoria contínua e integração com Olos e EasyCollector. 🤖📊📞

## 🖥️ Frontend — ATLAS

Interface web completa, dinâmica e responsiva (tema **preto & laranja**, inspirado
no sistema **ATLAS** da Roveri Cobrança) em `frontend/`. Não requer etapa de build.

```bash
pip install -r requirements.txt

# Backend + frontend unificados (a raiz redireciona para o app)
python projeto_git.py api          # → http://localhost:8000/  (SPA ATLAS)
#                                     http://localhost:8000/docs (API)
#                                     http://localhost:8000/health (status)

# Ou frontend standalone (modo demonstração, login admin/admin)
cd frontend && python -m http.server 8137   # → http://localhost:8137/
```

O FastAPI serve o frontend em `/app/` e **redireciona a raiz `/` para o app**,
além de expor toda a API (ocupação, pacing, mailing, forecast, feriados,
auditoria, alertas) consumida pela interface. Consulte
[`frontend/README.md`](frontend/README.md) para detalhes.
