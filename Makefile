# Local execution : stg
stg_games:
	@cd dbt/scripts/chess_com_api && python chess_games_pipeline.py

stg_games_times:
	@cd dbt/scripts/games_times && python chess_games_times_pipeline.py

stg_games_moves:
	@cd dbt/scripts/stockfish && python chess_games_moves_pipeline.py

# Local execution : dbt
run_dbt_full_refresh:
	@cd dbt && python run_dbt_full_refresh.py

run_all_with_reset:
	@cd dbt && python run_all_with_reset.py

run_all.py:
	@cd dbt && python run_all.py

# Local execution : streamlit
streamlit_run:
	@cd streamlit && streamlit run app.py

# Docker Hub - DBT
docker_build_project_dbt:
	docker build -f Dockerfile.dbt -t chess-com-bi-pg-dbt .

docker_hub_push_dbt: docker_build_project_dbt
	docker tag chess-com-bi-pg-dbt gabriellegall/chess-com-bi-pg-dbt:latest
	docker push gabriellegall/chess-com-bi-pg-dbt:latest

# Docker Hub - Streamlit
docker_build_project_streamlit:
	docker build -f Dockerfile.streamlit -t chess-com-bi-pg-streamlit .

docker_hub_push_streamlit: docker_build_project_streamlit
	docker tag chess-com-bi-pg-streamlit gabriellegall/chess-com-bi-pg-streamlit:latest
	docker push gabriellegall/chess-com-bi-pg-streamlit:latest

# Local postgres for debugging (if needed)
docker_postgres:
	docker run --name chess_local_postgres_container \
	-e POSTGRES_USER=admin \
	-e POSTGRES_PASSWORD=local \
	-e POSTGRES_DB=chess \
	-p 5432:5432 \
	-d postgres