# Deploy — Robô Analisador de Ligações (ALO / NÃO ALO)

Guia para subir o robô em produção e começar a analisar ligações. Dois
caminhos: **Docker (recomendado)** e **systemd (bare-metal)**. Segurança
detalhada em [`SECURITY.md`](SECURITY.md).

---

## Opção A — Docker Compose (recomendado)

Sobe o robô + Postgres, com reinício automático. É o caminho mais rápido para
ficar 24/7.

```bash
# 1. Configuração
cp .env.docker.example .env
#    edite .env e defina, no mínimo:
#      ROBO_ALO_API_KEY   (openssl rand -base64 32)
#      POSTGRES_PASSWORD  (openssl rand -base64 24)

# 2. Subir
docker compose up -d --build

# 3. Testar
curl -H "X-API-Key: $ROBO_ALO_API_KEY" http://localhost:5501/
```

O robô cria a tabela `alo_analises` sozinho no Postgres. Logs:
`docker compose logs -f robo-alo`. Atualizar: `git pull && docker compose up -d --build`.

### HTTPS

Em produção, ponha um proxy TLS na frente (nginx/Caddy) ou use certificados
diretos (`ROBO_ALO_TLS_CERT`/`ROBO_ALO_TLS_KEY`). Exemplo de bloco Caddy:

```
ligacoes.suaempresa.com {
    reverse_proxy 127.0.0.1:5501
}
```

---

## Opção B — systemd (bare-metal)

```bash
git clone <repo> /opt/agente_controlDesk && cd /opt/agente_controlDesk
python -m venv .venv && .venv/bin/pip install -r requirements-robo.txt

sudo useradd --system --home /opt/agente_controlDesk alo
sudo mkdir -p /etc/alo-robo
sudo cp .env.docker.example /etc/alo-robo/env   # edite e preencha as chaves
sudo cp deploy/alo-robo.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now alo-robo
systemctl status alo-robo
```

Sem Postgres nas variáveis, a persistência cai automaticamente para SQLite em
`data/alo_analises.db` (bom para começar; migre para Postgres em escala).

---

## Ligar o robô ao discador

O robô analisa a partir de dados de CDR + transcrição. Três formas:

1. **Envio direto (recomendado para começar):** seu discador/ETL faz `POST /alo/lote`
   com um lote de ligações no corpo (`{"chamadas":[...]}`). Tolera os nomes de
   campo mais comuns (`phone`/`telefone`, `carrier`/`operadora`, `amd_result`/`amd`,
   `sip_cause`, `turns`/`turnos`).
2. **Puxar do Olos:** configure `OLOS_BASE_URL`/`OLOS_TOKEN` e use
   `GET /alo/call/{id}` ou `POST /alo/processar` (lote recente).
3. **Uma ligação avulsa:** `POST /alo/analisar`.

Toda rota `/alo/*` exige o header `X-API-Key`.

```bash
curl -X POST http://SEU_SERVIDOR:5501/alo/lote \
  -H "X-API-Key: $ROBO_ALO_API_KEY" -H "Content-Type: application/json" \
  -d '{"chamadas":[
        {"id":"1","carrier":"Claro","amd_result":"Humano",
         "turns":[{"speaker":"cliente","text":"Alô","start":1.1}]}
      ]}'

# painel agregado
curl -H "X-API-Key: $ROBO_ALO_API_KEY" "http://SEU_SERVIDOR:5501/alo/estatisticas?dias=1"
```

---

## Modo de análise

Definido por `ALO_MODO` (padrão **hibrido**):

| Modo | Comportamento | Custo / velocidade |
|---|---|---|
| `heuristica` | Só regras determinísticas. | Grátis, ~milissegundos, offline. |
| `ia` | Sempre Claude (fallback heurístico em falha). | Custo por ligação + latência de rede. |
| `hibrido` | Heurística em tudo; **IA só nas ligações duvidosas** (confiança < `ALO_HIBRIDO_LIMIAR`). | Melhor custo/precisão. |

No híbrido, **sem `ANTHROPIC_API_KEY` o robô roda 100% na heurística** (sem
custo) — a IA entra automaticamente quando a chave é configurada. Cada resposta
traz `origem` (`heuristica`/`ia`) e `escalado_para_ia`; o resumo de lote traz
`escaladas_ia` (quantas foram para a IA).

---

## Escala

- **1 worker ≈ 390 análises/s** (heurística) nesta classe de máquina; suba
  `ROBO_ALO_WORKERS` (≈ 1 por núcleo) para escalar quase linear.
- Para várias instâncias, use **Postgres** (já suportado) e um balanceador.
  Observação: o rate-limit é por processo — para um teto global numa frota,
  use um proxy com limite centralizado.
- Números completos de capacidade: `scripts/loadtest_alo.py`.

---

## Checklist final de produção

- [ ] `ROBO_ALO_API_KEY` forte definida (não a chave gerada automaticamente).
- [ ] HTTPS na frente (proxy TLS) ou `ROBO_ALO_TLS_CERT/KEY`.
- [ ] Postgres com senha forte e backup; retenção/expurgo dos dados (LGPD).
- [ ] `ROBO_ALO_WORKERS` dimensionado à CPU.
- [ ] Monitoramento do `/health` e dos logs.
- [ ] Se usar IA, avaliar base legal (LGPD) para envio de transcrição à Anthropic.
