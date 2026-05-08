{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    post_hook = [
        "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_run_timestamp ON {{ this }} (run_timestamp)"
    ]
) }}

SELECT
    {{ dbt_utils.generate_surrogate_key(['gm.username']) }} AS players_sk,
    {{ dbt_utils.generate_surrogate_key(['gm.uuid', 'gm.username']) }} AS games_sk,
    gm.uuid,
    gm.username,
    gm.playing_as,
    gm.move_number,
    gm.move,
    gm.time_remaining_seconds,
    gm.prct_time_remaining,
    gm.game_phase,
    gm.player_color_turn,
    gm.is_playing_turn,
    gm.playing_turn_name,
    gm.score_playing,
    gm.run_timestamp,
    gm.prev_score_playing,
    gm.variance_score_playing,
    gm.miss_category_playing,
    gm.miss_move_number_playing,
    gm.massive_blunder_move_number_playing,
    gm.miss_category_opponent,
    gm.miss_move_number_opponent,
    gm.position_status_playing,
    gm.position_status_opponent,
    gm.prev_position_status_playing,
    gm.prev_position_status_opponent,
    gm.miss_context_playing,
    gm.miss_context_opponent
FROM {{ ref('int_game_moves_enriched') }} gm
{% if is_incremental() %}
    WHERE gm.run_timestamp > (
        SELECT MAX(i.run_timestamp)
        FROM {{ this }} i
    )
{% endif %}