# agente_controlDesk
Sistema de Control Desk com IA para operações de cobrança e contact center, oferecendo monitoramento em tempo real, ajuste automático de pacing, scoring de mailing, forecast operacional, auditoria contínua e integração com Olos e EasyCollector. 🤖📊📞

## Como executar (control_desk_agent.py)

```bash
pip install -r requirements.txt
cp .env.example .env   # gerado automaticamente na primeira execução; preencha com suas credenciais
python control_desk_agent.py
```

Ao iniciar, o agente sobe um health check em `http://localhost:8080/health`, roda ETL/monitoramento/relatórios/forecast em background via scheduler interno, e envia alertas para Teams/Email conforme configurado no `.env`.
