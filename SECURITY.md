# Segurança — Robô Analisador de Ligações (ALO / NÃO ALO)

Este documento resume as proteções já implementadas no robô e o checklist para
rodar com segurança **na rede / em produção**.

## Proteções já implementadas (no código)

| Controle | Como funciona |
|---|---|
| **Autenticação obrigatória** | Todas as rotas `/alo/*` exigem o header `X-API-Key`. A chave vem de `ROBO_ALO_API_KEY`. Se a variável não for definida, o robô **gera uma chave forte na inicialização e a registra no log** — nunca sobe aberto. Comparação em tempo constante (`secrets.compare_digest`), imune a timing attack. |
| **CORS restrito** | Cross-origin no navegador fica **bloqueado por padrão**. Libere apenas origens conhecidas em `ROBO_ALO_CORS_ORIGINS`. |
| **Rate-limit por IP** | Janela deslizante de 60 s; padrão 120 req/min (`ROBO_ALO_RATE_LIMIT`). Excedeu → `429`. |
| **Limite de tamanho** | Corpo acima de `ROBO_ALO_MAX_BYTES` (5 MB) → `413`. Lote acima de `ROBO_ALO_MAX_LOTE` (1000 ligações) → `413`. |
| **Validação de `call_id`** | Apenas `[A-Za-z0-9_:-]` (sem `.` / `/`), barrando path-traversal → `400`. |
| **Cabeçalhos de segurança** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`. |
| **Erros genéricos** | Respostas de erro não expõem detalhes internos (stack/DB); o detalhe fica só no log. |
| **HTTPS opcional embutido** | Defina `ROBO_ALO_TLS_CERT` e `ROBO_ALO_TLS_KEY` para servir em TLS direto (ou use um proxy HTTPS). |
| **Segredos fora do código** | Credenciais vêm de variáveis de ambiente; `.env` está no `.gitignore`. |

Rotas públicas (sem dados pessoais): apenas `GET /` e `GET /health`.

## Checklist para produção

1. **Defina uma `ROBO_ALO_API_KEY` própria e forte** (ex.: `openssl rand -base64 32`).
   Não use a chave gerada automaticamente em produção — fixe a sua.
2. **Sirva em HTTPS.** Configure `ROBO_ALO_TLS_CERT`/`ROBO_ALO_TLS_KEY` ou coloque
   atrás de um reverse proxy (nginx/Caddy) com TLS. Nunca trafegue telefone e
   transcrição em HTTP na rede.
3. **Restrinja a exposição.** Prefira `ROBO_ALO_HOST=127.0.0.1` atrás de um proxy,
   ou uma rede interna/VPN. Só use `0.0.0.0` quando for realmente necessário.
4. **Libere apenas as origens necessárias** em `ROBO_ALO_CORS_ORIGINS` (se houver front-end).
5. **Proteja os dados em repouso (LGPD).** O banco guarda telefone e trechos de
   transcrição — use criptografia de disco/coluna, controle de acesso e uma
   política de retenção/expurgo.
6. **API completa (`main.py api`):** defina `JWT_SECRET_KEY`. Com `AMBIENTE=production`,
   o boot **falha** se o segredo estiver no valor padrão.
7. **Modo IA:** com `ANTHROPIC_API_KEY` definida, a transcrição é enviada à API da
   Anthropic. Avalie a base legal (LGPD) antes de ligar em produção; sem a chave,
   o robô roda 100% local na heurística.

## Exemplo de execução segura

```bash
export ROBO_ALO_API_KEY="$(openssl rand -base64 32)"
export ROBO_ALO_HOST=127.0.0.1          # atrás de um proxy HTTPS
export ROBO_ALO_CORS_ORIGINS=https://painel.suaempresa.com
export ROBO_ALO_RATE_LIMIT=120
python main.py alo                       # porta 5501
```

Reportar uma vulnerabilidade: abra um issue privado / contate a equipe de segurança.
