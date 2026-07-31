"""Transcreve e analisa uma pasta de gravações (.mp3/.wav) com o robô ALO.

Uso:
    pip install -r requirements-transcricao.txt
    python scripts/transcrever_pasta.py /caminho/das/gravacoes [--persistir] [--modo hibrido]

Exige o motor de transcrição (faster-whisper). Em rede restrita, baixe o modelo
antes e aponte ALO_WHISPER_MODEL_DIR (ver TRANSCRICAO.md).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control_desk import alo_transcricao  # noqa: E402
from control_desk.alo_service import AloService  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Transcreve e analisa gravações com o robô ALO.")
    ap.add_argument("pasta", help="Diretório com os arquivos .mp3/.wav")
    ap.add_argument("--persistir", action="store_true", help="Grava no banco (SQLite/Postgres)")
    ap.add_argument("--modo", default=None, help="heuristica | ia | hibrido")
    args = ap.parse_args()

    if not alo_transcricao.disponivel():
        print("ERRO: motor de transcrição indisponível. "
              "Instale: pip install -r requirements-transcricao.txt", file=sys.stderr)
        return 2
    if not os.path.isdir(args.pasta):
        print(f"ERRO: pasta não encontrada: {args.pasta}", file=sys.stderr)
        return 2

    resumo = AloService.processar_pasta(args.pasta, persistir=args.persistir, modo=args.modo)
    det = resumo.pop("detalhes", [])
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    print("\nPor ligação:")
    for d in det:
        print(f"  {d['call_id']:<12} {d['classificacao']:<14} alo={str(d['houve_alo']):<5} "
              f"conf={d['grau_confianca']:<3} decisao={d['decisao']:<16} dur={d.get('duracao_seg')}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
