{{ config(materialized = 'view') }}

select
	pgm.*,
	case when mod(move_number, 2) = 1 then 'White' else 'Black' end as player_color_turn,
	-score_white as score_black,
	1.0 / (1 + exp(-0.004 * score_white)) as win_probability_white,
	1.0 - 1.0 / (1 + exp(-0.004 * score_white)) as win_probability_black
from {{ source('stockfish', 'players_games_moves') }} pgm