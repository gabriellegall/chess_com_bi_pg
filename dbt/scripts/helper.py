from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
import os
from dotenv import load_dotenv
import yaml
import hashlib
import re

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def get_engine() -> Engine:

    load_dotenv()

    db_name     = os.getenv("DB_NAME")
    db_user     = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host     = os.getenv("DB_HOST")
    db_port     = os.getenv("DB_PORT")

    return create_engine(f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_dbt_project() -> dict:
    project_path = os.path.join(os.path.dirname(__file__), '..', 'dbt_project.yml')
    with open(project_path, "r") as f:
        return yaml.safe_load(f)


def get_processable_games_condition() -> str:
    condition = load_dbt_project().get("vars", {}).get("processable_games_condition")
    if not condition:
        raise ValueError("Missing vars.processable_games_condition in dbt_project.yml")
    return condition.strip()


def get_table_settings(config: dict, source_key: str) -> tuple[str, str | None]:
    table_config = config["postgres"]["tables"][source_key]

    if not isinstance(table_config, dict):
        raise ValueError(
            f"Invalid postgres.tables.{source_key} config: expected mapping with 'name' and optional 'index_field'"
        )

    table_name = table_config.get("name")
    index_field = table_config.get("index_field")

    # DLT players_games table is managed by the source and not renamed in config.
    if not table_name and source_key == "chess_com_api":
        table_name = "players_games"

    if not table_name:
        raise ValueError(f"Missing postgres.tables.{source_key}.name in config.yml")

    return table_name, index_field


def _validate_identifier(value: str, label: str) -> str:
    if not IDENTIFIER_RE.match(value):
        raise ValueError(f"Invalid SQL identifier for {label}: {value}")
    return value


def _build_index_name(table_name: str, index_field: str) -> str:
    base = f"idx_{table_name}_{index_field}"
    if len(base) <= 63:
        return base
    suffix = hashlib.md5(base.encode("utf-8")).hexdigest()[:8]
    return f"{base[:54]}_{suffix}"


def create_index_if_not_exists(engine: Engine, schema_name: str, table_name: str, index_field: str | None) -> None:
    if not index_field:
        return

    schema_name = _validate_identifier(schema_name, "schema")
    table_name = _validate_identifier(table_name, "table")
    index_field = _validate_identifier(index_field, "index_field")
    index_name = _validate_identifier(_build_index_name(table_name, index_field), "index_name")

    query = text(
        f'CREATE INDEX IF NOT EXISTS "{index_name}" '
        f'ON "{schema_name}"."{table_name}" ("{index_field}")'
    )
    with engine.begin() as conn:
        conn.execute(query)

def table_with_prefix_exists(engine: Engine, schema_name: str, table_prefix: str) -> bool:

    inspector = inspect(engine)
    tables = inspector.get_table_names(schema=schema_name)
    
    return any(t.startswith(table_prefix) for t in tables)

def games_to_process(engine: Engine, schema: str, table: str, limit: int = 10) -> str:
    config = load_config()
    processable_games_condition = get_processable_games_condition().replace("%", "%%")

    schema_games = config["postgres"]["schemas"]["chess_com_api"]
    table_games  = "players_games" # DLT built-in table name (cannot be changed)

    if table_with_prefix_exists(engine, schema, table):

        # Identify new record (to process) from the games table
        query = f"""
        SELECT
            game.uuid,
            MAX(game.pgn) AS pgn,
            MAX(game.end_time) AS end_time
        FROM {schema_games}.{table_games} game
        LEFT JOIN (
            SELECT DISTINCT uuid FROM {schema}.{table}
        ) target_table
        ON game.uuid = target_table.uuid
        WHERE 
            target_table.uuid IS NULL
            AND {processable_games_condition}
        GROUP BY game.uuid
        ORDER BY end_time DESC -- Process the fresh games first
        LIMIT {limit}
        """
    else:
        query = f"""
        SELECT 
            game.uuid,
            MAX(game.pgn) AS pgn 
        FROM {schema_games}.{table_games} game
        WHERE TRUE
            AND {processable_games_condition}
        GROUP BY 1
        LIMIT {limit}
    """

    return query