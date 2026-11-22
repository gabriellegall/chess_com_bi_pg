"""Export Cube query results as JSON snapshots for the Claude dashboard.

Each dataset is one Cube REST query (/v1/load). Cube compiles the SQL; the
compiled SQL (/v1/sql) and the query are stored next to the rows in `meta`,
so every number on the dashboard can be traced back to Cube.

Usage: python dashboard/export_cube_snapshot.py <out_dir> [dataset ...]
Reads CUBE_API_SECRET from .env; Cube must be reachable on CUBE_API_URL
(default http://localhost:4000).
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUBE_API_URL = os.environ.get("CUBE_API_URL", "http://localhost:4000")

# Filter grain shared by every dataset: the dashboard's global filters
# (player, time class, both ratings, end date) are applied on these columns.
FILTER_DIMENSIONS = [
    "v_games.username_global",
    "v_games.time_class",
    "v_games.playing_rating",
    "v_games.opponent_rating",
]
FILTER_TIME = {"dimension": "v_games.end_time", "granularity": "day"}

DATASETS = {
    # Section "Results & context": every measure is additive, so the page can
    # filter rows and re-sum them without changing Cube's definitions.
    "games_results": {
        "dimensions": FILTER_DIMENSIONS + [
            "v_games.playing_as",
            "v_games.playing_result",
            "v_games.playing_rating_band",
            "v_games.opponent_rating_band",
            "v_games.rating_gap_category",
        ],
        "measures": [
            "v_games.nb_games_played",
            "v_games.nb_wins",
            "v_games.nb_draws",
            "v_games.nb_losses",
            "v_games.avg_playing_rating",
            "v_games.avg_opponent_rating",
        ],
        "timeDimensions": [FILTER_TIME],
        "order": {"v_games.end_time": "asc"},
        "limit": 50000,
    },
}


def read_env(key):
    for line in (ROOT / ".env").read_text().splitlines():
        k, _, v = line.partition("=")
        if k.strip() == key:
            return v.strip().strip('"')
    raise KeyError(key)


def token():
    def b64(raw):
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    now = int(time.time())
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps({"iat": now, "exp": now + 3600}).encode())
    sig = hmac.new(read_env("CUBE_API_SECRET").encode(), f"{head}.{body}".encode(), hashlib.sha256)
    return f"{head}.{body}.{b64(sig.digest())}"


def call(route, query, tok):
    url = f"{CUBE_API_URL}/cubejs-api/v1/{route}?query={urllib.parse.quote(json.dumps(query))}"
    for _ in range(60):
        req = urllib.request.Request(url, headers={"Authorization": tok})
        res = json.load(urllib.request.urlopen(req))
        if res.get("error") != "Continue wait":
            if "error" in res:
                raise RuntimeError(res["error"])
            return res
        time.sleep(1)
    raise TimeoutError(route)


def short(member):
    # "v_games.end_time.day" -> "end_time"; "v_games.nb_wins" -> "nb_wins"
    return member.split(".")[1]


def export(name, query, tok, out_dir):
    data = call("load", query, tok)
    sql = call("sql", query, tok)["sql"]["sql"]
    numeric = {m for m in query["measures"]} | {
        d for d in query["dimensions"]
        if data["annotation"]["dimensions"].get(d, {}).get("type") == "number"
    }
    time_dims = {t["dimension"] for t in query.get("timeDimensions", [])}
    rows = []
    for r in data["data"]:
        row = {}
        for k, v in r.items():
            if k.count(".") == 2:  # time dimension with granularity -> YYYY-MM-DD
                row[short(k)] = v[:10] if v else None
            elif k in time_dims:  # same value without granularity: skip
                continue
            elif k in numeric:
                n = None if v is None else round(float(v), 6)
                row[short(k)] = int(n) if n is not None and n.is_integer() else n
            else:
                row[short(k)] = v
        rows.append(row)
    exported = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta = [
        {"label": "Cube query (/v1/load)", "value": json.dumps(query, indent=2), "type": "code", "lang": "json"},
        {"label": "SQL compiled by Cube", "value": sql[0], "type": "code", "lang": "sql"},
        {"label": "export_cube_snapshot.py", "value": Path(__file__).read_text(), "type": "code", "lang": "python"},
        {"label": "Exported", "value": exported},
    ]
    path = Path(out_dir) / f"{name}.json"
    path.write_text(json.dumps({"rows": rows, "meta": meta}, separators=(",", ":")))
    print(f"{name}: {len(rows)} rows -> {path}")


def main():
    out_dir = sys.argv[1]
    names = sys.argv[2:] or list(DATASETS)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    tok = token()
    for name in names:
        export(name, DATASETS[name], tok, out_dir)


if __name__ == "__main__":
    main()
