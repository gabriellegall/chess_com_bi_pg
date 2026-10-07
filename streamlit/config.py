def get_plot_config(game_phases_config: dict, score_thresholds_config: dict) -> dict:
    """
    Generates the plot configuration dictionary.
    This dictionary defines how each metric is aggregated, annotated, and displayed.
    """
    return {
        # Time Management Metrics
        'prct_time_remaining_playing_early': {
            'agg': 'median',
            'left_annotation': '⌛Slow',
            'right_annotation': '⚡Fast',
            'plot_title': f"Time remaining (Early - Turn {game_phases_config.get('early', {}).get('end_game_move')})"
        },
        'prct_time_remaining_playing_mid': {
            'agg': 'median',
            'left_annotation': '⌛Slow',
            'right_annotation': '⚡Fast',
            'plot_title': f"Time remaining (Mid - Turn {game_phases_config.get('mid', {}).get('end_game_move')})"
        },
        'prct_time_remaining_playing_late': {
            'agg': 'median',
            'left_annotation': '⌛Slow',
            'right_annotation': '⚡Fast',
            'plot_title': f"Time remaining (Late - Turn {game_phases_config.get('late', {}).get('end_game_move')})"
        },

        # Throws Metrics
        'has_throw_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🎯Accurate',
            'right_annotation': '💥Confused',
            'plot_title': '🟠 Small Throws',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small throw (big throws are not counted). A small throw is a throw with a decrease in centipawn advantage between {score_thresholds_config.get('variance_score_blunder')} and {score_thresholds_config.get('variance_score_big_blunder')}."
        },
        'has_throw_big_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🎯Accurate',
            'right_annotation': '💥Confused',
            'plot_title': '🔴 Big Throws',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 big throw. A big throw is a throw with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_big_blunder')}."
        },

        # Missed Opportunities Metrics
        'has_miss_opp_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🔍Attentive',
            'right_annotation': '👀Blind',
            'plot_title': '🟠 Small Missed Opportunities',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity (big missed opportunities are not counted). A small missed opportunity is a missed opportunity with a decrease in centipawn advantage between {score_thresholds_config.get('variance_score_blunder')} and {score_thresholds_config.get('variance_score_big_blunder')}."
        },
        'has_miss_opp_big_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🔍Attentive',
            'right_annotation': '👀Blind',
            'plot_title': '🔴 Big Missed Opportunities',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 big missed opportunity. A big missed opportunity is a missed opportunity with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_big_blunder')}."
        },

        # Phase-Specific Metrics - Missed Opportunities
        'has_miss_opp_big_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Big Missed Opportunities - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 big missed opportunity during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'has_miss_opp_big_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Big Missed Opportunities - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 big missed opportunity during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'has_miss_opp_big_blunder_playing_late': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Big Missed Opportunities - Late',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 big missed opportunity during the late game phase (moves {game_phases_config.get('mid', {}).get('end_game_move') + 1} to {game_phases_config.get('late', {}).get('end_game_move')})."
        },

        # Phase-Specific Metrics - Throws
        'has_throw_big_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Big Throws - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 big throw during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'has_throw_big_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Big Throws - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 big throw during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'has_throw_big_blunder_playing_late': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Big Throws - Late',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 big throw during the late game phase (moves {game_phases_config.get('mid', {}).get('end_game_move') + 1} to {game_phases_config.get('late', {}).get('end_game_move')})."
        },

        # Phase-Specific Metrics - Small Missed Opportunities
        'has_miss_opp_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Missed Opportunities - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'has_miss_opp_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Missed Opportunities - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'has_miss_opp_blunder_playing_late': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Missed Opportunities - Late',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity during the late game phase (moves {game_phases_config.get('mid', {}).get('end_game_move') + 1} to {game_phases_config.get('late', {}).get('end_game_move')})."
        },

        # Phase-Specific Metrics - Small Throws
        'has_throw_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Throws - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small throw during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'has_throw_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Throws - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small throw during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'has_throw_blunder_playing_late': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Throws - Late',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small throw during the late game phase (moves {game_phases_config.get('mid', {}).get('end_game_move') + 1} to {game_phases_config.get('late', {}).get('end_game_move')})."
        },

        # Percentage of Time remaining at 1st Big Blunder
        'first_big_blunder_playing_prct_time_remaining': {
            'agg': 'median',
            'left_annotation': '⏳ You had no time',
            'right_annotation': '🚨 You had time',
            'plot_title': '⌛🔴 Time remaining on the 1st Big Blunder',
            'help': f"This boxplot represents, for each player, the percentage of time remaining on the clock when the 1st big blunder occurs. A big blunder is a blunder with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_big_blunder')}."
        },
        'first_throw_big_blunder_playing_prct_time_remaining': {
            'agg': 'median',
            'left_annotation': '⏳ You had no time',
            'right_annotation': '🚨 You had time',
            'plot_title': '⌛🔴💥 Time remaining on the 1st Big Throw',
            'help': f"This boxplot represents, for each player, the percentage of time remaining on the clock when the 1st big throw occurs. A big throw is a throw with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_big_blunder')}."
        },
        'first_miss_opp_big_blunder_playing_prct_time_remaining': {
            'agg': 'median',
            'left_annotation': '⏳ You had no time',
            'right_annotation': '🚨 You had time',
            'plot_title': '⌛🔴👀 Time remaining on the 1st Big Missed Opportunity',
            'help': f"This boxplot represents, for each player, the percentage of time remaining on the clock when the 1st big missed opportunity occurs. A big missed opportunity is a missed opportunity with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_big_blunder')}."
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
            "metrics": ("prct_time_remaining_playing_early", "prct_time_remaining_playing_mid", "prct_time_remaining_playing_late"),
            "help_text": f"Time management is estimated looking at the percentage of time remaining on the clock at specific turns. For the early-game: turn {game_phases_config.get('early', {}).get('end_game_move')}, for the mid-game: turn {game_phases_config.get('mid', {}).get('end_game_move')}, and for the late-game: turn {game_phases_config.get('late', {}).get('end_game_move')}.",
            "has_breakdown": False
        },
        {
            "title": "💥 Throws (small vs. big)",
            "metrics": ("has_throw_blunder_playing", "has_throw_big_blunder_playing"),
            "help_text": f"A throw is defined as a move which significantly worsens the player's position, **starting from a relatively even or disadvantageous position.** This means the engine evaluation advantage for the selected player was at most {score_thresholds_config.get('even_score_limit')} centipawns before the move.",
            "has_breakdown": True,
            "breakdown_groups": {
                "has_throw_blunder_playing": ["has_throw_blunder_playing_early", "has_throw_blunder_playing_mid", "has_throw_blunder_playing_late"],
                "has_throw_big_blunder_playing": ["has_throw_big_blunder_playing_early", "has_throw_big_blunder_playing_mid", "has_throw_big_blunder_playing_late"]
            }
        },
        {
            "title": "👀 Missed Opportunities (small vs. big)",
            "metrics": ("has_miss_opp_blunder_playing", "has_miss_opp_big_blunder_playing"),
            "help_text": f"A missed opportunity is defined as a move which significantly worsens the player's position, **starting from an advantageous position.** This means the engine evaluation advantage for the selected player was at least {score_thresholds_config.get('even_score_limit')} centipawns before the move.",
            "has_breakdown": True,
            "breakdown_groups": {
                "has_miss_opp_blunder_playing": ["has_miss_opp_blunder_playing_early", "has_miss_opp_blunder_playing_mid", "has_miss_opp_blunder_playing_late"],
                "has_miss_opp_big_blunder_playing": ["has_miss_opp_big_blunder_playing_early", "has_miss_opp_big_blunder_playing_mid", "has_miss_opp_big_blunder_playing_late"]
            }
        },
        {
            "title": "⏳🔴 Time Remaining on the 1st Big Blunder",
            "metrics": (
                "first_big_blunder_playing_prct_time_remaining",
                "first_throw_big_blunder_playing_prct_time_remaining",
                "first_miss_opp_big_blunder_playing_prct_time_remaining",
            ),
            "help_text": "These plots show, for each player, the percentage of time remaining on the clock when the 1st big mistake (throw or missed opportunity) occurs in a game.",
            "has_breakdown": False
        },
    ]
