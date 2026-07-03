"""Analisador de qualidade de ligações da operadora (ALO / NÃO ALO).

Avalia **exclusivamente a qualidade da ligação entregue pela operadora
telefônica ao discador** — não avalia o operador humano. Cada ligação é
classificada (ALO REAL, NÃO ALO, URA, CAIXA POSTAL, SECRETÁRIA, MUDO, RUÍDO,
OCUPADO, OPERADORA, DISCADOR, OUTRO) combinando transcrição, contexto e
metadados (CDR/SIP/AMD).

Dois modos de análise:

- **IA (Claude)** — usa o modelo ``claude-opus-4-8`` com saída estruturada em
  JSON quando o pacote ``anthropic`` está instalado e ``ANTHROPIC_API_KEY``
  está configurada. Ativado por padrão (``ALO_USAR_IA=true``).
- **Heurística** — regras determinísticas sobre palavras-chave de ALO,
  marcadores de não-ALO e metadados. É o *fallback* automático (sem chave, sem
  rede, ou em caso de erro da API) e roda 100% offline.

O resultado (:class:`AnaliseResultado`) responde às 13 tarefas do prompt-mestre,
mais métricas de tempo, score final (0-100) e recomendações.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Optional

from .config import CFG
from .logging_setup import get_logger

log = get_logger("alo")

# ── Vocabulário de classificação (task 3 do prompt-mestre) ──────────────────
ALO_REAL = "ALO REAL"
NAO_ALO = "NÃO ALO"
URA = "URA"
CAIXA_POSTAL = "CAIXA POSTAL"
SECRETARIA = "SECRETÁRIA"
MUDO = "MUDO"
RUIDO = "RUÍDO"
OCUPADO = "OCUPADO"
OPERADORA = "OPERADORA"
DISCADOR = "DISCADOR"
OUTRO = "OUTRO"

CLASSIFICACOES = [
    ALO_REAL, NAO_ALO, URA, CAIXA_POSTAL, SECRETARIA,
    MUDO, RUIDO, OCUPADO, OPERADORA, DISCADOR, OUTRO,
]

QUEM_DESLIGOU = ["Cliente", "Operador", "Operadora", "Sistema", "Desconhecido"]
NIVEIS_PREJUIZO = ["Nenhum", "Baixo", "Médio", "Alto", "Crítico"]
ENTREGA = ["SIM", "PARCIALMENTE", "NÃO"]
INDICIOS = [
    "Silêncio excessivo", "Ruído", "Eco", "Perda de áudio",
    "Cliente falando sozinho", "Operador entrou atrasado",
    "Ligação caiu", "Transferência lenta", "Sem falhas",
]

# ── Palavras-chave de atendimento humano (ALO) ──────────────────────────────
# Comparadas contra texto normalizado (minúsculo, sem acento).
PALAVRAS_ALO = [
    "alo", "oi", "quem fala", "pois nao", "pronto", "sim", "diga", "fala",
    "estou ouvindo", "pode falar", "quem e", "quem eh", "boa tarde",
    "boa noite", "bom dia", "boa manha", "estou na linha", "alguem",
    "tem alguem", "ta me ouvindo", "esta me ouvindo", "quem gostaria",
]

# Marcadores que indicam NÃO-ALO (mensagem automática / máquina).
MARC_CAIXA_POSTAL = [
    "caixa postal", "correio de voz", "deixe sua mensagem", "apos o sinal",
    "apos o bipe", "deixe seu recado", "nao pode atender", "nao esta disponivel",
    "grave sua mensagem",
]
MARC_SECRETARIA = [
    "secretaria eletronica", "grave seu recado apos", "atendedor automatico",
]
MARC_URA = [
    "digite", "tecle", "pressione", "para falar com", "menu de opcoes",
    "aguarde na linha", "sua ligacao e importante", "horario de atendimento",
    "para atendimento", "opcao", "disque", "retornaremos",
]
MARC_ERRO_DISCAGEM = [
    "numero chamado nao existe", "nao existe", "verifique o numero discado",
    "numero incorreto", "assinante nao existe", "chamada nao pode ser completada",
]

FALANTES_CLIENTE = {"cliente", "chamado", "destino", "pessoa", "consumidor"}
FALANTES_OPERADOR = {"operador", "agente", "atendente", "operadora_agente"}


def _norm(texto: str) -> str:
    """Normaliza para comparação: minúsculo, sem acento, espaços colapsados."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t.lower()).strip()


def _contem(texto_norm: str, marcadores: list[str]) -> Optional[str]:
    for m in marcadores:
        if m in texto_norm:
            return m
    return None


# ── Estruturas de entrada ───────────────────────────────────────────────────
@dataclass
class Turno:
    """Uma fala da transcrição."""
    falante: str
    texto: str
    inicio_seg: Optional[float] = None  # offset do início da fala na ligação

    @property
    def eh_cliente(self) -> bool:
        return _norm(self.falante) in FALANTES_CLIENTE

    @property
    def eh_operador(self) -> bool:
        return _norm(self.falante) in FALANTES_OPERADOR


@dataclass
class Ligacao:
    """Dados técnicos + transcrição de uma ligação (entrada da análise)."""
    numero_chamado: str = ""
    numero_origem: str = ""
    data: str = ""
    hora: str = ""
    operadora: str = ""

    # Métricas técnicas (segundos)
    duracao_total_seg: float = 0.0
    tempo_ate_conexao_seg: float = 0.0
    tempo_fala_seg: float = 0.0
    tempo_silencio_seg: float = 0.0
    tempo_espera_seg: float = 0.0
    tempo_transferencia_seg: float = 0.0
    tempo_ate_primeiro_alo_seg: Optional[float] = None

    codigo_encerramento: str = ""
    causa_sip: str = ""
    amd: str = ""              # "Humano" | "Maquina" | "" (desconhecido)
    transferencia: bool = False

    transcricao: str = ""             # transcrição livre (opcional)
    turnos: list[Turno] = field(default_factory=list)  # transcrição estruturada

    def obter_turnos(self) -> list[Turno]:
        """Retorna os turnos estruturados, parseando ``transcricao`` se preciso."""
        if self.turnos:
            return self.turnos
        return _parse_transcricao(self.transcricao)

    def texto_completo(self) -> str:
        if self.turnos:
            return " ".join(t.texto for t in self.turnos)
        return self.transcricao


_RE_FALANTE = re.compile(
    r"^\s*(cliente|agente|operador|operadora|atendente|destino|chamado|ura|sistema)"
    r"\s*[:\-]",
    re.IGNORECASE,
)


def _parse_transcricao(texto: str) -> list[Turno]:
    """Converte transcrição livre em turnos, detectando rótulos de falante.

    Aceita o formato ``Cliente:\\n"Alô"\\n\\nAgente:\\n...`` e variações. Linhas
    sem rótulo são anexadas ao turno corrente.
    """
    if not texto or not texto.strip():
        return []
    turnos: list[Turno] = []
    falante_atual: Optional[str] = None
    buffer: list[str] = []

    def _flush() -> None:
        if falante_atual is not None:
            conteudo = " ".join(buffer).strip().strip('"').strip()
            if conteudo:
                turnos.append(Turno(falante=falante_atual, texto=conteudo))
        buffer.clear()

    for linha in texto.splitlines():
        m = _RE_FALANTE.match(linha)
        if m:
            _flush()
            falante_atual = m.group(1)
            resto = linha[m.end():].strip()
            if resto:
                buffer.append(resto)
        elif falante_atual is not None:
            if linha.strip():
                buffer.append(linha.strip())
        elif linha.strip():
            # Texto antes de qualquer rótulo — trata como fala anônima do cliente.
            falante_atual = "cliente"
            buffer.append(linha.strip())
    _flush()
    return turnos


# ── Estrutura de saída ──────────────────────────────────────────────────────
@dataclass
class Metricas:
    tempo_ate_primeiro_alo_seg: Optional[float] = None
    tempo_ate_primeiro_audio_seg: Optional[float] = None
    tempo_ate_primeiro_operador_seg: Optional[float] = None
    tempo_silencio_seg: float = 0.0
    tempo_util_seg: float = 0.0
    tempo_perdido_seg: float = 0.0
    tempo_morto_seg: float = 0.0


@dataclass
class AnaliseResultado:
    # 1-2
    houve_alo: bool = False
    grau_confianca: int = 0
    # 3-4
    classificacao: str = OUTRO
    justificativa: str = ""
    # 5
    quem_desligou: str = "Desconhecido"
    # 6
    houve_atraso: bool = False
    tempo_atraso_seg: float = 0.0
    # 7
    atraso_prejudicou: str = "Nenhum"
    # 8
    operadora_entregou: str = "SIM"
    # 9
    indicios_falha: list[str] = field(default_factory=list)
    # 10-12
    prob_falha_operadora: int = 0
    prob_falha_discador: int = 0
    prob_falha_agente: int = 0
    # 13
    evidencias: list[str] = field(default_factory=list)
    # extras
    metricas: Metricas = field(default_factory=Metricas)
    score_final: int = 0
    recomendacoes: list[str] = field(default_factory=list)
    falso_positivo_alo: bool = False
    falso_negativo_alo: bool = False
    origem: str = "heuristica"  # "ia" | "heuristica"

    def to_dict(self) -> dict:
        return asdict(self)


# ── Prompt-mestre (usado no modo IA) ────────────────────────────────────────
MASTER_PROMPT = """\
Você é um Especialista Sênior em Telecom, Discadores Automáticos, Operações de \
Cobrança e IA aplicada a Contact Centers, com profundo conhecimento em \
operadoras telefônicas, SIP, discadores preditivos, AMD (Answering Machine \
Detection), CPA (Call Progress Analysis), VoIP, URA, CDR e transcrição.

Sua missão NÃO é avaliar o operador humano. Sua missão é avaliar \
EXCLUSIVAMENTE a qualidade da ligação entregue pela operadora telefônica ao \
discador.

Para cada ligação, combine transcrição, contexto e metadados (CDR/SIP/AMD) e \
classifique-a em UMA categoria: ALO REAL, NÃO ALO, URA, CAIXA POSTAL, \
SECRETÁRIA, MUDO, RUÍDO, OCUPADO, OPERADORA, DISCADOR ou OUTRO.

Considere ALO quando houver atendimento humano real — palavras como "Alô", \
"Oi", "Quem fala?", "Pois não?", "Pronto", "Sim?", "Diga", "Boa tarde", ou \
qualquer interação natural, mesmo sem a palavra "Alô". NÃO considere ALO: \
caixa postal, secretária eletrônica, URA, música, silêncio, apenas respiração, \
apenas ruído, bip, ou chamada encerrada antes da fala.

Detecte erro de entrega da operadora quando o cliente diz "Alô...", "Alguém?", \
"Tá me ouvindo?" e só depois de vários segundos o operador entra (atraso na \
entrega). Detecte FALSO ALO (operadora marcou humano, mas era máquina) e FALSO \
NÃO ALO (cliente atendeu, mas foi marcado como não-alo).

Responda SOMENTE com um objeto JSON válido, sem texto adicional, seguindo \
exatamente o schema fornecido. Seja objetivo e cite trechos literais como \
evidências.
"""

# JSON Schema para saída estruturada (output_config.format).
_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "houve_alo": {"type": "boolean"},
        "grau_confianca": {"type": "integer"},
        "classificacao": {"type": "string", "enum": CLASSIFICACOES},
        "justificativa": {"type": "string"},
        "quem_desligou": {"type": "string", "enum": QUEM_DESLIGOU},
        "houve_atraso": {"type": "boolean"},
        "tempo_atraso_seg": {"type": "number"},
        "atraso_prejudicou": {"type": "string", "enum": NIVEIS_PREJUIZO},
        "operadora_entregou": {"type": "string", "enum": ENTREGA},
        "indicios_falha": {"type": "array", "items": {"type": "string", "enum": INDICIOS}},
        "prob_falha_operadora": {"type": "integer"},
        "prob_falha_discador": {"type": "integer"},
        "prob_falha_agente": {"type": "integer"},
        "evidencias": {"type": "array", "items": {"type": "string"}},
        "score_final": {"type": "integer"},
        "recomendacoes": {"type": "array", "items": {"type": "string"}},
        "falso_positivo_alo": {"type": "boolean"},
        "falso_negativo_alo": {"type": "boolean"},
    },
    "required": [
        "houve_alo", "grau_confianca", "classificacao", "justificativa",
        "quem_desligou", "houve_atraso", "tempo_atraso_seg", "atraso_prejudicou",
        "operadora_entregou", "indicios_falha", "prob_falha_operadora",
        "prob_falha_discador", "prob_falha_agente", "evidencias", "score_final",
        "recomendacoes", "falso_positivo_alo", "falso_negativo_alo",
    ],
}


def _clamp_int(v, lo: int = 0, hi: int = 100) -> int:
    try:
        return max(lo, min(hi, int(round(float(v)))))
    except (TypeError, ValueError):
        return lo


# ── Métricas ────────────────────────────────────────────────────────────────
def _calcular_metricas(lig: Ligacao, turnos: list[Turno]) -> Metricas:
    m = Metricas()
    m.tempo_ate_primeiro_audio_seg = lig.tempo_ate_conexao_seg or None
    m.tempo_silencio_seg = lig.tempo_silencio_seg

    # Primeiro ALO
    if lig.tempo_ate_primeiro_alo_seg is not None:
        m.tempo_ate_primeiro_alo_seg = lig.tempo_ate_primeiro_alo_seg
    else:
        for t in turnos:
            if t.eh_cliente and _contem(_norm(t.texto), PALAVRAS_ALO) and t.inicio_seg is not None:
                m.tempo_ate_primeiro_alo_seg = t.inicio_seg
                break

    # Primeiro operador
    for t in turnos:
        if t.eh_operador and t.inicio_seg is not None:
            m.tempo_ate_primeiro_operador_seg = t.inicio_seg
            break

    m.tempo_util_seg = lig.tempo_fala_seg
    m.tempo_perdido_seg = round(lig.tempo_silencio_seg + lig.tempo_espera_seg, 2)
    m.tempo_morto_seg = round(
        max(0.0, lig.tempo_ate_conexao_seg) + lig.tempo_silencio_seg, 2
    )
    return m


def _grau_prejuizo(atraso: float) -> str:
    if atraso < 1.5:
        return "Nenhum"
    if atraso < 3.0:
        return "Baixo"
    if atraso < 5.0:
        return "Médio"
    if atraso < 8.0:
        return "Alto"
    return "Crítico"


# ── Análise heurística (offline) ────────────────────────────────────────────
def _analisar_heuristica(lig: Ligacao) -> AnaliseResultado:
    r = AnaliseResultado(origem="heuristica")
    turnos = lig.obter_turnos()
    r.metricas = _calcular_metricas(lig, turnos)

    texto_norm = _norm(lig.texto_completo())
    amd_norm = _norm(lig.amd)
    cod = _norm(lig.codigo_encerramento)
    sip = _norm(lig.causa_sip)

    turnos_cliente = [t for t in turnos if t.eh_cliente]
    turnos_operador = [t for t in turnos if t.eh_operador]
    tem_texto = bool(texto_norm)

    # Palavras de ALO ditas pelo cliente (evidência forte de humano).
    alo_cliente = None
    for t in turnos_cliente:
        achou = _contem(_norm(t.texto), PALAVRAS_ALO)
        if achou:
            alo_cliente = t
            break
    # Se não há turnos rotulados, procura ALO no texto inteiro.
    alo_texto = _contem(texto_norm, PALAVRAS_ALO) if not turnos_cliente else None

    # Marcadores de não-ALO.
    mc_caixa = _contem(texto_norm, MARC_CAIXA_POSTAL)
    mc_secr = _contem(texto_norm, MARC_SECRETARIA)
    mc_ura = _contem(texto_norm, MARC_URA)
    mc_erro = _contem(texto_norm, MARC_ERRO_DISCAGEM)

    evid: list[str] = []
    recs: list[str] = []
    indicios: list[str] = []

    # ── Árvore de decisão ────────────────────────────────────────────────
    if mc_erro or "unallocated" in sip or "no route" in sip or cod in {"3", "cause_3"}:
        r.classificacao = DISCADOR
        r.houve_alo = False
        r.grau_confianca = 88
        r.justificativa = "Número inexistente/erro de discagem (marcador ou causa SIP)."
        r.operadora_entregou = "SIM"
        r.prob_falha_discador = 80
        r.quem_desligou = "Sistema"
        if mc_erro:
            evid.append(f"Mensagem: '{mc_erro}'")
        recs.append("Revisar higienização do mailing e validação de telefones.")

    elif cod in {"busy", "ocupado"} or "busy" in sip or "486" in sip:
        r.classificacao = OCUPADO
        r.houve_alo = False
        r.grau_confianca = 92
        r.justificativa = "Tom de ocupado (busy) — número em uso."
        r.operadora_entregou = "SIM"
        r.quem_desligou = "Sistema"
        recs.append("Reagendar contato — linha ocupada não é falha de entrega.")

    elif mc_caixa or (amd_norm in {"maquina", "machine"} and not (alo_cliente or alo_texto)):
        r.classificacao = CAIXA_POSTAL
        r.houve_alo = False
        r.grau_confianca = 90 if mc_caixa else 75
        r.justificativa = "Caixa postal / correio de voz detectado."
        r.operadora_entregou = "SIM"
        r.quem_desligou = "Sistema"
        if mc_caixa:
            evid.append(f"Mensagem automática: '{mc_caixa}'")
        recs.append("Não transferir chamadas classificadas como caixa postal ao agente.")

    elif mc_secr:
        r.classificacao = SECRETARIA
        r.houve_alo = False
        r.grau_confianca = 85
        r.justificativa = "Secretária eletrônica detectada."
        r.operadora_entregou = "SIM"
        r.quem_desligou = "Sistema"
        evid.append(f"Mensagem automática: '{mc_secr}'")

    elif mc_ura:
        r.classificacao = URA
        r.houve_alo = False
        r.grau_confianca = 82
        r.justificativa = "Atendimento eletrônico/URA (menu de opções ou instruções)."
        r.operadora_entregou = "SIM"
        r.quem_desligou = "Sistema"
        evid.append(f"URA: '{mc_ura}'")
        recs.append("Ajustar AMD para reduzir transferências de URA ao agente.")

    elif alo_cliente or alo_texto:
        r.classificacao = ALO_REAL
        r.houve_alo = True
        r.operadora_entregou = "SIM"
        r.quem_desligou = "Desconhecido"
        trecho = alo_cliente.texto if alo_cliente else lig.texto_completo()[:80]
        evid.append(f"Cliente: '{trecho}'")
        # AMD marcou máquina mas houve humano → falso negativo do AMD.
        if amd_norm in {"maquina", "machine"}:
            r.falso_negativo_alo = True
            r.grau_confianca = 80
            r.justificativa = (
                "Atendimento humano confirmado na transcrição, porém o AMD "
                "marcou máquina (falso negativo de ALO)."
            )
            recs.append("Recalibrar AMD — humano classificado como máquina.")
        else:
            r.grau_confianca = 95
            r.justificativa = "O cliente respondeu com saudação/interação humana natural."
    elif not tem_texto and lig.tempo_silencio_seg >= max(3.0, lig.duracao_total_seg * 0.6):
        r.classificacao = MUDO
        r.houve_alo = False
        r.grau_confianca = 85
        r.justificativa = "Ligação permaneceu muda durante todo o período."
        r.operadora_entregou = "NÃO"
        r.quem_desligou = "Operadora"
        indicios.append("Silêncio excessivo")
        r.prob_falha_operadora = 70
        recs.append("Auditar a operadora — ligações mudas indicam falha na entrega de áudio.")

    else:
        # Sem marcadores claros. Se AMD diz humano, damos benefício da dúvida.
        if amd_norm in {"humano", "human"}:
            r.classificacao = ALO_REAL
            r.houve_alo = True
            r.grau_confianca = 60
            r.justificativa = (
                "AMD indicou humano, mas a transcrição não traz uma saudação "
                "explícita — confiança reduzida."
            )
            r.operadora_entregou = "PARCIALMENTE"
        else:
            r.classificacao = OUTRO
            r.houve_alo = False
            r.grau_confianca = 40
            r.justificativa = "Sinais insuficientes para classificação conclusiva."
            r.operadora_entregou = "PARCIALMENTE"
        r.quem_desligou = "Desconhecido"

    # ── Detecção de atraso na entrega (task 6/7) ─────────────────────────
    m = r.metricas
    if (
        r.houve_alo
        and m.tempo_ate_primeiro_alo_seg is not None
        and m.tempo_ate_primeiro_operador_seg is not None
    ):
        atraso = m.tempo_ate_primeiro_operador_seg - m.tempo_ate_primeiro_alo_seg
        if atraso > 1.5:
            r.houve_atraso = True
            r.tempo_atraso_seg = round(atraso, 2)
            r.atraso_prejudicou = _grau_prejuizo(atraso)
            indicios.append("Operador entrou atrasado")
            evid.append(
                f"Cliente falou aos {m.tempo_ate_primeiro_alo_seg:.1f}s; "
                f"operador entrou aos {m.tempo_ate_primeiro_operador_seg:.1f}s."
            )
    # Cliente falando sozinho: múltiplos turnos do cliente antes do 1º operador.
    if r.houve_alo and turnos_operador:
        idx_op = turnos.index(turnos_operador[0])
        cliente_antes = sum(1 for t in turnos[:idx_op] if t.eh_cliente)
        if cliente_antes >= 2:
            if "Cliente falando sozinho" not in indicios:
                indicios.append("Cliente falando sozinho")
            if not r.houve_atraso:
                r.houve_atraso = True
                r.atraso_prejudicou = "Médio"
            recs.append(
                "Auditar sincronização do discador — cliente repetiu chamadas "
                "antes do operador."
            )

    # Transferência lenta.
    if lig.tempo_transferencia_seg and lig.tempo_transferencia_seg > 3.0:
        indicios.append("Transferência lenta")
        r.prob_falha_operadora = max(r.prob_falha_operadora, 40)

    # Silêncio excessivo em ligação com ALO.
    if r.houve_alo and lig.tempo_silencio_seg > max(4.0, lig.duracao_total_seg * 0.4):
        if "Silêncio excessivo" not in indicios:
            indicios.append("Silêncio excessivo")

    # Ligação caiu prematuramente.
    if lig.duracao_total_seg and lig.duracao_total_seg < 5.0 and r.houve_alo:
        indicios.append("Ligação caiu")
        r.quem_desligou = "Operadora" if r.quem_desligou == "Desconhecido" else r.quem_desligou
        recs.append("Investigar quedas prematuras — possível corte da operadora.")

    if not indicios:
        indicios.append("Sem falhas")
    r.indicios_falha = indicios

    # ── Falso positivo de ALO (operadora/AMD marcou humano, era máquina) ─
    if amd_norm in {"humano", "human"} and r.classificacao in {
        CAIXA_POSTAL, SECRETARIA, URA,
    }:
        r.falso_positivo_alo = True
        recs.append("Recalibrar AMD — mensagem automática marcada como humano.")

    # ── Probabilidades de origem da falha ────────────────────────────────
    if r.houve_atraso and r.atraso_prejudicou in {"Alto", "Crítico"}:
        r.prob_falha_operadora = max(r.prob_falha_operadora, 65)
        r.prob_falha_agente = min(r.prob_falha_agente + 15, 40)
    if r.classificacao == MUDO:
        r.prob_falha_operadora = max(r.prob_falha_operadora, 70)
    if r.classificacao == DISCADOR:
        r.prob_falha_discador = max(r.prob_falha_discador, 80)
    if "Transferência lenta" in indicios:
        r.prob_falha_operadora = max(r.prob_falha_operadora, 45)

    # ── Score final (0-100) ──────────────────────────────────────────────
    score = 100
    if not r.houve_alo and r.classificacao in {MUDO, RUIDO, OPERADORA}:
        score -= 45
    if r.houve_atraso:
        score -= {"Nenhum": 0, "Baixo": 8, "Médio": 18, "Alto": 30, "Crítico": 45}[
            r.atraso_prejudicou
        ]
    if r.operadora_entregou == "PARCIALMENTE":
        score -= 15
    elif r.operadora_entregou == "NÃO":
        score -= 40
    if r.falso_positivo_alo or r.falso_negativo_alo:
        score -= 20
    if "Transferência lenta" in indicios:
        score -= 10
    if "Ligação caiu" in indicios:
        score -= 15
    r.score_final = max(0, min(100, score))

    r.evidencias = evid or ["(sem trechos textuais — análise baseada em metadados)"]
    if not recs:
        recs.append("Nenhuma ação corretiva necessária para esta ligação.")
    r.recomendacoes = recs
    return r


# ── Análise via Claude (IA) ─────────────────────────────────────────────────
def _montar_entrada_ia(lig: Ligacao) -> str:
    turnos = lig.obter_turnos()
    if turnos:
        linhas = []
        for t in turnos:
            ts = f" [{t.inicio_seg:.1f}s]" if t.inicio_seg is not None else ""
            linhas.append(f"{t.falante}{ts}: {t.texto}")
        transcricao = "\n".join(linhas)
    else:
        transcricao = lig.transcricao or "(sem transcrição)"

    metadados = {
        "numero_chamado": lig.numero_chamado,
        "operadora": lig.operadora,
        "data": lig.data,
        "hora": lig.hora,
        "duracao_total_seg": lig.duracao_total_seg,
        "tempo_ate_conexao_seg": lig.tempo_ate_conexao_seg,
        "tempo_fala_seg": lig.tempo_fala_seg,
        "tempo_silencio_seg": lig.tempo_silencio_seg,
        "tempo_espera_seg": lig.tempo_espera_seg,
        "tempo_transferencia_seg": lig.tempo_transferencia_seg,
        "tempo_ate_primeiro_alo_seg": lig.tempo_ate_primeiro_alo_seg,
        "codigo_encerramento": lig.codigo_encerramento,
        "causa_sip": lig.causa_sip,
        "amd": lig.amd,
        "transferencia": lig.transferencia,
    }
    return (
        "METADADOS (CDR/SIP/AMD):\n"
        + json.dumps(metadados, ensure_ascii=False, indent=2)
        + "\n\nTRANSCRIÇÃO:\n"
        + transcricao
    )


def _analisar_ia(lig: Ligacao) -> Optional[AnaliseResultado]:
    """Tenta analisar via Claude. Retorna ``None`` para acionar o fallback."""
    try:
        import anthropic
    except ImportError:
        log.info("Pacote 'anthropic' não instalado — usando heurística.")
        return None

    if not CFG.ANTHROPIC_API_KEY:
        log.info("ANTHROPIC_API_KEY não configurada — usando heurística.")
        return None

    try:
        client = anthropic.Anthropic(api_key=CFG.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=CFG.ANTHROPIC_MODEL,
            max_tokens=4000,
            thinking={"type": "adaptive"},
            system=MASTER_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": _JSON_SCHEMA}},
            messages=[{"role": "user", "content": _montar_entrada_ia(lig)}],
        )
        if resp.stop_reason == "refusal":
            log.warning("Claude recusou a análise — usando heurística.")
            return None
        texto = next((b.text for b in resp.content if b.type == "text"), "")
        dados = json.loads(texto)
    except Exception as e:  # rede, auth, parse, schema — fallback seguro
        log.warning(f"Falha na análise via Claude ({e}) — usando heurística.")
        return None

    r = AnaliseResultado(origem="ia")
    r.houve_alo = bool(dados.get("houve_alo"))
    r.grau_confianca = _clamp_int(dados.get("grau_confianca", 0))
    r.classificacao = dados.get("classificacao", OUTRO)
    r.justificativa = dados.get("justificativa", "")
    r.quem_desligou = dados.get("quem_desligou", "Desconhecido")
    r.houve_atraso = bool(dados.get("houve_atraso"))
    r.tempo_atraso_seg = float(dados.get("tempo_atraso_seg", 0) or 0)
    r.atraso_prejudicou = dados.get("atraso_prejudicou", "Nenhum")
    r.operadora_entregou = dados.get("operadora_entregou", "SIM")
    r.indicios_falha = list(dados.get("indicios_falha", [])) or ["Sem falhas"]
    r.prob_falha_operadora = _clamp_int(dados.get("prob_falha_operadora", 0))
    r.prob_falha_discador = _clamp_int(dados.get("prob_falha_discador", 0))
    r.prob_falha_agente = _clamp_int(dados.get("prob_falha_agente", 0))
    r.evidencias = list(dados.get("evidencias", []))
    r.score_final = _clamp_int(dados.get("score_final", 0))
    r.recomendacoes = list(dados.get("recomendacoes", []))
    r.falso_positivo_alo = bool(dados.get("falso_positivo_alo"))
    r.falso_negativo_alo = bool(dados.get("falso_negativo_alo"))
    # Métricas são determinísticas — sempre calculadas localmente.
    r.metricas = _calcular_metricas(lig, lig.obter_turnos())
    return r


# ── API pública ─────────────────────────────────────────────────────────────
class AnalisadorLigacao:
    """Fachada do analisador de ligações ALO / NÃO ALO."""

    @staticmethod
    def analisar(lig: Ligacao, usar_ia: Optional[bool] = None) -> AnaliseResultado:
        """Analisa uma ligação e devolve o :class:`AnaliseResultado`.

        ``usar_ia=None`` respeita a configuração ``ALO_USAR_IA``. Em qualquer
        falha da IA (sem chave, sem rede, erro de API) cai automaticamente na
        heurística offline.
        """
        if usar_ia is None:
            usar_ia = CFG.ALO_USAR_IA
        if usar_ia:
            resultado = _analisar_ia(lig)
            if resultado is not None:
                return resultado
        return _analisar_heuristica(lig)

    @staticmethod
    def analisar_dict(payload: dict, usar_ia: Optional[bool] = None) -> dict:
        """Versão orientada a dict (útil em APIs). Aceita ``turnos`` como lista
        de dicts ``{falante, texto, inicio_seg}``."""
        turnos_raw = payload.pop("turnos", None) or []
        turnos = [
            Turno(
                falante=t.get("falante", "cliente"),
                texto=t.get("texto", ""),
                inicio_seg=t.get("inicio_seg"),
            )
            for t in turnos_raw
        ]
        campos = {f.name for f in Ligacao.__dataclass_fields__.values()}
        lig = Ligacao(**{k: v for k, v in payload.items() if k in campos})
        lig.turnos = turnos
        return AnalisadorLigacao.analisar(lig, usar_ia=usar_ia).to_dict()


ANALISADOR = AnalisadorLigacao()
