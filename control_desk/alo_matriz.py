"""Matriz de confusão e métricas de acurácia do robô ALO (validação estatística).

Compara a classificação do **robô** contra o **rótulo humano** (auditoria) e
produz: matriz de confusão, acurácia, precisão/recall/F1 por classe, quebra por
operadora e **calibração das faixas de decisão** (a faixa "automática" está mesmo
acertando mais que a "auditoria humana"?).

Entrada: uma lista de itens (ou um CSV) com, por ligação:
  - ``classificacao_humana``  (rótulo verdadeiro — obrigatório)
  - ``classificacao_robo``    (predição; se ausente, o robô é rodado sobre a linha)
  - ``operadora``, ``grau_confianca``, ``decisao`` (opcionais)

Sem predição do robô, as demais colunas (``transcricao``/``amd``/``causa_sip``/…)
são usadas para rodar o analisador e obter classe, confiança e decisão.
"""
from __future__ import annotations

import csv as _csv
from typing import Optional

from .alo_analyzer import ANALISADOR, CLASSIFICACOES
from .logging_setup import get_logger

log = get_logger("alo_matriz")


def _norm(s: str) -> str:
    return (s or "").strip().upper()


# ── Núcleo: matriz e métricas ───────────────────────────────────────────────
def avaliar(pares: list[tuple[str, str]]) -> dict:
    """``pares`` = lista de (humano, robo). Devolve matriz + métricas por classe."""
    pares = [(_norm(h), _norm(r)) for h, r in pares if h and r]
    classes = [c for c in CLASSIFICACOES]  # ordem canônica
    for h, r in pares:  # inclui rótulos fora do vocabulário padrão, se houver
        for c in (h, r):
            if c not in classes:
                classes.append(c)

    matriz = {h: {r: 0 for r in classes} for h in classes}
    for h, r in pares:
        matriz[h][r] += 1

    total = len(pares)
    acertos = sum(matriz[c][c] for c in classes)
    por_classe = {}
    for c in classes:
        suporte = sum(matriz[c].values())                    # reais desta classe
        preditos = sum(matriz[h][c] for h in classes)        # preditos como esta classe
        tp = matriz[c][c]
        if suporte == 0 and preditos == 0:
            continue
        recall = tp / suporte if suporte else 0.0
        precisao = tp / preditos if preditos else 0.0
        f1 = (2 * precisao * recall / (precisao + recall)) if (precisao + recall) else 0.0
        por_classe[c] = {
            "suporte": suporte, "precisao": round(precisao, 3),
            "recall": round(recall, 3), "f1": round(f1, 3),
        }
    macro_f1 = round(sum(m["f1"] for m in por_classe.values()) / len(por_classe), 3) if por_classe else 0.0
    return {
        "total": total,
        "acuracia": round(acertos / total, 3) if total else 0.0,
        "macro_f1": macro_f1,
        "classes": [c for c in classes if c in por_classe],
        "matriz": {h: matriz[h] for h in classes if h in por_classe or sum(matriz[h].values())},
        "por_classe": por_classe,
    }


def por_operadora(itens: list[dict]) -> dict:
    """Acurácia por operadora."""
    ops: dict[str, list[bool]] = {}
    for it in itens:
        op = it.get("operadora") or "(sem operadora)"
        ops.setdefault(op, []).append(_norm(it["classificacao_humana"]) == _norm(it["classificacao_robo"]))
    return {
        op: {"n": len(v), "acuracia": round(sum(v) / len(v), 3)}
        for op, v in sorted(ops.items(), key=lambda x: -len(x[1]))
    }


def calibracao(itens: list[dict]) -> dict:
    """Acurácia por faixa de decisão — valida se ≥90 acerta mais que <70.

    Se a acurácia da faixa 'automatica' não for a maior, os limiares precisam de ajuste.
    """
    faixas: dict[str, list[bool]] = {}
    for it in itens:
        d = it.get("decisao") or "(sem decisao)"
        faixas.setdefault(d, []).append(_norm(it["classificacao_humana"]) == _norm(it["classificacao_robo"]))
    ordem = ["automatica", "revisar_ia", "auditoria_humana"]
    out = {}
    for d in ordem + [f for f in faixas if f not in ordem]:
        if d in faixas:
            v = faixas[d]
            out[d] = {"n": len(v), "acuracia": round(sum(v) / len(v), 3)}
    return out


# ── Alto nível: avalia itens (rodando o robô quando preciso) ─────────────────
def avaliar_itens(itens: list[dict], modo: Optional[str] = None) -> dict:
    """Cada item precisa de ``classificacao_humana``. Se não trouxer
    ``classificacao_robo``, o robô é rodado sobre o próprio item."""
    enriquecidos = []
    for it in itens:
        humano = it.get("classificacao_humana")
        if not humano:
            continue
        item = dict(it)
        if not item.get("classificacao_robo"):
            payload = {k: v for k, v in it.items()
                       if k not in ("classificacao_humana", "classificacao_robo")}
            res = ANALISADOR.analisar_dict(payload, modo=modo)
            item["classificacao_robo"] = res["classificacao"]
            item.setdefault("grau_confianca", res["grau_confianca"])
            item.setdefault("decisao", res["decisao"])
            item.setdefault("operadora", it.get("operadora", ""))
        enriquecidos.append(item)

    pares = [(it["classificacao_humana"], it["classificacao_robo"]) for it in enriquecidos]
    rel = avaliar(pares)
    rel["por_operadora"] = por_operadora(enriquecidos)
    rel["calibracao_faixas"] = calibracao(enriquecidos)
    return rel


def avaliar_csv(caminho: str, modo: Optional[str] = None) -> dict:
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        amostra = f.read(2048)
        f.seek(0)
        delim = ";" if amostra.count(";") > amostra.count(",") else ","
        linhas = list(_csv.DictReader(f, delimiter=delim))
    return avaliar_itens(linhas, modo=modo)


# ── Relatório em texto ───────────────────────────────────────────────────────
def relatorio_texto(rel: dict) -> str:
    L = []
    L.append(f"ACURÁCIA GERAL: {rel['acuracia']:.1%}  (macro-F1 {rel['macro_f1']:.3f}, n={rel['total']})")
    L.append("")
    L.append("PRECISÃO / RECALL / F1 por classe:")
    L.append(f"  {'classe':<16}{'suporte':>8}{'precisao':>10}{'recall':>9}{'f1':>7}")
    for c, m in rel["por_classe"].items():
        L.append(f"  {c:<16}{m['suporte']:>8}{m['precisao']:>10.3f}{m['recall']:>9.3f}{m['f1']:>7.3f}")
    if rel.get("calibracao_faixas"):
        L.append("")
        L.append("CALIBRAÇÃO das faixas de decisão (a 'automatica' deve ter a maior acurácia):")
        for d, v in rel["calibracao_faixas"].items():
            L.append(f"  {d:<18} acurácia {v['acuracia']:.1%}  (n={v['n']})")
    if rel.get("por_operadora"):
        L.append("")
        L.append("ACURÁCIA por operadora:")
        for op, v in rel["por_operadora"].items():
            L.append(f"  {op:<18} {v['acuracia']:.1%}  (n={v['n']})")
    # Matriz compacta
    classes = rel["classes"]
    if classes:
        L.append("")
        L.append("MATRIZ DE CONFUSÃO (linha = humano, coluna = robô):")
        larg = max(10, *(len(c) for c in classes))
        abrev = {c: c[:6] for c in classes}
        L.append(" " * (larg + 2) + "".join(f"{abrev[c]:>8}" for c in classes))
        for h in classes:
            L.append(f"  {h:<{larg}}" + "".join(f"{rel['matriz'][h][r]:>8}" for r in classes))
    return "\n".join(L)
