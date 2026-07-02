#!/usr/bin/env python3
"""Cria ou atualiza um usuário da API (tabela api_users) com senha bcrypt.

A tabela `api_users` guarda a senha apenas como hash bcrypt, então este
script é a forma de cadastrar o primeiro administrador — sem ele não é
possível autenticar em /auth/token.

Exemplos:
    python scripts/create_user.py --username admin --role admin
    python scripts/create_user.py -u operador1 -r operador --password segredo123

Se --password for omitido, a senha é solicitada de forma interativa.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

# Garante que o módulo principal (na raiz do repo) seja importável
# mesmo quando o script é chamado como `python scripts/create_user.py`.
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)


def _carregar_dependencias():
    """Importa passlib e a camada de banco só quando necessário, para que
    `--help` funcione mesmo sem as dependências instaladas."""
    try:
        from passlib.context import CryptContext
    except ImportError:
        sys.exit("Erro: 'passlib[bcrypt]' não instalado. Rode: pip install -r requirements.txt")
    from agente_ia_control_desk import executar_comando, executar_query, testar_conexao
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_ctx, executar_comando, executar_query, testar_conexao


def criar_ou_atualizar_usuario(executar_comando, pwd_ctx, username: str, senha: str, role: str) -> None:
    hashed = pwd_ctx.hash(senha)
    executar_comando(
        """
        INSERT INTO api_users (username, hashed_pw, role, ativo)
        VALUES (:u, :h, :r, TRUE)
        ON CONFLICT (username) DO UPDATE
            SET hashed_pw = EXCLUDED.hashed_pw,
                role      = EXCLUDED.role,
                ativo     = TRUE
        """,
        {"u": username, "h": hashed, "r": role},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria/atualiza usuário da API.")
    parser.add_argument("-u", "--username", required=True, help="Nome de usuário")
    parser.add_argument("-r", "--role", default="operador",
                        choices=["admin", "operador"], help="Papel do usuário")
    parser.add_argument("-p", "--password", default=None,
                        help="Senha (se omitida, será solicitada interativamente)")
    args = parser.parse_args()

    pwd_ctx, executar_comando, executar_query, testar_conexao = _carregar_dependencias()

    if not testar_conexao():
        print("Erro: não foi possível conectar ao banco. Verifique o .env / schema.sql.",
              file=sys.stderr)
        return 1

    senha = args.password
    if not senha:
        senha = getpass.getpass("Senha: ")
        if senha != getpass.getpass("Confirme a senha: "):
            print("As senhas não conferem.", file=sys.stderr)
            return 1
    if len(senha) < 6:
        print("A senha deve ter ao menos 6 caracteres.", file=sys.stderr)
        return 1

    criar_ou_atualizar_usuario(executar_comando, pwd_ctx, args.username, senha, args.role)

    total = executar_query("SELECT COUNT(*) AS n FROM api_users WHERE ativo = TRUE")
    print(f"Usuário '{args.username}' (role={args.role}) criado/atualizado com sucesso.")
    print(f"Usuários ativos: {total[0]['n'] if total else '?'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
