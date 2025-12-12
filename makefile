.PHONY: create-table populate-db run-api database_up database_down db_up db_down redis_up redis_down

create-table:
	alembic upgrade head

populate-db:
	python3 database/populate_db.py

run-api:
	uvicorn server:app --port 8000 --reload

# --- All services ---
# Start both Postgres and Redis containers
database_up:
	docker compose up -d

# Stop and remove all containers and volumes
database_down:
	docker compose down --volumes

# --- Individual services ---
# db_agent_ai
db_agent_ai_up:
	docker compose up -d db_agent_ai

db_agent_ai_down:
	docker compose stop db_agent_ai && docker compose rm -f db_agent_ai

# redis_agent_ai
redis_agent_ai_up:
	docker compose up -d redis_agent_ai

redis_agent_ai_down:
	docker stop redis_agent_ai && docker rm -f redis_agent_ai
