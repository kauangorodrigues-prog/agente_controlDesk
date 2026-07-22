# Cobra.ai — Documento Estratégico

**Camada de Inteligência de Recuperação de Crédito (Receivables Intelligence)**
Do nicho de cobrança ao mercado global de *order-to-cash*.

*Versão 1.0 · Documento de trabalho · Nome "Cobra.ai" é provisório*

> **Avisos de rigor.** Os tamanhos de mercado citados vêm de relatórios públicos (Mordor Intelligence, Fortune Business Insights, Market Research Future, Grand View, entre outros) e servem como ordem de grandeza. As projeções financeiras são **cenários ilustrativos com premissas explícitas**, não previsões — não constituem aconselhamento financeiro. A tese depende de uma coisa acima de tudo: **provar aumento mensurável e repetível de recuperação (uplift) entre clientes.**

---

## 1. Sumário executivo

Operações de cobrança desperdiçam margem porque decidem *quem contatar, quando e por qual canal* no "feeling". A taxa de contato com a pessoa certa (CPC) é baixa, a esteira de acordo é lenta e a priorização de carteira é rudimentar. Isso custa **milhões por ano** em recuperação perdida em cada carteira relevante.

A **Cobra.ai** é uma camada de inteligência que se instala **sobre** os discadores e CRMs já existentes (Olos, Weddo, EasyCollector e similares). Ela ingere o mailing e os resultados de cobrança, prevê propensão a pagar, prioriza a carteira, orquestra canal e horário de abordagem e redige a comunicação — sempre com auditabilidade e humano no loop.

**Por que agora e por que nós:** o mercado de software de cobrança (~US$5–6 bi, crescendo ~9–10% a.a.) migra para analytics em tempo real e engajamento omnichannel; incumbentes como discadores são infraestrutura, não inteligência. A vantagem injusta do fundador é domínio operacional real do problema (Olos/Weddo, scoring de mailing, previsão de CPC já prototipados), o que encurta o MVP e dá credibilidade de venda.

**Estratégia central:** começar estreito, onde há vantagem injusta (inteligência de operação de cobrança), e expandir para o mercado gigante de *order-to-cash* / contas a receber. **Wedge → plataforma.**

---

## 2. O problema

Toda carteira inadimplente é uma operação de decisão sob incerteza: recursos de contato são limitados e cada devedor tem uma probabilidade e um "melhor caminho" diferentes para virar acordo. Hoje essa decisão é tomada com regras estáticas e intuição.

Consequências mensuráveis para o cliente:

- **Recuperação abaixo do potencial.** Contato no devedor errado, na hora errada e pelo canal errado desperdiça capacidade da operação.
- **CPC baixo.** Discagem sem priorização inteligente queima minutos de operador e minutos de discador em contatos improdutivos.
- **Esteira de acordo lenta.** Falta a "próxima melhor ação" para cada caso; negociação padronizada não personaliza oferta nem abordagem.
- **Falta de aprendizado.** O resultado de cada interação (o que efetivamente converteu) raramente vira modelo — o conhecimento fica na cabeça dos supervisores.

A dor é **cara e recorrente**, medida diretamente em reais de recuperação. Esse é o critério nº 1 de um problema que vale a pena resolver: quando o comprador consegue ligar sua solução a caixa recuperado, a venda deixa de ser sobre "features" e passa a ser sobre ROI.

---

## 3. A solução (produto)

A Cobra.ai é uma **camada de decisão auditável** entre os dados da carteira e a execução da operação. Ela não substitui o discador nem o CRM — ela os torna inteligentes.

**Capacidades do produto (por fase de maturidade):**

1. **Priorização** — score de propensão a pagar por conta, ordenando a carteira do dia por retorno esperado.
2. **Orquestração** — recomenda canal (voz, WhatsApp, e-mail, SMS) e janela de horário por perfil de devedor.
3. **Próxima melhor ação** — para cada caso, sugere a abordagem e a oferta de acordo com maior probabilidade de conversão.
4. **Redação assistida** — LLM redige a abordagem/negociação e resume o histórico do caso para o operador; humano aprova.
5. **Uplift e auditoria** — relatório A/B (grupo tratado × controle) que prova o ganho de recuperação, com trilha de auditoria para LGPD e regras de cobrança.

**Princípios de produto inegociáveis:**

- **Humano no loop** no início de cada carteira nova (nada de autonomia total falando com devedor — isso é o que trava a venda e cria risco regulatório).
- **Explicabilidade.** O motor mostra *por que* priorizou/recomendou. Isso vende e protege contra risco regulatório de scoring automatizado.
- **Neutralidade de discador.** A Cobra.ai é multi-discador por princípio; é complemento da infraestrutura do cliente, não concorrente frontal dela.

---

## 4. Mercado

**TAM (direcional, fontes públicas):**

| Camada de mercado | Tamanho 2025 (US$) | Crescimento | Fonte (ordem de grandeza) |
|---|---|---|---|
| Software de cobrança (wedge) | ~5–6 bi | ~9–10% a.a. | Mordor, Fortune, MRFR |
| Automação de contas a receber / order-to-cash (expansão) | ~3,4–4,8 bi | ~12–16% a.a. | Mordor, Grand View, SkyQuest |
| **Espaço endereçável combinado** | **> 10 bi** | crescente | síntese |

**SAM (realista de curto prazo):** operações de cobrança e credores digitais em LatAm (Português/Espanhol) com discador/CRM instalado — fintechs de crédito, financeiras, bancos digitais, BNPL, utilities e assessorias.

**SOM (3 anos):** algumas centenas de operações mid-market e SMB em LatAm. Não é preciso dominar o mercado global para chegar à faixa de valuation de US$100 M — basta capturar uma fatia defensável do SAM com NRR alto.

**Tese de tempo:** a digitalização de crédito gera dados de inadimplência em volume; a pressão por eficiência e a migração para nuvem/omnichannel criam a janela para uma camada de inteligência independente antes que os incumbentes a incorporem bem.

---

## 5. Modelo de negócio e pricing

**Formato:** SaaS B2B com contrato anual + componente de consumo (volume de carteira/assentos), e upsell atrelado a resultado.

**Estrutura de pricing (hipótese inicial, a validar):**

- **SMB (assessorias):** R$3–8 mil/mês → ~R$36–96 mil de ACV.
- **Mid-market (credores):** R$15–40 mil/mês → ~R$180–480 mil de ACV.
- **Expansão:** por carteira adicional, por canal orquestrado e, em contas maduras, componente de sucesso (% do uplift comprovado).

**Land & expand:** entra pela priorização (dor imediata, prova rápida), expande para orquestração omnichannel, simulação de acordo e, depois, para o order-to-cash mais amplo.

**Por que a recorrência é forte:** uma vez integrada ao discador/CRM e treinada nos dados da carteira, a Cobra.ai tem alto custo de troca e melhora com o tempo — o cliente perde performance ao sair.

---

## 6. Fosso competitivo (defensabilidade)

1. **Dado de resultado proprietário.** O que efetivamente converteu acordo (não só o mailing, mas o *outcome*) acumulado entre clientes. Modelos de LLM genéricos não têm isso; ninguém replica sem os dados.
2. **Integrações profundas.** Conectores maduros com discadores/CRMs criam custo de troca.
3. **Efeito de dados composto.** Quanto mais carteiras, melhor a previsão e o benchmark entre clientes — vantagem que aumenta com escala.
4. **Neutralidade estratégica.** Ao ser multi-discador e complementar à infraestrutura, evita a briga frontal com incumbentes e vira parceiro deles.

**Ameaça principal e resposta:** o discador incumbente pode tentar embutir inteligência. Resposta: mover rápido, ser neutro entre discadores (o que o incumbente não é), e ancorar-se no dado de resultado cross-cliente que um fornecedor de infraestrutura single-vendor não consegue montar.

---

## 7. Arquitetura técnica e stack

**Camadas:**

- **Ingestão:** conectores para discador/CRM (Olos, Weddo, EasyCollector) + upload de mailing; ETL para um data lake operacional.
- **Núcleo de ML:** feature store → modelo de propensão a pagar (gradient boosting, explicável, barato e auditável antes de qualquer coisa mais pesada) → motor de "próxima melhor ação" (canal/horário/prioridade).
- **Camada generativa:** RAG sobre política da carteira + histórico do devedor, alimentando LLM que redige abordagem/negociação e resume casos; agente sugere a ação e, com aprovação, dispara via API do discador.
- **Saída:** console operacional (tema graphite/navy com acentos amber/teal) + relatórios de uplift e auditoria.

**Stack recomendada (MVP magro):**

- Backend de ML: **Python + FastAPI**; serviços de integração em Node/Express onde fizer sentido.
- Dados: **PostgreSQL + Redis**; fila leve (Redis/RabbitMQ).
- Frontend: **React 18 + Vite**.
- Deploy: cloud gerenciada simples. **Sem Kubernetes/Terraform no MVP** — é overkill e queima tempo. Observabilidade enxuta.
- **Não reconstruir** a versão "Enterprise" de 10k linhas agora. MVP magro primeiro; complexidade só quando a receita justificar.

---

## 8. Roadmap de MVP — 90 dias

Meta única do MVP: **provar uplift de recuperação em uma carteira real e converter o piloto em contrato anual.**

| Janela | Entregas | Objetivo de saída |
|---|---|---|
| **Dias 1–30** | 1 conector (o discador do 1º piloto), ingestão de mailing + resultados, score de propensão v1, dashboard de priorização | Rodar sobre uma carteira real |
| **Dias 31–60** | Orquestração de canal/horário + relatório de uplift A/B (tratado × controle) | **Provar aumento de recuperação (%)** |
| **Dias 61–90** | Redação de abordagem via LLM com humano no loop + trilha de auditoria (LGPD) | Fechar o piloto pago como contrato anual |

**Regra de ouro:** cada semana deve avançar a métrica de uplift, não a lista de features. Se uma feature não move recuperação, ela espera.

---

## 9. Roadmap de 12 meses

- **Trimestre 2:** 3–5 conectores; onboarding autoatendível; primeiros contratos anuais.
- **Trimestre 3:** motor de simulação de acordo; multi-carteira/multi-tenant; começo do benchmark entre clientes.
- **Trimestre 4:** expansão inicial LatAm (Espanhol); primeiros sinais de expansão para order-to-cash em clientes B2B.
- **Meta de 12 meses:** 15–30 clientes pagantes, uplift comprovado replicável, NRR > 110%.

---

## 10. Go-to-market e funil de vendas

**Motor:** venda direta consultiva. Você conhece o comprador e fala a língua da operação.

**Funil:**

1. Lista de assessorias e fintechs de crédito (LatAm).
2. **Diagnóstico gratuito de carteira** (gera insight e cria urgência).
3. **Piloto pago de 60 dias com meta de uplift** contratualizada.
4. Conversão em contrato anual.
5. Expansão por assentos, carteiras e canais.

**Marketing:** conteúdo técnico de nicho (LinkedIn — seu terreno), estudos de caso de uplift, parcerias com integradores de discador. **Sem mídia paga cara** no início — o filtro do venture studio exige um negócio que não dependa de publicidade.

---

## 11. Métricas-chave (KPIs)

- **Uplift de recuperação (%)** — a métrica que vende. Sempre medida com grupo de controle.
- **CPC** e produtividade de operador.
- **DSO / tempo de recuperação** da carteira.
- **ARR, NRR** (expansão líquida), **churn logo**.
- **CAC payback** e ciclo médio de venda.
- **Tempo de integração** de um novo cliente (fosso operacional).

---

## 12. Time inicial e custos

**Time enxuto:**

- Você — produto e engenharia.
- 1 vendas/CS com domínio de cobrança (pode entrar como sócio comissionado no início).
- 1 engenheiro de dados **somente** quando o volume justificar.

**Custos iniciais (baixos por design):**

- Cloud + inferência de LLM (comece com modelos baratos e RAG enxuto; custo cresce com uso, não antes).
- Seu tempo.
- **Contratar só depois do primeiro contrato anual assinado.** O modelo escala sem crescimento proporcional de equipe — critério nº 5 do filtro.

---

## 13. Internacionalização

- **LatAm primeiro** (Português → Espanhol): dores idênticas, mesmos discadores, produto já multi-idioma via LLM.
- **Depois:** mercados com alta inadimplência digital e infraestrutura de cobrança fragmentada.
- **Alavanca:** o mesmo motor e os mesmos conectores atendem novos mercados com custo marginal baixo.

---

## 14. Projeções financeiras (cenário ilustrativo)

> Premissas: ACV inicial de ~R$48 mil/ano (SMB) a ~R$180 mil/ano (mid-market); churn baixo por custo de troca; NRR > 110% via expansão. **Números são cenário de raciocínio, não previsão.**

| Horizonte | Clientes (ordem) | ARR (ordem de grandeza) | Marcos |
|---|---|---|---|
| **Ano 1** | 15–30 | ~R$1–2 M | Uplift comprovado, primeiros contratos anuais |
| **Ano 3** | 150–300 | ~R$20–40 M | Expansão + início LatAm + subida ao order-to-cash |
| **Ano 5** | — | ordem de US$30–60 M | Internacionalização e plataforma de recebíveis |

---

## 15. Riscos e mitigação

| Risco | Tipo | Mitigação |
|---|---|---|
| Virar "feature" do discador incumbente | Comercial/estratégico | Neutralidade multi-discador; fosso de dado cross-cliente; velocidade |
| Setor de cobrança percebido como estressado | Comercial | Ancorar ROI em caixa recuperado; expandir para order-to-cash saudável |
| LGPD e regras de cobrança | Regulatório | Humano no loop, explicabilidade, trilha de auditoria; nunca autonomia total |
| Venda depende de provar uplift | Comercial | Piloto pago com grupo de controle e meta contratualizada |
| Dado de entrada sujo/inconsistente | Técnico | ETL robusto + começar por 1 conector maduro antes de escalar |
| Dependência de um único cliente-âncora | Comercial | Diversificar cedo; não desenhar o produto para uma só carteira |

---

## 16. Caminho para valuation > US$100 M

SaaS vertical com fosso de dados costuma negociar em torno de **~8–15× ARR**. A US$100 M de valuation corresponde, nessa faixa, a **~US$8–12 M de ARR** — plausível no Ano 3–4 se três alavancas estiverem provadas:

1. **Fosso de dados de resultado** que melhora a previsão com escala.
2. **NRR > 120%** via expansão de cobrança para order-to-cash.
3. **Uplift replicável e medível** entre clientes (a evidência que sustenta o múltiplo).

O múltiplo não vem do tamanho do código nem da quantidade de features — vem da prova de que o produto aumenta recuperação de forma repetível e defensável.

---

## 17. Próximos passos imediatos (30 dias)

1. **Escolher o cliente-piloto** com discador acessível e disposição a medir uplift.
2. **Construir o 1º conector + score v1 + dashboard de priorização** (Dias 1–30 do MVP).
3. **Contratualizar o piloto pago de 60 dias** com grupo de controle e meta de uplift.
4. **Instrumentar a medição de uplift desde o dia 1** — é o ativo comercial mais valioso.
5. **Recrutar o parceiro de vendas/CS** com domínio de cobrança (comissionado).

---

*Fim do documento — v1.0. Próxima revisão após fechar o primeiro piloto e medir o uplift real.*
