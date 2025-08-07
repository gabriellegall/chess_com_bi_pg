import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
import sys
import os
from unittest.mock import MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_processing import get_players_aggregates

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
