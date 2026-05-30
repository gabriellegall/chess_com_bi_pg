.DEFAULT_GOAL := help

PYTHON ?= python
ifeq ($(OS),Windows_NT)
VENV_PYTHON := $(abspath venv/Scripts/python.exe)
else
VENV_PYTHON := $(abspath venv/bin/python)
endif
ifneq ("$(wildcard $(VENV_PYTHON))","")
PYTHON := $(VENV_PYTHON)
endif
DBT_DIR := dbt
STREAMLIT_DIR := streamlit
DBT_MODELS_DIR := models/

DOCKERHUB_USER ?= gabriellegall
DBT_IMAGE_LOCAL := chess-com-bi-pg-dbt
DBT_IMAGE_REMOTE := $(DOCKERHUB_USER)/chess-com-bi-pg-dbt:latest
STREAMLIT_IMAGE_LOCAL := chess-com-bi-pg-streamlit
STREAMLIT_IMAGE_REMOTE := $(DOCKERHUB_USER)/chess-com-bi-pg-streamlit:latest
POSTGRES_COMPOSE_SERVICE ?= analytical_db

RUN_ALL_SLEEP_TIME ?= 600
STREAMLIT_PORT ?= 8501

.PHONY: \
	help \
	run_all_with_reset run_all run_all_no_api \
	sqlfluff_lint sqlfluff_fix test_dbt_doc \
	streamlit_test streamlit_run \
	docker_build_project_dbt docker_hub_push_dbt docker_build_project_streamlit docker_hub_push_streamlit \
	docker_compose_postgres_up docker_compose_postgres_down

help:
	@echo "Available targets:"
	@echo "  run_all                     - Run orchestrator with API enabled"
	@echo "  run_all_no_api              - Run orchestrator with API disabled"
	@echo "  run_all_with_reset          - Reset dbt schemas and run orchestrator"
	@echo "  sqlfluff_lint               - Lint dbt models with SQLFluff"
	@echo "  sqlfluff_fix                - Auto-fix dbt SQL style issues"
	@echo "  test_dbt_doc                - Validate dbt docs consistency"
	@echo "  streamlit_test              - Run Streamlit test suite"
	@echo "  streamlit_run               - Run Streamlit app locally"
	@echo "  docker_build_project_dbt    - Build dbt Docker image"
	@echo "  docker_hub_push_dbt         - Build, tag and push dbt image"
	@echo "  docker_build_project_streamlit - Build Streamlit Docker image"
	@echo "  docker_hub_push_streamlit   - Build, tag and push Streamlit image"
	@echo "  docker_compose_postgres_up  - Start only Postgres service from docker-compose"
	@echo "  docker_compose_postgres_down - Stop only Postgres service from docker-compose"
	@echo ""
	@echo "Configurable variables (examples):"
	@echo "  make run_all RUN_ALL_SLEEP_TIME=60"
	@echo "  make streamlit_run STREAMLIT_PORT=8502"
	@echo "  make docker_compose_postgres_up POSTGRES_COMPOSE_SERVICE=analytical_db"

run_all_with_reset:
	@cd $(DBT_DIR) && $(PYTHON) run_all_with_reset.py

run_all:
	@cd $(DBT_DIR) && set SKIP_CHESS_COM_API=false && set SLEEP_TIME=$(RUN_ALL_SLEEP_TIME) && $(PYTHON) run_all.py

run_all_no_api:
	@cd $(DBT_DIR) && set SKIP_CHESS_COM_API=true && set SLEEP_TIME=0 && $(PYTHON) run_all.py

sqlfluff_lint:
	@cd $(DBT_DIR) && sqlfluff lint $(DBT_MODELS_DIR) --dialect postgres

sqlfluff_fix:
	@cd $(DBT_DIR) && sqlfluff fix $(DBT_MODELS_DIR) --dialect postgres

test_dbt_doc:
	@cd $(DBT_DIR) && $(PYTHON) scripts/test_doc.py

# Local execution : streamlit
streamlit_test:
	@cd $(STREAMLIT_DIR)/tests && $(PYTHON) -m pytest

streamlit_run:
	@cd $(STREAMLIT_DIR) && streamlit run app.py --server.port $(STREAMLIT_PORT)

# Docker Hub - dbt
docker_build_project_dbt:
	docker build -f Dockerfile.dbt -t $(DBT_IMAGE_LOCAL) .

docker_hub_push_dbt: docker_build_project_dbt
	docker tag $(DBT_IMAGE_LOCAL) $(DBT_IMAGE_REMOTE)
	docker push $(DBT_IMAGE_REMOTE)

# Docker Hub - Streamlit
docker_build_project_streamlit:
	docker build -f Dockerfile.streamlit -t $(STREAMLIT_IMAGE_LOCAL) .

docker_hub_push_streamlit: docker_build_project_streamlit
	docker tag $(STREAMLIT_IMAGE_LOCAL) $(STREAMLIT_IMAGE_REMOTE)
	docker push $(STREAMLIT_IMAGE_REMOTE)

# Docker Compose postgres only
docker_compose_postgres_up:
	docker-compose up -d $(POSTGRES_COMPOSE_SERVICE)

docker_compose_postgres_down:
	docker-compose stop $(POSTGRES_COMPOSE_SERVICE)
