# agente_controlDesk
Sistema de Control Desk com IA para operações de cobrança e contact center, oferecendo monitoramento em tempo real, ajuste automático de pacing, scoring de mailing, forecast operacional, auditoria contínua e integração com Olos e EasyCollector. 🤖📊📞

---

## 🗓️ Agente de Tarefas (`agente_tarefas.py`)

Um agente de linha de comando para gerenciar suas **demandas do dia a dia** (to-do).
Não precisa instalar nada: usa apenas a biblioteca padrão do Python (3.9+) e guarda
os dados em um banco SQLite local.

### Onde ficam os dados
Por padrão em `~/.agente_tarefas/tarefas.db`. Para usar outro caminho, defina a
variável de ambiente `AGENTE_TAREFAS_DB`.

### Uso rápido

```bash
# Criar tarefas (prioridade, prazo e categoria são opcionais)
python agente_tarefas.py add "Enviar relatório mensal" -p alta -v amanha -c trabalho
python agente_tarefas.py add "Pagar boleto" -p urgente -v 05/08

# Ver a agenda do dia (atrasadas + para hoje + em andamento)
python agente_tarefas.py hoje        # ou apenas: python agente_tarefas.py

# Listar / filtrar
python agente_tarefas.py listar --atrasadas
python agente_tarefas.py listar -p urgente
python agente_tarefas.py listar -b relatório   # busca por texto
python agente_tarefas.py listar --todas         # inclui concluídas/canceladas

# Andamento das tarefas
python agente_tarefas.py iniciar 3    # marca como "em andamento"
python agente_tarefas.py concluir 3   # marca como concluída
python agente_tarefas.py reabrir 3
python agente_tarefas.py cancelar 3

# Editar / detalhar / remover
python agente_tarefas.py editar 3 -p urgente -v hoje
python agente_tarefas.py ver 3
python agente_tarefas.py remover 3 -y

# Estatísticas gerais
python agente_tarefas.py resumo
```

### Comandos

| Comando | Aliases | O que faz |
|---------|---------|-----------|
| `add`      | `nova`         | Cria uma nova tarefa |
| `listar`   | `ls`, `lista`  | Lista/filtra tarefas |
| `hoje`     | `agenda`       | Agenda do dia (atrasadas + hoje + em andamento) |
| `ver`      | `show`         | Detalhes de uma tarefa |
| `editar`   | `edit`         | Edita campos de uma tarefa |
| `iniciar`  | `start`        | Marca como em andamento |
| `concluir` | `done`, `ok`   | Marca como concluída |
| `reabrir`  | —              | Volta a pendente |
| `cancelar` | —              | Cancela a tarefa |
| `remover`  | `rm`           | Remove a tarefa (use `-y` para não confirmar) |
| `resumo`   | `stats`        | Estatísticas gerais |

### Formatos de prazo (`-v` / `--vencimento`)
`hoje`, `amanha`, `ontem`, `+N` (N dias à frente), dia da semana (`seg`, `ter`, …,
próxima ocorrência), `DD/MM`, `DD/MM/AAAA` ou `AAAA-MM-DD`.

### Prioridades
`baixa`, `media` (padrão), `alta`, `urgente` — usadas para ordenar as listagens.
