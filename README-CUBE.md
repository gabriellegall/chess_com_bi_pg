# Tested limits

## KPI: window-function on the last X
Cube does support window calculation on the last X days:

```
      - name: nb_losses_last_30_days
        type: count
        filters:
          - sql: "{CUBE}.playing_result = 'Lose'"
        rolling_window:
          trailing: 30 day
```
### Problem 1:
Cubes does NOT support the winrate on the last X games that user ABC played.
The only solution is to pre-calculate it, but it loses all filtering dynamism.

### Problem 2:
This query does not work on the last 30D:
```
SELECT
    username_global,
    MEASURE(v_games.win_rate) AS win_rate,
    MEASURE(v_games.win_rate_last_30_days) AS win_rate_last_30_days
FROM public.v_games
GROUP BY
    username_global
```

We have to use a time dimension:
```
SELECT
    username_global,
    DATE_TRUNC('day', end_time) AS game_day,
    MEASURE(v_games.win_rate) AS win_rate,
    MEASURE(v_games.win_rate_last_30_days) AS win_rate_last_30_days
FROM public.v_games
GROUP BY
    username_global,
    DATE_TRUNC('day', end_time)
ORDER BY
    game_day;
```

or use a WHERE clause with win_rate:
```
SELECT
    username_global,
    MEASURE(v_games.win_rate) AS win_rate_last_30_days
FROM public.v_games
WHERE end_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
    username_global;
```