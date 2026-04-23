# Best Practices Applied

This document summarizes the dbt best practices that were applied in this refactor and where they were implemented.

## 1. Staging organized by source system

Applied:
- Split staging into source-based subdirectories.
- Kept `stg_[source]__[entity]` naming.

Implemented in:
- `models/staging/chess_com/`
- `models/staging/openings/`
- `models/staging/stockfish/`
- `models/staging/times/`

Key files:
- `models/staging/chess_com/stg_chess_com__players_games.sql`
- `models/staging/openings/stg_openings__chess_openings.sql`
- `models/staging/stockfish/stg_stockfish__players_games_moves.sql`
- `models/staging/times/stg_times__players_games_times.sql`

## 2. Staging models remain 1:1 to sources

Applied:
- Preserved one staging model per source table.
- Staging models continue to be direct entry points from `source()`.

Implemented in:
- `models/staging/chess_com/stg_chess_com__players_games.sql`
- `models/staging/openings/stg_openings__chess_openings.sql`
- `models/staging/stockfish/stg_stockfish__players_games_moves.sql`
- `models/staging/times/stg_times__players_games_times.sql`

## 3. Staging materialized as views

Applied:
- Kept staging models materialized as views (aligned with project-level and model-level behavior).

Implemented in:
- `dbt_project.yml` (staging default)
- Staging model SQL files under `models/staging/*`

## 4. Folder-scoped YAML (instead of monolithic YAML)

Applied:
- Replaced broad flat YAML layout with per-folder YAML files.
- Added leading-underscore YAML naming convention per folder.

Implemented in:
- `models/staging/chess_com/_chess_com__models.yml`
- `models/staging/chess_com/_chess_com__sources.yml`
- `models/staging/openings/_openings__models.yml`
- `models/staging/openings/_openings__sources.yml`
- `models/staging/stockfish/_stockfish__models.yml`
- `models/staging/stockfish/_stockfish__sources.yml`
- `models/staging/times/_times__models.yml`
- `models/staging/times/_times__sources.yml`
- `models/intermediate/games/_games__models.yml`
- `models/intermediate/openings/_openings__models.yml`
- `models/marts/core/_core__models.yml`
- `models/marts/analytics/_analytics__models.yml`

## 5. Intermediate organized by business concern

Applied:
- Reorganized flat intermediate layer into business-aligned folders.
- Grouped game-related transformations together.

Implemented in:
- `models/intermediate/games/`
- `models/intermediate/openings/`

Key files:
- `models/intermediate/games/int_games.sql`
- `models/intermediate/games/int_games_scoped.sql`
- `models/intermediate/games/int_games_moves.sql`
- `models/intermediate/games/int_games_times.sql`
- `models/intermediate/games/int_games_with_moves_enriched.sql`
- `models/intermediate/games/int_games_openings.sql`
- `models/intermediate/games/int_games_stats.sql`
- `models/intermediate/openings/int_openings.sql`

## 6. Mart YAML consolidated by folder

Applied:
- Consolidated per-model mart YAML into folder-level YAML for core and analytics marts.

Implemented in:
- `models/marts/core/_core__models.yml`
- `models/marts/analytics/_analytics__models.yml`

## 7. SQL style enforcement tooling added

Applied:
- Added SQLFluff config to enforce consistent SQL style.
- Added SQLFluff ignore file to avoid linting generated and package directories.

Implemented in:
- `.sqlfluff`
- `.sqlfluffignore`

## 8. Validation after refactor

Applied:
- Verified compilation with `dbt parse`.
- Verified runtime model build with full `dbt run`.

Validation result:
- `dbt parse`: success
- `dbt run`: success (`PASS=61`, `WARN=0`, `ERROR=0`)

## Notes on scope

Not changed in this pass:
- Existing model business logic was not broadly rewritten.
- Existing incremental strategy choices were preserved.
- Existing marts under `models/marts/to_delete/` were not removed.
