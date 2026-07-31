"""Matriz de confusão do robô ALO — robô × auditoria humana.

Uso:
    python scripts/matriz_confusao.py auditoria.csv [--modo hibrido]

CSV (separador ; ou ,) com uma linha por ligação:
  classificacao_humana   (rótulo verdadeiro — obrigatório)
  classificacao_robo     (opcional; se ausente, o robô é rodado sobre a linha
                          usando transcricao/amd/causa_sip/etc.)
  operadora, grau_confianca, decisao   (opcionais)

Sem argumento, roda uma demonstração com dados sintéticos.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control_desk import alo_matriz  # noqa: E402


def _demo() -> dict:
    # Rótulos humanos + predições do robô (sintético, só p/ mostrar o formato).
    itens = []
    plano = [("ALO REAL", "ALO REAL", "Claro", 95, "automatica")] * 40
    plano += [("ALO REAL", "CAIXA POSTAL", "Vivo", 72, "revisar_ia")] * 5   # erros
    plano += [("CAIXA POSTAL", "CAIXA POSTAL", "Vivo", 90, "automatica")] * 25
    plano += [("URA", "URA", "Tim", 82, "revisar_ia")] * 12
    plano += [("MUDO", "MUDO", "Tim", 85, "revisar_ia")] * 10
    plano += [("MUDO", "OUTRO", "Oi", 40, "auditoria_humana")] * 4          # duvidosos
    plano += [("OCUPADO", "OCUPADO", "Claro", 92, "automatica")] * 8
    for h, r, op, cf, dec in plano:
        itens.append({"classificacao_humana": h, "classificacao_robo": r,
                      "operadora": op, "grau_confianca": cf, "decisao": dec})
    return alo_matriz.avaliar_itens(itens)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    modo = None
    if "--modo" in sys.argv:
        i = sys.argv.index("--modo")
        modo = sys.argv[i + 1] if i + 1 < len(sys.argv) else None

    if not args:
        print(">>> DEMONSTRAÇÃO com dados sintéticos (passe um CSV real para valer) <<<\n")
        rel = _demo()
    else:
        if not os.path.isfile(args[0]):
            print(f"ERRO: arquivo não encontrado: {args[0]}", file=sys.stderr)
            return 2
        rel = alo_matriz.avaliar_csv(args[0], modo=modo)

    print(alo_matriz.relatorio_texto(rel))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
