import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
import sys
import os
from unittest.mock import MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_processing import get_players_aggregates, get_player_metric_values, get_summary_kpis

def sample_data():
    """Fixture for creating a sample DataFrame for testing."""
    data = {
        'username': ['user1', 'user1', 'user1', 'user2', 'user2', 'user3', 'user1', 'user1'],
        'playing_as': ['White', 'Black', 'White', 'Black', 'White', 'White', 'Black', 'White'],
        'is_win': [1, 0, 1, 1, 0, 1, 1, 0],
        'elo': [1500, 1510, 1505, 1200, 1210, 1800, 1520, 1490],
        'end_time': pd.to_datetime([
            '2023-01-01 10:00', '2023-01-01 11:00', '2023-01-02 10:00', 
            '2023-01-03 12:00', '2023-01-03 13:00', '2023-01-04 14:00',
            '2023-01-05 15:00', '2023-01-06 16:00'
        ]),
    }
    return pd.DataFrame(data)

def test_get_players_aggregates():
    """Test get_players_aggregates function."""
    df = sample_data()
    agg_dict = {
        'is_win': {'agg': 'mean'},
        'elo': {'agg': 'max'}
    }
    
    # Test with min_games=3, user1 should be included, user2 and user3 should be excluded
    result = get_players_aggregates(df, agg_dict, min_games=3)
    expected = pd.DataFrame({
        'username': ['user1'],
        'is_win': [0.6], # 3 wins / 5 games
        'elo': [1520]
    })
    assert_frame_equal(result, expected)

    # Test with min_games=1, all users should be included
    result = get_players_aggregates(df, agg_dict, min_games=1)
    expected = pd.DataFrame({
        'username': ['user1', 'user2', 'user3'],
        'is_win': [0.6, 0.5, 1.0],
        'elo': [1520, 1210, 1800]
    }).sort_values('username').reset_index(drop=True)
    assert_frame_equal(result.sort_values('username').reset_index(drop=True), expected)

    # Test with no users meeting min_games
    result = get_players_aggregates(df, agg_dict, min_games=10)
    assert result.empty

    # Test with empty dataframe
    result = get_players_aggregates(pd.DataFrame(), agg_dict, min_games=1)
    assert result.empty

def test_get_player_metric_values():
    """Test get_player_metric_values function."""
    df = sample_data()

    # Test case 1: Scalar values (no aggregation_dimension)
    value_all, value_specific = get_player_metric_values(df, 'is_win', 'user1', 'mean', 2)
    assert value_all == 0.6
    assert value_specific == 0.5

    # Test case 2: Scalar values with different metric and aggregation
    value_all, value_specific = get_player_metric_values(df, 'elo', 'user1', 'max', 3)
    assert value_all == 1520
    assert value_specific == 1520

    # Test case 3: DataFrame values (with aggregation_dimension)
    df_all, df_specific = get_player_metric_values(df, 'is_win', 'user1', 'mean', 2, 'playing_as')
    
    expected_all = pd.DataFrame({
        'playing_as': ['Black', 'White'],
        'is_win': [0.5, 2/3]
    }).sort_values('playing_as').reset_index(drop=True)
    assert_frame_equal(df_all.sort_values('playing_as').reset_index(drop=True), expected_all)

    expected_specific = pd.DataFrame({
        'playing_as': ['Black', 'White'],
        'is_win': [1.0, 0.0]
    }).sort_values('playing_as').reset_index(drop=True)
    assert_frame_equal(df_specific.sort_values('playing_as').reset_index(drop=True), expected_specific)

    # Test case 4: Non-existent user
    value_all, value_specific = get_player_metric_values(df, 'is_win', 'nonexistent', 'mean', 5)
    assert value_all is None
    assert value_specific is None

    df_all, df_specific = get_player_metric_values(df, 'is_win', 'nonexistent', 'mean', 5, 'playing_as')
    assert df_all.empty
    assert df_specific.empty

    # Test case 5: Test with user2
    value_all, value_specific = get_player_metric_values(df, 'is_win', 'user2', 'mean', 1)
    assert value_all == 0.5
    assert value_specific == 0.0

    # Test case 6: Test with user2 and aggregation dimension
    df_all, df_specific = get_player_metric_values(df, 'is_win', 'user2', 'mean', 1, 'playing_as')
    expected_all = pd.DataFrame({
        'playing_as': ['Black', 'White'],
        'is_win': [1.0, 0.0]
    }).sort_values('playing_as').reset_index(drop=True)
    assert_frame_equal(df_all.sort_values('playing_as').reset_index(drop=True), expected_all)
    
    expected_specific = pd.DataFrame({
        'playing_as': ['White'],
        'is_win': [0.0]
    })
    assert_frame_equal(df_specific, expected_specific)

    # Test case 7: Test with user3 (only one game)
    value_all, value_specific = get_player_metric_values(df, 'elo', 'user3', 'max', 5)
    assert value_all == 1800
    assert value_specific == 1800

    # Test case 8: Test with user3 and aggregation dimension
    df_all, df_specific = get_player_metric_values(df, 'elo', 'user3', 'max', 5, 'playing_as')
    expected = pd.DataFrame({
        'playing_as': ['White'],
        'elo': [1800]
    })
    assert_frame_equal(df_all, expected)
    assert_frame_equal(df_specific, expected)

def test_get_summary_kpis():
    """Test get_summary_kpis function."""
    df = sample_data()

    # Scenario 1: Test with user1 and last_n_games=3
    kpis = get_summary_kpis(df[df['username'] == 'user1'], 'user1', 3)
    
    # White stats for user1
    assert kpis['White']['total_games'] == 3
    assert kpis['White']['win_rate_overall'] == pytest.approx((2/3) * 100)
    assert kpis['White']['total_recent_games'] == 2
    assert kpis['White']['win_rate_recent'] == pytest.approx(50.0)
    assert kpis['White']['delta_vs_overall'] == pytest.approx(50.0 - (2/3) * 100)

    # Black stats for user1
    assert kpis['Black']['total_games'] == 2
    assert kpis['Black']['win_rate_overall'] == pytest.approx(50.0)
    assert kpis['Black']['total_recent_games'] == 1
    assert kpis['Black']['win_rate_recent'] == pytest.approx(100.0)
    assert kpis['Black']['delta_vs_overall'] == pytest.approx(50.0)

    # Recent games df
    assert len(kpis['recent_games_df']) == 3
    expected_recent_usernames = ['user1', 'user1', 'user1']
    assert kpis['recent_games_df']['username'].tolist() == expected_recent_usernames

    # Scenario 2: Test with user2 (fewer games than last_n_games)
    kpis_user2 = get_summary_kpis(df[df['username'] == 'user2'], 'user2', 5)

    # White stats for user2
    assert kpis_user2['White']['total_games'] == 1
    assert kpis_user2['White']['win_rate_overall'] == 0.0
    assert kpis_user2['White']['total_recent_games'] == 1
    assert kpis_user2['White']['win_rate_recent'] == 0.0
    assert kpis_user2['White']['delta_vs_overall'] == 0.0

    # Black stats for user2
    assert kpis_user2['Black']['total_games'] == 1
    assert kpis_user2['Black']['win_rate_overall'] == 100.0
    assert kpis_user2['Black']['total_recent_games'] == 1
    assert kpis_user2['Black']['win_rate_recent'] == 100.0
    assert kpis_user2['Black']['delta_vs_overall'] == 0.0

    # Recent games df for user2
    assert len(kpis_user2['recent_games_df']) == 2

    # Scenario 3: Test with user3 (only played as White)
    kpis_user3 = get_summary_kpis(df[df['username'] == 'user3'], 'user3', 5)

    # White stats for user3
    assert kpis_user3['White']['total_games'] == 1
    assert kpis_user3['White']['win_rate_overall'] == 100.0
    assert kpis_user3['White']['total_recent_games'] == 1
    assert kpis_user3['White']['win_rate_recent'] == 100.0
    assert kpis_user3['White']['delta_vs_overall'] == 0.0

    # Black stats for user3 (should be None as user3 never played as Black)
    assert kpis_user3['Black'] is None
