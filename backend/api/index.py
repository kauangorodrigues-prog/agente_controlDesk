"""Entrypoint serverless da Vercel para a API FastAPI (ASGI).

A Vercel detecta `app` como aplicação ASGI e a serve. As migrations são
aplicadas fora do runtime (via Alembic no processo de release), portanto aqui
apenas expomos a aplicação já configurada.
"""
from app.main import app  # noqa: F401
