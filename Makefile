stg_games:
	@cd scripts\chess_com_api && python chess_games_pipeline.py

stg_games_times:
	@cd scripts\games_times && python chess_games_times_pipeline.py

stg_games_moves:
	@cd scripts\stockfish && python chess_games_moves_pipeline.py

stg_all: stg_games stg_games_times stg_games_moves