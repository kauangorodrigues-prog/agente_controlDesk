# ATLAS · Frontend — Control Desk IA

Frontend web completo, dinâmico e responsivo para o **agente_controlDesk**,
inspirado no design do sistema **ATLAS** (Roveri Cobrança). Tema **preto & laranja**.

> Stack **zero-build**: HTML + CSS + JavaScript (ES Modules) puros, sem
> dependências externas nem etapa de compilação. Gráficos SVG próprios,
> ícones inline. Funciona abrindo o `index.html` por qualquer servidor
> estático ou servido diretamente pelo backend FastAPI.

---

## ✨ Recursos

- **Login com JWT** contra o endpoint `POST /auth/token` do FastAPI.
- **8 módulos** navegáveis:
  | Módulo | Descrição | Endpoints |
  |--------|-----------|-----------|
  | Tempo Real | Ocupação ao vivo, distribuição de agentes, mailing, alertas | `/ocupacao`, `/ocupacao/campanhas`, `/alertas` |
  | Campanhas | Desempenho consolidado do dia | `/ocupacao/campanhas` |
  | Pacing | Histórico + execução do ajuste automático | `/pacing/historico`, `/pacing/ajustar` |
  | Mailing | Ranking por score, distribuição, exportar CSV | `/mailing/top`, `/mailing/processar` |
  | Forecast | Previsão de volume + dimensionamento de equipe | `/forecast`, `/forecast/gerar` |
  | Feriados | Calendário, cadastro, sincronização (admin) | `/feriados`, `/feriados/proximos`, ... |
  | Auditoria | Detecção de anomalias operacionais | `/auditoria/executar` |
  | Alertas | Linha do tempo com filtro por nível | `/alertas` |
- **Gráficos SVG** próprios: linha (com faixa de confiança), barras, donut/gauge.
- **Auto-refresh** configurável (30 s) + atualização manual.
- **Responsivo** (desktop / tablet / mobile) com sidebar retrátil.
- **Modo Demonstração** automático: se o backend estiver indisponível, o
  dashboard passa a usar dados simulados realistas — ótimo para apresentações.

---

## 🚀 Como usar

### Opção 1 — Servido pelo próprio FastAPI (recomendado)

O `projeto_git.py` monta este diretório automaticamente:

```bash
pip install -r requirements.txt
python projeto_git.py api
```

Acesse a **raiz** — ela redireciona para o app: **http://localhost:8000/**
(app em `/app/`, documentação da API em `/docs`, status em `/health`).

### Opção 2 — Servidor estático (sem backend / apenas demonstração)

```bash
cd frontend
python -m http.server 8137
```

Acesse **http://localhost:8137/** e entre com **`admin` / `admin`**
(modo demonstração, dados simulados).

---

## 🔧 Configuração

- **Base da API:** por padrão usa a mesma origem. Para apontar para outro host:
  ```js
  localStorage.setItem("cd_api_base", "http://localhost:8000");
  ```
- **Forçar modo demo:**
  ```js
  localStorage.setItem("cd_demo", "1");
  ```

---

## 📁 Estrutura

```
frontend/
├── index.html            # shell + loader
├── css/styles.css        # design system (tema preto & laranja)
└── js/
    ├── app.js            # bootstrap, router SPA, shell, auth flow
    ├── config.js         # constantes e flags
    ├── api.js            # cliente HTTP + JWT + fallback demo
    ├── mock.js           # camada de dados simulados
    ├── icons.js          # ícones SVG inline + logo ATLAS
    ├── ui.js             # helpers (toasts, KPIs, tabelas, modal, formatação)
    ├── charts.js         # gráficos SVG (line/bar/donut)
    └── pages/            # um módulo por tela
        ├── dashboard.js  campanhas.js  pacing.js   mailing.js
        └── forecast.js   feriados.js   auditoria.js alertas.js
```

Cada página exporta `meta` (título/subtítulo/ícone) e `mount(root)`, que
retorna opcionalmente `{ onRefresh }` usado pelo auto-refresh global.
