def get_plot_config(game_phases_config: dict, score_thresholds_config: dict) -> dict:
    """
    Generates the plot configuration dictionary.
    This dictionary defines how each metric is aggregated, annotated, and displayed.
    """
    return {
        # Time Management Metrics
        'prct_time_remaining_early_playing': {
            'agg': 'median',
            'left_annotation': '⌛Slow',
            'right_annotation': '⚡Fast',
            'plot_title': f"Time remaining (Early - Turn {game_phases_config.get('early', {}).get('end_game_move')})"
        },
        'prct_time_remaining_mid_playing': {
            'agg': 'median',
            'left_annotation': '⌛Slow',
            'right_annotation': '⚡Fast',
            'plot_title': f"Time remaining (Mid - Turn {game_phases_config.get('mid', {}).get('end_game_move')})"
        },
        'prct_time_remaining_late_playing': {
            'agg': 'median',
            'left_annotation': '⌛Slow',
            'right_annotation': '⚡Fast',
            'plot_title': f"Time remaining (Late - Turn {game_phases_config.get('late', {}).get('end_game_move')})"
        },

        # Throws Metrics
        'nb_throw_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🎯Accurate',
            'right_annotation': '💥Confused',
            'plot_title': '🟠 Small Throws',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small throw (massive throws are not counted). A small throw is a throw with a decrease in centipawn advantage between {score_thresholds_config.get('variance_score_blunder')} and {score_thresholds_config.get('variance_score_massive_blunder')}."
        },
        'nb_throw_massive_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🎯Accurate',
            'right_annotation': '💥Confused',
            'plot_title': '🔴 Massive Throws',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive throw. A massive throw is a throw with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_massive_blunder')}."
        },

        # Missed Opportunities Metrics
        'nb_missed_opportunity_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🔍Attentive',
            'right_annotation': '👀Blind',
            'plot_title': '🟠 Small Missed Opportunities',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity (massive missed opportunities are not counted). A small missed opportunity is a missed opportunity with a decrease in centipawn advantage between {score_thresholds_config.get('variance_score_blunder')} and {score_thresholds_config.get('variance_score_massive_blunder')}."
        },
        'nb_missed_opportunity_massive_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🔍Attentive',
            'right_annotation': '👀Blind',
            'plot_title': '🔴 Massive Missed Opportunities',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive missed opportunity. A massive missed opportunity is a missed opportunity with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_massive_blunder')}."
        },

        # Phase-Specific Metrics - Missed Opportunities
        'nb_missed_opportunity_massive_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Missed Opportunities - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive missed opportunity during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'nb_missed_opportunity_massive_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Missed Opportunities - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive missed opportunity during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'nb_missed_opportunity_massive_blunder_playing_late': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Missed Opportunities - Late',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive missed opportunity during the late game phase (moves {game_phases_config.get('mid', {}).get('end_game_move') + 1} to {game_phases_config.get('late', {}).get('end_game_move')})."
        },

        # Phase-Specific Metrics - Throws
        'nb_throw_massive_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Throws - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive throw during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'nb_throw_massive_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Throws - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive throw during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'nb_throw_massive_blunder_playing_late': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Throws - Late',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive throw during the late game phase (moves {game_phases_config.get('mid', {}).get('end_game_move') + 1} to {game_phases_config.get('late', {}).get('end_game_move')})."
        },

        # Phase-Specific Metrics - Small Missed Opportunities
        'nb_missed_opportunity_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Missed Opportunities - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'nb_missed_opportunity_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Missed Opportunities - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'nb_missed_opportunity_blunder_playing_late': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Missed Opportunities - Late',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity during the late game phase (moves {game_phases_config.get('mid', {}).get('end_game_move') + 1} to {game_phases_config.get('late', {}).get('end_game_move')})."
        },

        # Phase-Specific Metrics - Small Throws
        'nb_throw_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Throws - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small throw during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'nb_throw_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Throws - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small throw during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'nb_throw_blunder_playing_late': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Throws - Late',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small throw during the late game phase (moves {game_phases_config.get('mid', {}).get('end_game_move') + 1} to {game_phases_config.get('late', {}).get('end_game_move')})."
        },
    }

def get_section_config(game_phases_config: dict, score_thresholds_config: dict) -> list:
    """
    Generates the configuration for each section of plots.
    Each section is composed of several main plots and optional breakdown subplots.
    """
    return [
        {
            "title": "⏳ Time Management (early vs. mid vs. late-game)",
            "metrics": ("prct_time_remaining_early_playing", "prct_time_remaining_mid_playing", "prct_time_remaining_late_playing"),
            "help_text": f"Time management is estimated looking at the percentage of time remaining on the clock at specific turns. For the early-game: turn {game_phases_config.get('early', {}).get('end_game_move')}, for the mid-game: turn {game_phases_config.get('mid', {}).get('end_game_move')}, and for the late-game: turn {game_phases_config.get('late', {}).get('end_game_move')}.",
            "has_breakdown": False
        },
        {
            "title": "💥 Throws (small vs. massive)", 
            "metrics": ("nb_throw_blunder_playing", "nb_throw_massive_blunder_playing"),
            "help_text": f"A throw is defined as a move which significantly worsens the player's position, **starting from a relatively even or disadvantageous position.** This means the engine evaluation advantage for the selected player was at most {score_thresholds_config.get('even_score_limit')} centipawns before the move.",
            "has_breakdown": True,
            "breakdown_groups": {
                "nb_throw_blunder_playing": ["nb_throw_blunder_playing_early", "nb_throw_blunder_playing_mid", "nb_throw_blunder_playing_late"],
                "nb_throw_massive_blunder_playing": ["nb_throw_massive_blunder_playing_early", "nb_throw_massive_blunder_playing_mid", "nb_throw_massive_blunder_playing_late"]
            }
        },
        {
            "title": "👀 Missed Opportunities (small vs. massive)", 
            "metrics": ("nb_missed_opportunity_blunder_playing", "nb_missed_opportunity_massive_blunder_playing"),
            "help_text": f"A missed opportunity is defined as a move which significantly worsens the player's position, **starting from an advantageous position.** This means the engine evaluation advantage for the selected player was at least {score_thresholds_config.get('even_score_limit')} centipawns before the move.",
            "has_breakdown": True,
            "breakdown_groups": {
                "nb_missed_opportunity_blunder_playing": ["nb_missed_opportunity_blunder_playing_early", "nb_missed_opportunity_blunder_playing_mid", "nb_missed_opportunity_blunder_playing_late"],
                "nb_missed_opportunity_massive_blunder_playing": ["nb_missed_opportunity_massive_blunder_playing_early", "nb_missed_opportunity_massive_blunder_playing_mid", "nb_missed_opportunity_massive_blunder_playing_late"]
            }
        },
    ]
