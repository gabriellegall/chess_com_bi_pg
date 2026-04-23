{{ config(materialized = 'view') }}

with source_data as (
	select *
	from {{ source('chess_com', 'players_games') }}
),

filter_table as (
	select *
	from source_data
	where true
		and rules = 'chess'
		and (
			length(initial_setup) = 0
			or initial_setup = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
		)
		and length(pgn) > 0
		and pgn ~ E'\\d+\\. '
),

cast_types as (
	select
		*,
		end_time::date as end_time_date,
		to_char(end_time, 'YYYY-MM') as end_time_month
	from filter_table
),

define_playing as (
	select
		*,
		case
			when lower(username) = lower(white__username) then 'White'
			when lower(username) = lower(black__username) then 'Black'
			else null
		end as playing_as
	from cast_types
),

define_result as (
	select
		*,
		case
			when playing_as = 'White' then white__result
			when playing_as = 'Black' then black__result
			else null
		end as playing_result_detailed,
		case
			when playing_as = 'White' then white__rating
			when playing_as = 'Black' then black__rating
			else null
		end as playing_rating,
		case
			when playing_as = 'White' then black__rating
			when playing_as = 'Black' then white__rating
			else null
		end as opponent_rating
	from define_playing
)

select *
from define_result