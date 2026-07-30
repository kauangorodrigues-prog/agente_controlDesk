#!/usr/bin/env python3
"""
Agente de Tarefas — gerenciador de demandas do dia a dia via CLI.

Ferramenta autônoma (usa apenas a biblioteca padrão do Python) para
organizar suas tarefas pessoais: criar, listar, priorizar, acompanhar
prazos e ver a agenda do dia direto no terminal.

Persistência: banco SQLite local. Por padrão em ~/.agente_tarefas/tarefas.db
(sobrescreva com a variável de ambiente AGENTE_TAREFAS_DB).

Exemplos rápidos:
    python agente_tarefas.py add "Ligar para o cliente X" -p alta -v amanha -c trabalho
    python agente_tarefas.py hoje
    python agente_tarefas.py listar --atrasadas
    python agente_tarefas.py concluir 3
    python agente_tarefas.py resumo
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# ══════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════════

PRIORIDADES = ["baixa", "media", "alta", "urgente"]
PRIORIDADE_ORDEM = {"urgente": 0, "alta": 1, "media": 2, "baixa": 3}
STATUS_VALIDOS = ["pendente", "em_andamento", "concluida", "cancelada"]
STATUS_ABERTOS = ("pendente", "em_andamento")


def _db_path() -> Path:
    override = os.getenv("AGENTE_TAREFAS_DB")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".agente_tarefas" / "tarefas.db"


# ══════════════════════════════════════════════════════════════════════
# CORES (ANSI) — desativa se a saída não for um terminal
# ══════════════════════════════════════════════════════════════════════

class C:
    _ativo = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
    RESET = "\033[0m" if _ativo else ""
    BOLD = "\033[1m" if _ativo else ""
    DIM = "\033[2m" if _ativo else ""
    RED = "\033[31m" if _ativo else ""
    GREEN = "\033[32m" if _ativo else ""
    YELLOW = "\033[33m" if _ativo else ""
    BLUE = "\033[34m" if _ativo else ""
    MAGENTA = "\033[35m" if _ativo else ""
    CYAN = "\033[36m" if _ativo else ""
    GRAY = "\033[90m" if _ativo else ""


COR_PRIORIDADE = {
    "urgente": C.RED + C.BOLD,
    "alta": C.RED,
    "media": C.YELLOW,
    "baixa": C.GRAY,
}

ICONE_STATUS = {
    "pendente": "○",
    "em_andamento": "◐",
    "concluida": "●",
    "cancelada": "✕",
}


# ══════════════════════════════════════════════════════════════════════
# BANCO DE DADOS
# ══════════════════════════════════════════════════════════════════════

def conectar() -> sqlite3.Connection:
    caminho = _db_path()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(caminho))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _criar_schema(conn)
    return conn


def _criar_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tarefas (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo       TEXT    NOT NULL,
            descricao    TEXT,
            prioridade   TEXT    NOT NULL DEFAULT 'media',
            status       TEXT    NOT NULL DEFAULT 'pendente',
            categoria    TEXT,
            vencimento   TEXT,
            criado_em    TEXT    NOT NULL,
            atualizado_em TEXT   NOT NULL,
            concluido_em TEXT
        )
        """
    )
    conn.commit()


# ══════════════════════════════════════════════════════════════════════
# UTILIDADES DE DATA
# ══════════════════════════════════════════════════════════════════════

def _hoje() -> date:
    return date.today()


def parse_data(texto: Optional[str]) -> Optional[str]:
    """Converte entrada flexível de data em ISO (YYYY-MM-DD).

    Aceita: hoje, amanha, ontem, seg/ter/.../dom (próxima ocorrência),
    +N (N dias a partir de hoje), DD/MM, DD/MM/YYYY, YYYY-MM-DD.
    Retorna None se texto for vazio. Lança ValueError se não reconhecer.
    """
    if not texto:
        return None
    t = texto.strip().lower()
    hoje = _hoje()

    atalhos = {"hoje": 0, "amanha": 1, "amanhã": 1, "ontem": -1}
    if t in atalhos:
        return (hoje + timedelta(days=atalhos[t])).isoformat()

    dias_semana = {
        "seg": 0, "ter": 1, "qua": 2, "qui": 3,
        "sex": 4, "sab": 5, "sáb": 5, "dom": 6,
    }
    if t[:3] in dias_semana:
        alvo = dias_semana[t[:3]]
        delta = (alvo - hoje.weekday()) % 7
        delta = delta or 7  # próxima ocorrência (nunca hoje)
        return (hoje + timedelta(days=delta)).isoformat()

    if t.startswith("+") and t[1:].isdigit():
        return (hoje + timedelta(days=int(t[1:]))).isoformat()

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d/%m"):
        try:
            dt = datetime.strptime(t, fmt).date()
            if fmt == "%d/%m":
                dt = dt.replace(year=hoje.year)
            return dt.isoformat()
        except ValueError:
            continue

    raise ValueError(
        f"Data '{texto}' não reconhecida. Use: hoje, amanha, +3, "
        f"sex, DD/MM ou YYYY-MM-DD."
    )


def _fmt_vencimento(iso: Optional[str]) -> str:
    """Formata o vencimento com rótulo humano e cor por urgência."""
    if not iso:
        return ""
    venc = date.fromisoformat(iso)
    dias = (venc - _hoje()).days
    rotulo = venc.strftime("%d/%m")
    if dias < 0:
        return f"{C.RED}{C.BOLD}⚠ {rotulo} (atrasada {abs(dias)}d){C.RESET}"
    if dias == 0:
        return f"{C.YELLOW}{C.BOLD}⏰ {rotulo} (hoje){C.RESET}"
    if dias == 1:
        return f"{C.YELLOW}{rotulo} (amanhã){C.RESET}"
    if dias <= 7:
        return f"{C.CYAN}{rotulo} (em {dias}d){C.RESET}"
    return f"{C.GRAY}{rotulo}{C.RESET}"


# ══════════════════════════════════════════════════════════════════════
# OPERAÇÕES (a lógica do "agente")
# ══════════════════════════════════════════════════════════════════════

def criar_tarefa(
    conn: sqlite3.Connection,
    titulo: str,
    descricao: Optional[str] = None,
    prioridade: str = "media",
    categoria: Optional[str] = None,
    vencimento: Optional[str] = None,
) -> int:
    if prioridade not in PRIORIDADES:
        raise ValueError(
            f"Prioridade inválida: '{prioridade}'. Use uma de {PRIORIDADES}."
        )
    agora = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """
        INSERT INTO tarefas
            (titulo, descricao, prioridade, status, categoria,
             vencimento, criado_em, atualizado_em)
        VALUES (?, ?, ?, 'pendente', ?, ?, ?, ?)
        """,
        (titulo.strip(), descricao, prioridade, categoria,
         vencimento, agora, agora),
    )
    conn.commit()
    return int(cur.lastrowid)


def buscar_por_id(conn: sqlite3.Connection, tid: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM tarefas WHERE id = ?", (tid,)).fetchone()


def mudar_status(conn: sqlite3.Connection, tid: int, status: str) -> bool:
    if status not in STATUS_VALIDOS:
        raise ValueError(f"Status inválido: '{status}'.")
    tarefa = buscar_por_id(conn, tid)
    if not tarefa:
        return False
    agora = datetime.now().isoformat(timespec="seconds")
    concluido = agora if status == "concluida" else None
    conn.execute(
        "UPDATE tarefas SET status=?, atualizado_em=?, concluido_em=? WHERE id=?",
        (status, agora, concluido, tid),
    )
    conn.commit()
    return True


def editar_tarefa(conn: sqlite3.Connection, tid: int, campos: dict) -> bool:
    if not buscar_por_id(conn, tid):
        return False
    if not campos:
        return True
    campos["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    sets = ", ".join(f"{k}=?" for k in campos)
    conn.execute(
        f"UPDATE tarefas SET {sets} WHERE id=?",
        (*campos.values(), tid),
    )
    conn.commit()
    return True


def remover_tarefa(conn: sqlite3.Connection, tid: int) -> bool:
    if not buscar_por_id(conn, tid):
        return False
    conn.execute("DELETE FROM tarefas WHERE id=?", (tid,))
    conn.commit()
    return True


def listar_tarefas(
    conn: sqlite3.Connection,
    status: Optional[str] = None,
    prioridade: Optional[str] = None,
    categoria: Optional[str] = None,
    somente_abertas: bool = False,
    atrasadas: bool = False,
    hoje: bool = False,
    ate_data: Optional[str] = None,
    busca: Optional[str] = None,
) -> list[sqlite3.Row]:
    clausulas = []
    params: list = []

    if status:
        clausulas.append("status = ?")
        params.append(status)
    elif somente_abertas:
        clausulas.append(f"status IN ({','.join('?' * len(STATUS_ABERTOS))})")
        params.extend(STATUS_ABERTOS)

    if prioridade:
        clausulas.append("prioridade = ?")
        params.append(prioridade)
    if categoria:
        clausulas.append("categoria = ?")
        params.append(categoria)
    if atrasadas:
        clausulas.append("vencimento IS NOT NULL AND vencimento < ?")
        params.append(_hoje().isoformat())
        clausulas.append(f"status IN ({','.join('?' * len(STATUS_ABERTOS))})")
        params.extend(STATUS_ABERTOS)
    if hoje:
        clausulas.append("vencimento = ?")
        params.append(_hoje().isoformat())
    if ate_data:
        clausulas.append("vencimento IS NOT NULL AND vencimento <= ?")
        params.append(ate_data)
    if busca:
        clausulas.append("(titulo LIKE ? OR descricao LIKE ? OR categoria LIKE ?)")
        termo = f"%{busca}%"
        params.extend([termo, termo, termo])

    where = f"WHERE {' AND '.join(clausulas)}" if clausulas else ""
    # Ordena por: prioridade (urgente→baixa), depois vencimento (nulos por último), depois id
    ordem = (
        "ORDER BY CASE prioridade "
        "WHEN 'urgente' THEN 0 WHEN 'alta' THEN 1 "
        "WHEN 'media' THEN 2 ELSE 3 END, "
        "vencimento IS NULL, vencimento ASC, id ASC"
    )
    sql = f"SELECT * FROM tarefas {where} {ordem}"
    return conn.execute(sql, params).fetchall()


# ══════════════════════════════════════════════════════════════════════
# APRESENTAÇÃO
# ══════════════════════════════════════════════════════════════════════

def _linha_tarefa(t: sqlite3.Row) -> str:
    cor_prio = COR_PRIORIDADE.get(t["prioridade"], "")
    icone = ICONE_STATUS.get(t["status"], "?")
    id_txt = f"{C.BOLD}#{t['id']:<3}{C.RESET}"
    prio_txt = f"{cor_prio}{t['prioridade']:<8}{C.RESET}"

    titulo = t["titulo"]
    if t["status"] == "concluida":
        titulo = f"{C.GRAY}{C.DIM}{titulo}{C.RESET}"
    elif t["status"] == "cancelada":
        titulo = f"{C.GRAY}{C.DIM}̶{titulo}{C.RESET}"

    partes = [f"{icone} {id_txt} {prio_txt} {titulo}"]
    if t["categoria"]:
        partes.append(f"{C.BLUE}[{t['categoria']}]{C.RESET}")
    venc = _fmt_vencimento(t["vencimento"])
    if venc:
        partes.append(venc)
    return "  ".join(partes)


def imprimir_lista(tarefas: list[sqlite3.Row], titulo: Optional[str] = None) -> None:
    if titulo:
        print(f"\n{C.BOLD}{C.CYAN}{titulo}{C.RESET}")
        print(f"{C.GRAY}{'─' * max(len(titulo), 40)}{C.RESET}")
    if not tarefas:
        print(f"{C.GRAY}  (nenhuma tarefa){C.RESET}")
        return
    for t in tarefas:
        print("  " + _linha_tarefa(t))


def imprimir_detalhe(t: sqlite3.Row) -> None:
    cor_prio = COR_PRIORIDADE.get(t["prioridade"], "")
    print(f"\n{C.BOLD}#{t['id']} — {t['titulo']}{C.RESET}")
    print(f"{C.GRAY}{'─' * 44}{C.RESET}")
    print(f"  Status......: {ICONE_STATUS.get(t['status'], '?')} {t['status']}")
    print(f"  Prioridade..: {cor_prio}{t['prioridade']}{C.RESET}")
    print(f"  Categoria...: {t['categoria'] or '—'}")
    venc = _fmt_vencimento(t["vencimento"]) or "—"
    print(f"  Vencimento..: {venc}")
    if t["descricao"]:
        print(f"  Descrição...: {t['descricao']}")
    print(f"{C.GRAY}  Criada em...: {t['criado_em']}{C.RESET}")
    if t["concluido_em"]:
        print(f"{C.GRAY}  Concluída em: {t['concluido_em']}{C.RESET}")


# ══════════════════════════════════════════════════════════════════════
# HANDLERS DE COMANDO
# ══════════════════════════════════════════════════════════════════════

def cmd_add(conn, args) -> int:
    try:
        vencimento = parse_data(args.vencimento)
    except ValueError as e:
        print(f"{C.RED}Erro: {e}{C.RESET}")
        return 1
    tid = criar_tarefa(
        conn,
        titulo=args.titulo,
        descricao=args.descricao,
        prioridade=args.prioridade,
        categoria=args.categoria,
        vencimento=vencimento,
    )
    print(f"{C.GREEN}✓ Tarefa #{tid} criada.{C.RESET}")
    imprimir_detalhe(buscar_por_id(conn, tid))
    return 0


def cmd_listar(conn, args) -> int:
    tarefas = listar_tarefas(
        conn,
        status=args.status,
        prioridade=args.prioridade,
        categoria=args.categoria,
        somente_abertas=not (args.todas or args.status),
        atrasadas=args.atrasadas,
        hoje=args.hoje,
        busca=args.buscar,
    )
    imprimir_lista(tarefas, titulo="Tarefas")
    print(f"\n{C.GRAY}Total: {len(tarefas)}{C.RESET}")
    return 0


def cmd_hoje(conn, args) -> int:
    hoje_iso = _hoje().isoformat()
    atrasadas = listar_tarefas(conn, atrasadas=True)
    do_dia = listar_tarefas(conn, hoje=True, somente_abertas=True)
    em_andamento = [
        t for t in listar_tarefas(conn, status="em_andamento")
        if t["vencimento"] != hoje_iso
        and not (t["vencimento"] and t["vencimento"] < hoje_iso)
    ]

    data_str = _hoje().strftime("%A, %d/%m/%Y")
    print(f"\n{C.BOLD}{C.CYAN}📅 Agenda de {data_str}{C.RESET}")

    imprimir_lista(atrasadas, titulo="⚠  Atrasadas")
    imprimir_lista(do_dia, titulo="⏰ Para hoje")
    imprimir_lista(em_andamento, titulo="◐  Em andamento")

    total = len(atrasadas) + len(do_dia) + len(em_andamento)
    if total == 0:
        print(f"\n{C.GREEN}Tudo em dia! Nada pendente para hoje. 🎉{C.RESET}")
    return 0


def cmd_concluir(conn, args) -> int:
    return _aplicar_status(conn, args.id, "concluida", "concluída ✓", C.GREEN)


def cmd_iniciar(conn, args) -> int:
    return _aplicar_status(conn, args.id, "em_andamento", "em andamento ◐", C.YELLOW)


def cmd_reabrir(conn, args) -> int:
    return _aplicar_status(conn, args.id, "pendente", "reaberta ○", C.CYAN)


def cmd_cancelar(conn, args) -> int:
    return _aplicar_status(conn, args.id, "cancelada", "cancelada ✕", C.GRAY)


def _aplicar_status(conn, tid, status, rotulo, cor) -> int:
    if mudar_status(conn, tid, status):
        print(f"{cor}Tarefa #{tid} marcada como {rotulo}.{C.RESET}")
        return 0
    print(f"{C.RED}Tarefa #{tid} não encontrada.{C.RESET}")
    return 1


def cmd_editar(conn, args) -> int:
    campos: dict = {}
    if args.titulo is not None:
        campos["titulo"] = args.titulo
    if args.descricao is not None:
        campos["descricao"] = args.descricao
    if args.prioridade is not None:
        if args.prioridade not in PRIORIDADES:
            print(f"{C.RED}Prioridade inválida: {args.prioridade}{C.RESET}")
            return 1
        campos["prioridade"] = args.prioridade
    if args.categoria is not None:
        campos["categoria"] = args.categoria
    if args.vencimento is not None:
        try:
            campos["vencimento"] = parse_data(args.vencimento) if args.vencimento else None
        except ValueError as e:
            print(f"{C.RED}Erro: {e}{C.RESET}")
            return 1
    if not campos:
        print(f"{C.YELLOW}Nada para editar. Informe ao menos um campo.{C.RESET}")
        return 1
    if editar_tarefa(conn, args.id, campos):
        print(f"{C.GREEN}✓ Tarefa #{args.id} atualizada.{C.RESET}")
        imprimir_detalhe(buscar_por_id(conn, args.id))
        return 0
    print(f"{C.RED}Tarefa #{args.id} não encontrada.{C.RESET}")
    return 1


def cmd_remover(conn, args) -> int:
    tarefa = buscar_por_id(conn, args.id)
    if not tarefa:
        print(f"{C.RED}Tarefa #{args.id} não encontrada.{C.RESET}")
        return 1
    if not args.sim:
        resp = input(f"Remover #{args.id} '{tarefa['titulo']}'? [s/N] ").strip().lower()
        if resp not in ("s", "sim", "y", "yes"):
            print("Cancelado.")
            return 0
    remover_tarefa(conn, args.id)
    print(f"{C.GREEN}Tarefa #{args.id} removida.{C.RESET}")
    return 0


def cmd_ver(conn, args) -> int:
    tarefa = buscar_por_id(conn, args.id)
    if not tarefa:
        print(f"{C.RED}Tarefa #{args.id} não encontrada.{C.RESET}")
        return 1
    imprimir_detalhe(tarefa)
    return 0


def cmd_resumo(conn, args) -> int:
    todas = conn.execute("SELECT status, prioridade, vencimento FROM tarefas").fetchall()
    total = len(todas)
    por_status = {s: 0 for s in STATUS_VALIDOS}
    abertas_por_prio = {p: 0 for p in PRIORIDADES}
    atrasadas = 0
    hoje_iso = _hoje().isoformat()

    for t in todas:
        por_status[t["status"]] = por_status.get(t["status"], 0) + 1
        if t["status"] in STATUS_ABERTOS:
            abertas_por_prio[t["prioridade"]] = abertas_por_prio.get(t["prioridade"], 0) + 1
            if t["vencimento"] and t["vencimento"] < hoje_iso:
                atrasadas += 1

    print(f"\n{C.BOLD}{C.CYAN}📊 Resumo das tarefas{C.RESET}")
    print(f"{C.GRAY}{'─' * 40}{C.RESET}")
    print(f"  Total cadastradas...: {total}")
    print(f"  {C.CYAN}○ Pendentes.........: {por_status['pendente']}{C.RESET}")
    print(f"  {C.YELLOW}◐ Em andamento......: {por_status['em_andamento']}{C.RESET}")
    print(f"  {C.GREEN}● Concluídas........: {por_status['concluida']}{C.RESET}")
    print(f"  {C.GRAY}✕ Canceladas........: {por_status['cancelada']}{C.RESET}")
    if atrasadas:
        print(f"  {C.RED}{C.BOLD}⚠ Atrasadas.........: {atrasadas}{C.RESET}")
    print(f"\n{C.BOLD}  Abertas por prioridade:{C.RESET}")
    for p in PRIORIDADES:
        cor = COR_PRIORIDADE.get(p, "")
        print(f"    {cor}{p:<8}{C.RESET}: {abertas_por_prio[p]}")

    concluidas = por_status["concluida"]
    finalizadas = concluidas + por_status["cancelada"]
    if finalizadas:
        taxa = 100 * concluidas / finalizadas
        print(f"\n{C.GRAY}  Taxa de conclusão: {taxa:.0f}%{C.RESET}")
    return 0


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="agente_tarefas",
        description="Agente de tarefas — gerencie suas demandas do dia a dia.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  agente_tarefas add \"Enviar relatório\" -p alta -v amanha -c trabalho\n"
            "  agente_tarefas hoje\n"
            "  agente_tarefas listar --atrasadas\n"
            "  agente_tarefas concluir 3\n"
            "  agente_tarefas resumo\n"
        ),
    )
    sub = p.add_subparsers(dest="comando", metavar="comando")

    # add
    a = sub.add_parser("add", aliases=["nova"], help="Cria uma nova tarefa")
    a.add_argument("titulo", help="Título da tarefa")
    a.add_argument("-d", "--descricao", help="Descrição/detalhes")
    a.add_argument("-p", "--prioridade", default="media", choices=PRIORIDADES,
                   help="Prioridade (padrão: media)")
    a.add_argument("-c", "--categoria", help="Categoria/projeto (ex: trabalho)")
    a.add_argument("-v", "--vencimento",
                   help="Prazo: hoje, amanha, +3, sex, DD/MM ou YYYY-MM-DD")
    a.set_defaults(func=cmd_add)

    # listar
    l = sub.add_parser("listar", aliases=["ls", "lista"], help="Lista tarefas")
    l.add_argument("-s", "--status", choices=STATUS_VALIDOS, help="Filtra por status")
    l.add_argument("-p", "--prioridade", choices=PRIORIDADES, help="Filtra por prioridade")
    l.add_argument("-c", "--categoria", help="Filtra por categoria")
    l.add_argument("--atrasadas", action="store_true", help="Só as vencidas e abertas")
    l.add_argument("--hoje", action="store_true", help="Só as que vencem hoje")
    l.add_argument("--todas", action="store_true", help="Inclui concluídas/canceladas")
    l.add_argument("-b", "--buscar", help="Busca por texto")
    l.set_defaults(func=cmd_listar)

    # hoje / agenda
    h = sub.add_parser("hoje", aliases=["agenda"], help="Agenda do dia (atrasadas + hoje)")
    h.set_defaults(func=cmd_hoje)

    # ver
    v = sub.add_parser("ver", aliases=["show"], help="Mostra detalhes de uma tarefa")
    v.add_argument("id", type=int)
    v.set_defaults(func=cmd_ver)

    # editar
    e = sub.add_parser("editar", aliases=["edit"], help="Edita campos de uma tarefa")
    e.add_argument("id", type=int)
    e.add_argument("-t", "--titulo")
    e.add_argument("-d", "--descricao")
    e.add_argument("-p", "--prioridade", choices=PRIORIDADES)
    e.add_argument("-c", "--categoria")
    e.add_argument("-v", "--vencimento", help="Novo prazo (vazio '' remove)")
    e.set_defaults(func=cmd_editar)

    # transições de status
    for nome, alias, func, ajuda in [
        ("concluir", ["done", "ok"], cmd_concluir, "Marca como concluída"),
        ("iniciar", ["start"], cmd_iniciar, "Marca como em andamento"),
        ("reabrir", [], cmd_reabrir, "Reabre (volta a pendente)"),
        ("cancelar", [], cmd_cancelar, "Cancela a tarefa"),
    ]:
        s = sub.add_parser(nome, aliases=alias, help=ajuda)
        s.add_argument("id", type=int)
        s.set_defaults(func=func)

    # remover
    r = sub.add_parser("remover", aliases=["rm"], help="Remove uma tarefa")
    r.add_argument("id", type=int)
    r.add_argument("-y", "--sim", action="store_true", help="Não pede confirmação")
    r.set_defaults(func=cmd_remover)

    # resumo
    rs = sub.add_parser("resumo", aliases=["stats"], help="Estatísticas gerais")
    rs.set_defaults(func=cmd_resumo)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "comando", None):
        # Sem comando: mostra a agenda do dia como tela inicial útil.
        with conectar() as conn:
            return cmd_hoje(conn, args)

    with conectar() as conn:
        try:
            return args.func(conn, args)
        except ValueError as e:
            print(f"{C.RED}Erro: {e}{C.RESET}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
