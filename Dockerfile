# ============================================================
# Agente IA Control Desk — imagem de aplicação
# ============================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

# psycopg2-binary dispensa toolchain de compilação.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# API (8000) e Dashboard Streamlit (8501)
EXPOSE 8000 8501

# Sobe a API por padrão. Para o modo standalone (scheduler) use:
#   command: python agente_ia_control_desk.py
CMD ["python", "agente_ia_control_desk.py", "api"]
