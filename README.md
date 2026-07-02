# agente_controlDesk
Sistema de Control Desk com IA para operações de cobrança e contact center, oferecendo monitoramento em tempo real, ajuste automático de pacing, scoring de mailing, forecast operacional, auditoria contínua e integração com Olos e EasyCollector. 🤖📊📞

## 🖥️ Frontend — ATLAS

Interface web completa, dinâmica e responsiva (tema **preto & laranja**, inspirado
no sistema **ATLAS** da Roveri Cobrança) em `frontend/`. Não requer etapa de build.

```bash
# Servido pelo próprio backend FastAPI
python projeto_git.py api          # → http://localhost:8000/app/

# Ou standalone (modo demonstração, login admin/admin)
cd frontend && python -m http.server 8137   # → http://localhost:8137/
```

Consulte [`frontend/README.md`](frontend/README.md) para detalhes.
