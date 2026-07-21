# Imagem do robô Analisador de Ligações ALO / NÃO ALO
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ROBO_ALO_HOST=0.0.0.0 \
    ROBO_ALO_PORT=5501

WORKDIR /app

# Dependências primeiro (cache de camada)
COPY requirements-robo.txt .
RUN pip install --no-cache-dir -r requirements-robo.txt

# Código
COPY control_desk ./control_desk
COPY main.py ./

# Usuário não-root + diretórios graváveis (SQLite e logs)
RUN mkdir -p /app/data /app/logs \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app
USER app

EXPOSE 5501

# Health check nativo do container
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:'+__import__('os').getenv('ROBO_ALO_PORT','5501')+'/health',timeout=3).status==200 else sys.exit(1)"

CMD ["python", "main.py", "alo"]
