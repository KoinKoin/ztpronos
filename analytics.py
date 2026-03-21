import duckdb
from pathlib import Path

DATA_DIR = Path("data")

def get_connection(db_path=":memory:"):
    """
    Returns a DuckDB connection with views on top of Parquet lake.
    """
    con = duckdb.connect(db_path)

    # Enable performance features
    con.execute("PRAGMA threads=4")
    con.execute("PRAGMA enable_object_cache")

    register_views(con)

    return con


def register_views(con):
    """
    Register all datasets as DuckDB views.
    """

    base = DATA_DIR.as_posix()

    con.execute(f"""
        CREATE OR REPLACE VIEW course AS
        SELECT * FROM read_parquet('{base}/course/**/*.parquet', hive_partitioning=1)
    """)

    con.execute(f"""
        CREATE OR REPLACE VIEW arrivee AS
        SELECT * FROM read_parquet('{base}/arrivee/**/*.parquet', hive_partitioning=1)
    """)

    con.execute(f"""
        CREATE OR REPLACE VIEW pronos AS
        SELECT * FROM read_parquet('{base}/pronos/**/*.parquet', hive_partitioning=1)
    """)

    con.execute(f"""
        CREATE OR REPLACE VIEW rapports AS
        SELECT * FROM read_parquet('{base}/rapports/**/*.parquet', hive_partitioning=1)
    """)


def refresh(con):
    """
    Reload views (useful if new Parquet files added)
    """
    register_views(con)
