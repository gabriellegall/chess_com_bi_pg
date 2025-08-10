import yaml
import subprocess
import sys
from scripts.helper import get_engine
from sqlalchemy import text

def extract_schemas_from_dbt_project(dbt_config):
    """Helper to extract schema names from dbt_project.yml config."""
    schemas = set()
    project_name = dbt_config.get("name")
    if not project_name:
        return schemas

    # Get schemas from models
    models_config = dbt_config.get("models", {}).get(project_name, {})
    for model_group in models_config.values():
        if isinstance(model_group, dict) and model_group.get("+schema"):
            schemas.add(model_group["+schema"])

    # Get schema from seeds
    seeds_config = dbt_config.get("seeds", {}).get(project_name, {})
    if isinstance(seeds_config, dict) and seeds_config.get("+schema"):
        schemas.add(seeds_config["+schema"])

    return schemas

def get_schemas_all_from_config():
    schemas = set()
    # Load config.yml
    with open("scripts/config.yml", "r") as f:
        config = yaml.safe_load(f)
        postgres_schemas = config.get("postgres", {}).get("schemas", {})
        for key, schema in postgres_schemas.items():
            if key == "stockfish": # ignore stockfish YAML key
                continue
            schemas.add(schema)
            # Add _staging variant for chess_com_api (automatic schema with the Data Load Tool (DLT) Python library)
            if key == "chess_com_api":
                schemas.add(f"{schema}_staging")

    # Load dbt_project.yml to get model and seed schemas
    with open("dbt_project.yml", "r") as f:
        dbt_config = yaml.safe_load(f)
        schemas.update(extract_schemas_from_dbt_project(dbt_config))

    return list(schemas)

def drop_schemas():
    """
    This function will delete all staging schemas except Stockfish, as well as all DBT schemas.
    Finally, it executes the regular run_all.py script.
    """
    schemas = get_schemas_all_from_config()
    print("The following schemas will be dropped:")
    for schema in schemas:
        print(f"- {schema}")
    
    proceed = input("Would you like to proceed? (Y/N): ").strip().upper()
    if proceed == 'Y':
        engine = get_engine()
        with engine.connect() as conn:
            for schema in schemas:
                print(f"Dropping schema: {schema}")
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE;'))
            conn.commit()
        print("✅ Schemas dropped.")
        print("🚀 Running run_all.py...")
        subprocess.run([sys.executable, "run_all.py"], check=True)
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    drop_schemas()