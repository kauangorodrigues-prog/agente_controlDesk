"""
Módulo de conformidade com a LGPD (Lei nº 13.709/2018).

Fornece os controles de proteção de dados pessoais exigidos para um sistema de
cobrança/call center que trata dados de titulares (CPF, nome, telefone, e-mail):

  • Mascaramento de PII em respostas de API (art. 6º — necessidade/segurança).
  • Redação de PII nos logs da aplicação (art. 6º, VII — segurança).
  • Registro das operações de tratamento / acesso (art. 37 — registro).
  • Registro da base legal por campanha/finalidade (arts. 7º e 10).
  • Atendimento aos direitos do titular (art. 18):
        - confirmação da existência de tratamento (I) e acesso (II);
        - portabilidade / exportação (V);
        - anonimização (IV) e eliminação (VI).
  • Protocolo/rastreio das requisições de titular.
  • Política de retenção / descarte (arts. 15 e 16).

O módulo depende apenas da biblioteca padrão. As dependências de banco
(`executar_query`, `executar_comando`), a configuração e o logger são injetados
na inicialização via :func:`configurar`, evitando importar o monólito e seus
efeitos colaterais.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
from datetime import datetime
from typing import Any, Callable, Optional

# ── Estado injetado (ver configurar) ──────────────────────────────────────────
_log: logging.Logger = logging.getLogger("ControlDesk.LGPD")
_exec_query: Optional[Callable[..., list]] = None
_exec_cmd: Optional[Callable[..., int]] = None
_cfg: Any = None

# ── Expressões auxiliares ─────────────────────────────────────────────────────
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_FONE_RE = re.compile(r"\b(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

# Bases legais válidas para tratamento de dados pessoais (arts. 7º e 10 da LGPD).
BASES_LEGAIS = {
    "consentimento",
    "obrigacao_legal",
    "execucao_contrato",
    "exercicio_direitos",
    "protecao_credito",
    "legitimo_interesse",
    "politica_publica",
    "estudo_orgao_pesquisa",
    "protecao_vida",
    "tutela_saude",
}

# Onde vivem os dados pessoais dos titulares. Sobrescrevível via
# CFG.LGPD_FONTES_PII ou variável de ambiente LGPD_FONTES_PII (JSON).
FONTES_PII_PADRAO = [
    {
        "tabela": "mailing_scored",
        "coluna_cpf": "cpf",
        "colunas_pii": ["cpf", "nome", "telefone", "email"],
        "coluna_data": "captured_at",
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# Inicialização
# ══════════════════════════════════════════════════════════════════════════════
def configurar(executar_query, executar_comando, config=None, logger=None) -> None:
    """Injeta as dependências de banco/config/logger. Chamar uma vez no boot."""
    global _exec_query, _exec_cmd, _cfg, _log
    _exec_query = executar_query
    _exec_cmd = executar_comando
    if config is not None:
        _cfg = config
    if logger is not None:
        _log = logger.getChild("LGPD") if hasattr(logger, "getChild") else logger


def _garantir_config() -> None:
    if _exec_query is None or _exec_cmd is None:
        raise RuntimeError(
            "LGPD não configurado — chame lgpd.configurar(...) na inicialização."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Mascaramento de PII
# ══════════════════════════════════════════════════════════════════════════════
def _so_digitos(v: Any) -> str:
    return re.sub(r"\D", "", str(v or ""))


def mascarar_cpf(cpf: Any) -> str:
    d = _so_digitos(cpf)
    if len(d) != 11:
        return "***"
    return f"{d[:3]}.***.***-{d[9:]}"


def mascarar_telefone(fone: Any) -> str:
    d = _so_digitos(fone)
    if len(d) < 4:
        return "***"
    ddd = d[:2] if len(d) >= 10 else ""
    prefixo = f"({ddd}) " if ddd else ""
    return f"{prefixo}*****-**{d[-2:]}"


def mascarar_email(email: Any) -> str:
    s = str(email or "")
    if "@" not in s:
        return "***"
    usuario, dominio = s.split("@", 1)
    inicio = (usuario[:2] + "***") if len(usuario) > 2 else "***"
    return f"{inicio}@{dominio}"


def mascarar_nome(nome: Any) -> str:
    partes = str(nome or "").split()
    if not partes:
        return "***"
    if len(partes) == 1:
        return partes[0][:1] + "***"
    return partes[0] + " " + " ".join(p[:1] + "." for p in partes[1:])


_MASCARADORES = {
    "cpf": mascarar_cpf,
    "documento": mascarar_cpf,
    "telefone": mascarar_telefone,
    "celular": mascarar_telefone,
    "fone": mascarar_telefone,
    "whatsapp": mascarar_telefone,
    "email": mascarar_email,
    "e_mail": mascarar_email,
    "nome": mascarar_nome,
    "cliente": mascarar_nome,
    "titular": mascarar_nome,
    "contato": mascarar_nome,
}


def _mascarador_para(campo: str) -> Optional[Callable[[Any], str]]:
    c = campo.lower()
    for chave, fn in _MASCARADORES.items():
        if chave in c:
            return fn
    return None


def mascarar_registro(registro: dict, campos: Optional[set] = None) -> dict:
    """Retorna uma cópia do registro com os campos de PII mascarados."""
    out = dict(registro)
    for k, v in registro.items():
        if v is None:
            continue
        if campos is not None and k not in campos:
            continue
        fn = _mascarador_para(k)
        if fn:
            out[k] = fn(v)
    return out


def mascarar_registros(registros: list, campos: Optional[set] = None) -> list:
    return [mascarar_registro(r, campos) for r in registros]


class RedactingFilter(logging.Filter):
    """Filtro de logging que remove CPF/telefone/e-mail das mensagens (art. 6º)."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        try:
            msg = record.getMessage()
        except Exception:
            return True
        red = _EMAIL_RE.sub("[email removido]", msg)
        red = _CPF_RE.sub("[cpf removido]", red)
        red = _FONE_RE.sub("[telefone removido]", red)
        if red != msg:
            record.msg = red
            record.args = ()
        return True


# ══════════════════════════════════════════════════════════════════════════════
# Pseudonimização e validação
# ══════════════════════════════════════════════════════════════════════════════
def _salt() -> str:
    if _cfg is not None and getattr(_cfg, "LGPD_HASH_SALT", ""):
        return _cfg.LGPD_HASH_SALT
    return os.getenv("LGPD_HASH_SALT", "")


def hash_cpf(cpf: Any) -> str:
    """SHA-256 salgado do CPF — usado para rastrear titular sem armazenar o CPF."""
    d = _so_digitos(cpf)
    if not d:
        return ""
    return hashlib.sha256((_salt() + d).encode("utf-8")).hexdigest()


def validar_cpf(cpf: Any) -> bool:
    d = _so_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(d[j]) * ((i + 1) - j) for j in range(i))
        dig = (soma * 10) % 11
        dig = 0 if dig == 10 else dig
        if dig != int(d[i]):
            return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Fontes de dados pessoais
# ══════════════════════════════════════════════════════════════════════════════
def _ident_ok(nome: Any) -> bool:
    return bool(_IDENT_RE.match(str(nome or "")))


def _fontes() -> list:
    fontes = getattr(_cfg, "LGPD_FONTES_PII", None) if _cfg is not None else None
    if not fontes:
        env = os.getenv("LGPD_FONTES_PII", "")
        if env:
            try:
                fontes = json.loads(env)
            except Exception:
                _log.warning("LGPD_FONTES_PII inválido (JSON) — usando padrão")
    return fontes or FONTES_PII_PADRAO


def _fontes_validas() -> list:
    """Fontes com identificadores validados (defesa contra SQL injection)."""
    validas = []
    for f in _fontes():
        tab = f.get("tabela")
        col = f.get("coluna_cpf")
        if not _ident_ok(tab) or not _ident_ok(col):
            _log.warning("Fonte PII ignorada (identificador inválido): %r", f)
            continue
        cols = [c for c in f.get("colunas_pii", []) if _ident_ok(c)]
        validas.append({**f, "colunas_pii": cols})
    return validas


# ══════════════════════════════════════════════════════════════════════════════
# Registro de operações / acesso (art. 37)
# ══════════════════════════════════════════════════════════════════════════════
def registrar_acesso(usuario, acao, recurso, cpf=None, justificativa=None, ip=None) -> None:
    _garantir_config()
    try:
        _exec_cmd(
            """
            INSERT INTO lgpd_acesso_log (usuario, acao, recurso, cpf_hash, justificativa, ip)
            VALUES (:u, :a, :r, :h, :j, :ip)
            """,
            {
                "u": usuario,
                "a": acao,
                "r": recurso,
                "h": hash_cpf(cpf) if cpf else None,
                "j": justificativa,
                "ip": ip,
            },
        )
    except Exception as e:
        _log.error("Falha ao registrar acesso LGPD: %s", e)


def _registrar_evento(tipo, cpf, fontes, usuario) -> None:
    try:
        _exec_cmd(
            """
            INSERT INTO lgpd_titular_evento (tipo, cpf_hash, fontes, executado_por)
            VALUES (:t, :h, CAST(:f AS JSONB), :u)
            """,
            {"t": tipo, "h": hash_cpf(cpf), "f": json.dumps(fontes, default=str), "u": usuario},
        )
    except Exception as e:
        _log.error("Falha ao registrar evento LGPD (%s): %s", tipo, e)


# ══════════════════════════════════════════════════════════════════════════════
# Base legal por campanha/finalidade (arts. 7º e 10)
# ══════════════════════════════════════════════════════════════════════════════
def registrar_base_legal(campanha, finalidade, base_legal, observacao=None, criado_por="API") -> bool:
    _garantir_config()
    _exec_cmd(
        """
        INSERT INTO lgpd_base_legal (campanha, finalidade, base_legal, observacao, criado_por)
        VALUES (:c, :f, :b, :o, :p)
        ON CONFLICT (campanha, finalidade)
        DO UPDATE SET base_legal = EXCLUDED.base_legal,
                      observacao = EXCLUDED.observacao,
                      vigente    = TRUE,
                      criado_por = EXCLUDED.criado_por,
                      criado_em  = NOW()
        """,
        {"c": campanha, "f": finalidade, "b": base_legal, "o": observacao, "p": criado_por},
    )
    return True


def listar_bases_legais(campanha=None) -> list:
    _garantir_config()
    if campanha:
        return _exec_query(
            "SELECT * FROM lgpd_base_legal WHERE campanha = :c AND vigente ORDER BY finalidade",
            {"c": campanha},
        )
    return _exec_query("SELECT * FROM lgpd_base_legal WHERE vigente ORDER BY campanha, finalidade")


# ══════════════════════════════════════════════════════════════════════════════
# Direitos do titular (art. 18)
# ══════════════════════════════════════════════════════════════════════════════
def _consultar_fontes(cpf_digits: str, mascarar: bool) -> dict:
    resultado = {}
    for f in _fontes_validas():
        tab, col = f["tabela"], f["coluna_cpf"]
        try:
            rows = _exec_query(
                f"SELECT * FROM {tab} "
                f"WHERE regexp_replace({col}::text, '[^0-9]', '', 'g') = :cpf",
                {"cpf": cpf_digits},
            )
        except Exception as e:
            resultado[tab] = {"erro": str(e)}
            continue
        if mascarar:
            rows = mascarar_registros(rows)
        resultado[tab] = {"registros": len(rows), "dados": rows}
    return resultado


def confirmar_tratamento(cpf, usuario="API") -> dict:
    """Art. 18, I e II — confirmação da existência de tratamento e acesso (mascarado)."""
    _garantir_config()
    achado = _consultar_fontes(_so_digitos(cpf), mascarar=True)
    existe = any(
        isinstance(v, dict) and v.get("registros", 0) > 0 for v in achado.values()
    )
    registrar_acesso(usuario, "confirmar_tratamento", "titular", cpf=cpf)
    return {
        "cpf": mascarar_cpf(cpf),
        "possui_tratamento": existe,
        "fontes": achado,
        "bases_legais": listar_bases_legais(),
    }


def exportar_dados(cpf, usuario="API") -> dict:
    """Art. 18, V — portabilidade/exportação dos dados reais do titular."""
    _garantir_config()
    dados = _consultar_fontes(_so_digitos(cpf), mascarar=False)
    registrar_acesso(usuario, "exportar_dados", "titular", cpf=cpf, justificativa="portabilidade")
    return {
        "cpf": mascarar_cpf(cpf),
        "gerado_em": datetime.utcnow().isoformat() + "Z",
        "dados": dados,
    }


def anonimizar_titular(cpf, usuario="API") -> dict:
    """Art. 18, IV — anonimização: remove a identificabilidade preservando a linha."""
    _garantir_config()
    dig = _so_digitos(cpf)
    afetados: dict = {}
    for f in _fontes_validas():
        tab, col, pii = f["tabela"], f["coluna_cpf"], f.get("colunas_pii", [])
        if not pii:
            continue
        sets, params = [], {"cpf": dig}
        for c in pii:
            token = "ANONIMIZADO" if ("nome" in c.lower() or "cliente" in c.lower()) else None
            sets.append(f"{c} = :val_{c}")
            params[f"val_{c}"] = token
        try:
            afetados[tab] = _exec_cmd(
                f"UPDATE {tab} SET {', '.join(sets)} "
                f"WHERE regexp_replace({col}::text, '[^0-9]', '', 'g') = :cpf",
                params,
            )
        except Exception as e:
            afetados[tab] = {"erro": str(e)}
    _registrar_evento("anonimizacao", cpf, afetados, usuario)
    registrar_acesso(usuario, "anonimizar_titular", "titular", cpf=cpf)
    return {"cpf": mascarar_cpf(cpf), "afetados": afetados}


def eliminar_titular(cpf, usuario="API") -> dict:
    """Art. 18, VI — eliminação dos dados pessoais do titular."""
    _garantir_config()
    dig = _so_digitos(cpf)
    afetados: dict = {}
    for f in _fontes_validas():
        tab, col = f["tabela"], f["coluna_cpf"]
        try:
            afetados[tab] = _exec_cmd(
                f"DELETE FROM {tab} "
                f"WHERE regexp_replace({col}::text, '[^0-9]', '', 'g') = :cpf",
                {"cpf": dig},
            )
        except Exception as e:
            afetados[tab] = {"erro": str(e)}
    _registrar_evento("eliminacao", cpf, afetados, usuario)
    registrar_acesso(usuario, "eliminar_titular", "titular", cpf=cpf)
    return {"cpf": mascarar_cpf(cpf), "afetados": afetados}


# ══════════════════════════════════════════════════════════════════════════════
# Protocolo de requisições do titular
# ══════════════════════════════════════════════════════════════════════════════
def abrir_requisicao(tipo, cpf, solicitante="API", observacao=None) -> str:
    _garantir_config()
    protocolo = "LGPD-" + datetime.utcnow().strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()
    _exec_cmd(
        """
        INSERT INTO lgpd_requisicao_titular (protocolo, tipo, cpf_hash, status, solicitante, observacao)
        VALUES (:p, :t, :h, 'recebida', :s, :o)
        """,
        {"p": protocolo, "t": tipo, "h": hash_cpf(cpf), "s": solicitante, "o": observacao},
    )
    return protocolo


def concluir_requisicao(protocolo, status="concluida") -> None:
    _garantir_config()
    _exec_cmd(
        "UPDATE lgpd_requisicao_titular SET status = :st, atendido_em = NOW() WHERE protocolo = :p",
        {"st": status, "p": protocolo},
    )


# ══════════════════════════════════════════════════════════════════════════════
# Retenção / descarte (arts. 15 e 16)
# ══════════════════════════════════════════════════════════════════════════════
def aplicar_retencao(dias=None, usuario="scheduler") -> dict:
    """Elimina registros mais antigos que o prazo de retenção configurado."""
    _garantir_config()
    if dias is None:
        dias = getattr(_cfg, "LGPD_RETENCAO_DIAS", 1825) if _cfg is not None else 1825
    afetados: dict = {}
    for f in _fontes_validas():
        tab, datac = f["tabela"], f.get("coluna_data")
        if not datac or not _ident_ok(datac):
            afetados[tab] = "sem coluna_data configurada"
            continue
        try:
            afetados[tab] = _exec_cmd(
                f"DELETE FROM {tab} WHERE {datac} < NOW() - (:d || ' days')::interval",
                {"d": str(int(dias))},
            )
        except Exception as e:
            afetados[tab] = {"erro": str(e)}
    _registrar_evento("retencao", "", afetados, usuario)
    _log.info("Retenção LGPD aplicada (%s dias): %s", dias, afetados)
    return {"dias": int(dias), "afetados": afetados}
