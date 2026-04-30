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
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small throw (massive throws are not counted). A small throw is a throw with a decrease in centipawn advantage between {score_thresholds_config.get('variance_score_blunder')} and {score_thresholds_config.get('variance_score_massive_blunder')}."
        },
        'has_throw_massive_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🎯Accurate',
            'right_annotation': '💥Confused',
            'plot_title': '🔴 Massive Throws',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive throw. A massive throw is a throw with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_massive_blunder')}."
        },

        # Missed Opportunities Metrics
        'has_missed_opportunity_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🔍Attentive',
            'right_annotation': '👀Blind',
            'plot_title': '🟠 Small Missed Opportunities',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity (massive missed opportunities are not counted). A small missed opportunity is a missed opportunity with a decrease in centipawn advantage between {score_thresholds_config.get('variance_score_blunder')} and {score_thresholds_config.get('variance_score_massive_blunder')}."
        },
        'has_missed_opportunity_massive_blunder_playing': {
            'agg': 'mean',
            'left_annotation': '🔍Attentive',
            'right_annotation': '👀Blind',
            'plot_title': '🔴 Massive Missed Opportunities',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive missed opportunity. A massive missed opportunity is a missed opportunity with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_massive_blunder')}."
        },

        # Phase-Specific Metrics - Missed Opportunities
        'has_missed_opportunity_massive_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Missed Opportunities - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive missed opportunity during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'has_missed_opportunity_massive_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Missed Opportunities - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive missed opportunity during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'has_missed_opportunity_massive_blunder_playing_late': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Missed Opportunities - Late',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive missed opportunity during the late game phase (moves {game_phases_config.get('mid', {}).get('end_game_move') + 1} to {game_phases_config.get('late', {}).get('end_game_move')})."
        },

        # Phase-Specific Metrics - Throws
        'has_throw_massive_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Throws - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive throw during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'has_throw_massive_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Throws - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive throw during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'has_throw_massive_blunder_playing_late': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🔴 Massive Throws - Late',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 massive throw during the late game phase (moves {game_phases_config.get('mid', {}).get('end_game_move') + 1} to {game_phases_config.get('late', {}).get('end_game_move')})."
        },

        # Phase-Specific Metrics - Small Missed Opportunities
        'has_missed_opportunity_blunder_playing_early': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Missed Opportunities - Early',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity during the early game phase (moves 1 to {game_phases_config.get('early', {}).get('end_game_move')})."
        },
        'has_missed_opportunity_blunder_playing_mid': {
            'agg': 'mean',
            'left_annotation': 'Short Games',
            'right_annotation': 'Long Games',
            'plot_title': '🟠 Small Missed Opportunities - Mid',
            'help': f"This boxplot represents, for each player, the percentage of games with at least 1 small missed opportunity during the mid game phase (moves {game_phases_config.get('early', {}).get('end_game_move') + 1} to {game_phases_config.get('mid', {}).get('end_game_move')})."
        },
        'has_missed_opportunity_blunder_playing_late': {
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

        # Percentage of Time remaining at 1st Massive Blunder
        'first_massive_blunder_playing_prct_time_remaining': {
            'agg': 'median',
            'left_annotation': '⏳ You had no time',
            'right_annotation': '🚨 You had time',
            'plot_title': '⌛🔴 Time remaining on the 1st Massive Blunder',
            'help': f"This boxplot represents, for each player, the percentage of time remaining on the clock when the 1st massive blunder occurs. A massive blunder is a blunder with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_massive_blunder')}."
        },
        'first_throw_massive_blunder_playing_prct_time_remaining': {
            'agg': 'median',
            'left_annotation': '⏳ You had no time',
            'right_annotation': '🚨 You had time',
            'plot_title': '⌛🔴💥 Time remaining on the 1st Massive Throw',
            'help': f"This boxplot represents, for each player, the percentage of time remaining on the clock when the 1st massive throw occurs. A massive throw is a throw with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_massive_blunder')}."
        },
        'first_missed_opp_massive_blunder_playing_prct_time_remaining': {
            'agg': 'median',
            'left_annotation': '⏳ You had no time',
            'right_annotation': '🚨 You had time',
            'plot_title': '⌛🔴👀 Time remaining on the 1st Massive Missed Opportunity',
            'help': f"This boxplot represents, for each player, the percentage of time remaining on the clock when the 1st massive missed opportunity occurs. A massive missed opportunity is a missed opportunity with a decrease in centipawn advantage beyond {score_thresholds_config.get('variance_score_massive_blunder')}."
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
            "title": "💥 Throws (small vs. massive)", 
            "metrics": ("has_throw_blunder_playing", "has_throw_massive_blunder_playing"),
            "help_text": f"A throw is defined as a move which significantly worsens the player's position, **starting from a relatively even or disadvantageous position.** This means the engine evaluation advantage for the selected player was at most {score_thresholds_config.get('even_score_limit')} centipawns before the move.",
            "has_breakdown": True,
            "breakdown_groups": {
                "has_throw_blunder_playing": ["has_throw_blunder_playing_early", "has_throw_blunder_playing_mid", "has_throw_blunder_playing_late"],
                "has_throw_massive_blunder_playing": ["has_throw_massive_blunder_playing_early", "has_throw_massive_blunder_playing_mid", "has_throw_massive_blunder_playing_late"]
            }
        },
        {
            "title": "👀 Missed Opportunities (small vs. massive)", 
            "metrics": ("has_missed_opportunity_blunder_playing", "has_missed_opportunity_massive_blunder_playing"),
            "help_text": f"A missed opportunity is defined as a move which significantly worsens the player's position, **starting from an advantageous position.** This means the engine evaluation advantage for the selected player was at least {score_thresholds_config.get('even_score_limit')} centipawns before the move.",
            "has_breakdown": True,
            "breakdown_groups": {
                "has_missed_opportunity_blunder_playing": ["has_missed_opportunity_blunder_playing_early", "has_missed_opportunity_blunder_playing_mid", "has_missed_opportunity_blunder_playing_late"],
                "has_missed_opportunity_massive_blunder_playing": ["has_missed_opportunity_massive_blunder_playing_early", "has_missed_opportunity_massive_blunder_playing_mid", "has_missed_opportunity_massive_blunder_playing_late"]
            }
        },
        {
            "title": "⏳🔴 Time Remaining on the 1st Massive Blunder",
            "metrics": (
                "first_massive_blunder_playing_prct_time_remaining",
                "first_throw_massive_blunder_playing_prct_time_remaining",
                "first_missed_opp_massive_blunder_playing_prct_time_remaining",
            ),
            "help_text": "These plots show, for each player, the percentage of time remaining on the clock when the 1st massive mistake (throw or missed opportunity) occurs in a game.",
            "has_breakdown": False
        },
    ]
