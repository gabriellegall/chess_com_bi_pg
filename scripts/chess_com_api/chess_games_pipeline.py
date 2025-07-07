import dlt
from chess import source

def run_pipeline():
    pipeline = dlt.pipeline(
        pipeline_name="chess_games_pipeline",
        destination='postgres',
        dataset_name="stg_chess_com",
    )

    data = source(
        ["zundorn", "piwi100", "chessman1ray"],
        start_month="2025/06",
    )

    info = pipeline.run(
        data.with_resources("players_games"),
        write_disposition="merge",
        primary_key=["uuid", "username"]
    )

    print(info)

if __name__ == "__main__":
    run_pipeline()