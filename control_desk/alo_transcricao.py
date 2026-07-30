"""Transcrição de áudio para o robô ALO (áudio → texto).

Ponte opcional entre gravações de ligação (.mp3/.wav) e o analisador, que
trabalha com **texto**. Duas realidades de produção:

- **O discador já entrega transcrição** (ex.: Olos): não precisa deste módulo —
  mande o texto direto para o robô (``/alo/lote`` / ``/alo/call``).
- **Só há o áudio**: este módulo transcreve localmente com ``faster-whisper``.

Dependência opcional (``requirements-transcricao.txt``). Sem ela, ``disponivel()``
retorna ``False`` e as rotas de áudio respondem de forma clara, sem quebrar o robô.

Rede restrita (sem HuggingFace): baixe o modelo numa máquina com internet e aponte
``ALO_WHISPER_MODEL_DIR`` para a pasta do modelo — o carregamento é 100% offline.
"""
from __future__ import annotations

import os
import re
import struct
from typing import Optional

from .config import CFG
from .logging_setup import get_logger

log = get_logger("alo_transcricao")

_modelo = None
_carregado = False


class TranscricaoIndisponivel(RuntimeError):
    """Levantada quando o motor de transcrição não está instalado/carregável."""


def disponivel() -> bool:
    """True se o ``faster-whisper`` está instalado (motor de transcrição local)."""
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _get_modelo():
    global _modelo, _carregado
    if _carregado:
        if _modelo is None:
            raise TranscricaoIndisponivel(
                "Motor de transcrição indisponível. Instale: "
                "pip install -r requirements-transcricao.txt"
            )
        return _modelo
    _carregado = True
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        _modelo = None
        raise TranscricaoIndisponivel(
            "faster-whisper não instalado. pip install -r requirements-transcricao.txt"
        ) from e
    origem = CFG.ALO_WHISPER_MODEL_DIR or CFG.ALO_WHISPER_MODEL
    log.info(f"Carregando modelo de transcrição: {origem} ({CFG.ALO_WHISPER_DEVICE}/{CFG.ALO_WHISPER_COMPUTE})")
    _modelo = WhisperModel(origem, device=CFG.ALO_WHISPER_DEVICE, compute_type=CFG.ALO_WHISPER_COMPUTE)
    return _modelo


def transcrever(caminho: str, idioma: Optional[str] = None) -> str:
    """Transcreve um arquivo de áudio e devolve o texto (vazio se só silêncio)."""
    modelo = _get_modelo()
    segmentos, _ = modelo.transcribe(
        caminho, language=idioma or CFG.ALO_WHISPER_IDIOMA, vad_filter=True
    )
    return " ".join(s.text.strip() for s in segmentos).strip()


# ── Metadados do nome do arquivo de gravação (padrão Olos) ──────────────────
# Ex.: 1115829654_AuthLogin1722016105060_073999180792_454_7511_20260724_080025.mp3
def parse_nome_gravacao(nome: str) -> dict:
    """Extrai call_id, telefone, DDD, data e hora do nome do arquivo, quando presentes."""
    base = os.path.basename(nome)
    base = re.sub(r"\.(mp3|wav|ogg|m4a|flac)$", "", base, flags=re.IGNORECASE)
    p = base.split("_")
    tel = p[2] if len(p) > 2 and p[2].isdigit() else ""
    tel_norm = tel.lstrip("0")
    ddd = tel_norm[:2] if len(tel_norm) >= 10 else ""
    return {
        "call_id": p[0] if p else base,
        "numero_chamado": tel,
        "ddd": ddd,
        "data": p[-2] if len(p) >= 2 and re.fullmatch(r"\d{8}", p[-2] or "") else "",
        "hora": p[-1] if p and re.fullmatch(r"\d{6}", p[-1] or "") else "",
    }


# ── Duração de MP3 (CBR) sem depender de ffmpeg ─────────────────────────────
_BR1 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
_BR2 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]


def duracao_mp3(caminho: str) -> float:
    """Duração aproximada de um MP3 CBR (segundos). 0 se não conseguir estimar."""
    try:
        data = open(caminho, "rb").read()
    except OSError:
        return 0.0
    n = len(data)
    off = 0
    if data[:3] == b"ID3":
        off = 10 + ((data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9])
    i = off
    while i < min(n - 4, off + 20000):
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            h = struct.unpack(">I", data[i:i + 4])[0]
            ver = (h >> 19) & 3
            lay = (h >> 17) & 3
            bi = (h >> 12) & 0xF
            si = (h >> 10) & 3
            if lay == 1 and bi not in (0, 15) and si != 3:
                br = (_BR1 if ver == 3 else _BR2)[bi] * 1000
                audio = n - off - (128 if data[-128:-125] == b"TAG" else 0)
                return round(audio * 8 / br, 1) if br else 0.0
        i += 1
    return 0.0
