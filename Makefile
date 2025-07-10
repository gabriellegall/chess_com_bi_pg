# Local execution (forward slash for Linux)
stg_games:
	@cd scripts/chess_com_api && python chess_games_pipeline.py

stg_games_times:
	@cd scripts/games_times && python chess_games_times_pipeline.py

stg_games_moves:
	@cd scripts/stockfish && python chess_games_moves_pipeline.py

dbt_build:
	dbt build

stg_all: stg_games stg_games_times stg_games_moves

run_all: stg_all dbt_build

# Docker Desktop
CURDIR := $(shell cd)
docker_build_project:
	docker build -t chess-com-bi-pg .

docker_run_project:
	docker run --rm -it chess-com-bi-pg

# Docker Hub
docker_hub_push: docker_build_project
	docker tag chess-com-bi-pg gabriellegall/chess-com-bi-pg:latest
	docker push gabriellegall/chess-com-bi-pg:latest

docker_hub_pull_and_run:
	docker pull gabriellegall/chess-com-bi-pg:latest
	docker run --rm -it -v ${CURDIR}/data:/app/data gabriellegall/chess-com-bi-pg:latest