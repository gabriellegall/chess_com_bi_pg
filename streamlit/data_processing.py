import pandas as pd
from data.loader import load_query
import streamlit as st

@st.cache_data
def get_raw_data() -> pd.DataFrame:
    """Loads the raw game data from the specified SQL query."""
    return load_query("data/agg_games_with_moves__games.sql")

@st.cache_data
def get_players_aggregates(data: pd.DataFrame, agg_dict: dict, min_games: int = 15, group_by_col: str = 'username') -> pd.DataFrame:
    """
    This function aggregates the data for each player based on the provided aggregation dictionary.
    The dictionary should contain the metric names as keys and a the 'agg' key with the aggregation function (e.g., 'mean', 'median').
    Only groups with at least `min_games` will be returned.
    """
    # First, find which groups meet the minimum games threshold
    group_counts = data[group_by_col].value_counts()
    valid_groups = group_counts[group_counts >= min_games].index

    if valid_groups.empty:
        return pd.DataFrame()

    # Filter the original dataframe to only include valid groups
    filtered_data = data[data[group_by_col].isin(valid_groups)]

    agg_funcs = {k: v["agg"] for k, v in agg_dict.items()}
    
    # Perform a single aggregation on the filtered data
    return filtered_data.groupby(group_by_col).agg(agg_funcs).reset_index()

def get_summary_kpis(df: pd.DataFrame, username: str, last_n: int) -> dict:
    """
    Calculates all KPIs for the summary header.
    Returns a dictionary with stats for White and Black pieces, both overall and recent.
    """
    kpis = {'White': {}, 'Black': {}}

    # Calculate win rates for all games and recent games, broken down by color
    win_rate_data, win_rate_data_recent = get_player_metric_values(
        df, 'is_win', username, 'mean', last_n=last_n, aggregation_dimension='playing_as'
    )

    # Identify the last N games overall for the user with current filters
    recent_games_overall = df.sort_values('end_time', ascending=False).head(last_n)
    kpis['recent_games_df'] = recent_games_overall

    for color in ['White', 'Black']:
        df_color = df[df['playing_as'] == color]
        
        if df_color.empty:
            kpis[color] = None # No data for this color
            continue

        # Overall stats
        total_games = len(df_color)
        wr_overall_series = win_rate_data[win_rate_data['playing_as'] == color]['is_win']
        win_rate_overall = wr_overall_series.iloc[0] * 100 if not wr_overall_series.empty else 0

        # Recent stats
        total_recent_games = len(recent_games_overall[recent_games_overall['playing_as'] == color])
        wr_recent_series = win_rate_data_recent[win_rate_data_recent['playing_as'] == color]['is_win']
        win_rate_recent = wr_recent_series.iloc[0] * 100 if not wr_recent_series.empty else 0
        
        delta_vs_overall = win_rate_recent - win_rate_overall

        kpis[color] = {
            'total_games': total_games,
            'win_rate_overall': win_rate_overall,
            'total_recent_games': total_recent_games,
            'win_rate_recent': win_rate_recent,
            'delta_vs_overall': delta_vs_overall
        }
        
    return kpis

def get_player_metric_values(data: pd.DataFrame, metric: str, username: str, agg_type: str, last_n: int, aggregation_dimension: str = None) -> tuple | pd.DataFrame:
    """
    This function aggregates the metric for a specific user.
    If `aggregation_dimension` is None, it returns two scalar values as a tuple:
    - value_all: The aggregated value for the entire dataset for that user.
    - value_specific: The aggregated value for the last `last_n` games for that user.
    If `aggregation_dimension` is provided, it returns two DataFrames, one for all games and one for recent games,
    with the metric aggregated by the specified dimension.
    """
    user_data = data[data['username'] == username]
    if user_data.empty:
        return (None, None) if not aggregation_dimension else (pd.DataFrame(), pd.DataFrame())

    # Aggregation for all data
    if aggregation_dimension:
        value_all = user_data.groupby(aggregation_dimension).agg({metric: agg_type}).reset_index()
    else:
        if hasattr(user_data[metric], agg_type):
            value_all = getattr(user_data[metric], agg_type)()
        else:
            raise ValueError(f"Unsupported aggregation type: {agg_type}")

    # Aggregation for recent data
    user_data_sorted = user_data.sort_values('end_time', ascending=False)
    recent_data = user_data_sorted.head(last_n)
    
    if recent_data.empty:
        value_specific = None if not aggregation_dimension else pd.DataFrame()
    else:
        if aggregation_dimension:
            value_specific = recent_data.groupby(aggregation_dimension).agg({metric: agg_type}).reset_index()
        else:
            if hasattr(recent_data[metric], agg_type):
                value_specific = getattr(recent_data[metric], agg_type)()
            else:
                raise ValueError(f"Unsupported aggregation type: {agg_type}")

    return value_all, value_specific
