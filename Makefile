# ============================================================
# Agente IA Control Desk — atalhos de desenvolvimento
# ============================================================
.PHONY: help install schema seed create-user api dashboard run test docker-up docker-down

help:
	@echo "Alvos disponíveis:"
	@echo "  install      Instala as dependências (requirements.txt)"
	@echo "  schema       Aplica db/schema.sql   (usa \$$DATABASE_URL)"
	@echo "  seed         Aplica db/seed_data.sql (usa \$$DATABASE_URL)"
	@echo "  create-user  Cadastra usuário da API (interativo)"
	@echo "  api          Sobe a API FastAPI (porta 8000)"
	@echo "  dashboard    Sobe o dashboard Streamlit (porta 8501)"
	@echo "  run          Modo standalone (scheduler)"
	@echo "  test         Roda os testes (pytest)"
	@echo "  docker-up    Sobe a stack via docker compose"
	@echo "  docker-down  Derruba a stack"

install:
	pip install -r requirements.txt

schema:
	psql "$(DATABASE_URL)" -f db/schema.sql

seed:
	psql "$(DATABASE_URL)" -f db/seed_data.sql

create-user:
	python scripts/create_user.py --username admin --role admin

api:
	python agente_ia_control_desk.py api

dashboard:
	streamlit run agente_ia_control_desk.py dashboard

run:
	python agente_ia_control_desk.py

test:
	pytest -q

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
