# Deploy — Robô Analisador de Ligações (ALO / NÃO ALO)

Guia para subir o robô em produção e começar a analisar ligações. Dois
caminhos: **Docker (recomendado)** e **systemd (bare-metal)**. Segurança
detalhada em [`SECURITY.md`](SECURITY.md).

---

## Opção A — Docker Compose com HTTPS automático (recomendado)

Sobe **Caddy (HTTPS automático) + robô + Postgres**, com reinício automático.
O Caddy obtém e renova o certificado TLS sozinho. É o caminho para ficar 24/7 e
seguro na internet.

```bash
# 1. Configuração
cp .env.docker.example .env
#    edite .env e defina, no mínimo:
#      ROBO_ALO_API_KEY   (openssl rand -base64 32)
#      POSTGRES_PASSWORD  (openssl rand -base64 24)
#      ALO_DOMAIN         (seu domínio público; ou deixe 'localhost' p/ testar)

# 2. Subir
docker compose up -d --build

# 3. Testar
#    domínio público:
curl -H "X-API-Key: $ROBO_ALO_API_KEY" https://SEU_DOMINIO/
#    local (certificado interno → -k):
curl -k -H "X-API-Key: $ROBO_ALO_API_KEY" https://localhost/
```

O robô cria a tabela `alo_analises` sozinho no Postgres. Logs:
`docker compose logs -f`. Atualizar: `git pull && docker compose up -d --build`.

### Como funciona o HTTPS automático

- Defina **`ALO_DOMAIN`** com um domínio público cujo DNS aponte para o servidor
  e mantenha as **portas 80 e 443 abertas**. O Caddy emite e renova o
  certificado Let's Encrypt automaticamente — sem passo manual.
- Com `ALO_DOMAIN=localhost`, o Caddy usa um **certificado interno** (self-signed)
  para teste — use `curl -k`.
- O robô fica na rede interna do compose (exposto ao host só em
  `127.0.0.1:5501` para depuração); todo o tráfego externo entra pelo Caddy.
- O Caddy repassa o `X-Forwarded-For`, e o robô (`ROBO_ALO_TRUST_PROXY=true`, já
  configurado no compose) aplica o rate-limit pelo **IP real** de cada cliente.
- Adiciona **HSTS** e HTTP/2+HTTP/3 automaticamente.

> Alternativa sem Caddy: certificados diretos no robô via
> `ROBO_ALO_TLS_CERT`/`ROBO_ALO_TLS_KEY`.

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
- [ ] HTTPS ativo: `ALO_DOMAIN` com DNS apontando + portas 80/443 abertas (Caddy
      emite o certificado), ou `ROBO_ALO_TLS_CERT/KEY` no robô.
- [ ] Postgres com senha forte e backup; retenção/expurgo dos dados (LGPD).
- [ ] `ROBO_ALO_WORKERS` dimensionado à CPU.
- [ ] Monitoramento do `/health` e dos logs.
- [ ] Se usar IA, avaliar base legal (LGPD) para envio de transcrição à Anthropic.
