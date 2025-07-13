# Local execution (forward slash for Linux)
stg_games:
	@cd scripts/chess_com_api && python chess_games_pipeline.py

stg_games_times:
	@cd scripts/games_times && python chess_games_times_pipeline.py

stg_games_moves:
	@cd scripts/stockfish && python chess_games_moves_pipeline.py

# Docker Hub
docker_build_project:
	dbt clean
	docker build -t chess-com-bi-pg .

docker_hub_push: docker_build_project
	docker tag chess-com-bi-pg gabriellegall/chess-com-bi-pg:latest
	docker push gabriellegall/chess-com-bi-pg:latest

# Local postgres for debugging (if needed)
docker_postgres:
	docker run --name chess_local_postgres_container \
	-e POSTGRES_PASSWORD=AsidDe5845edDikkDee \
	-e POSTGRES_USER=glegall \
	-e POSTGRES_DB=chess \
	-p 5432:5432 \
	-d postgres