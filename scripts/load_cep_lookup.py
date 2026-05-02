#!/usr/bin/env python3
"""
Load data/cep_sp.csv into DuckDB as raw_cep_lookup.
The source CSV has 6 columns but only 5 header names (last header covers two columns),
so column names are provided explicitly.
"""

import sys
import logging
from pathlib import Path

import pandas as pd
import duckdb
from dotenv import load_dotenv
import os

CEP_CSV_PATH = "data/cep_sp.csv"
CEP_TABLE = "raw_cep_lookup"


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("load_cep")


def load_cep_lookup(csv_path: str, db_path: str, logger: logging.Logger) -> None:
    logger.info(f"Reading {csv_path}")
    df = pd.read_csv(
        csv_path,
        names=["cep", "logradouro", "lado", "bairro", "id_cidade", "id_bairro"],
        skiprows=1,
        dtype=str,
    )
    df = df.where(pd.notnull(df), None)

    logger.info(f"Read {len(df)} rows, {df['cep'].nunique()} unique CEPs")

    con = duckdb.connect(db_path)
    con.execute(f"DROP TABLE IF EXISTS {CEP_TABLE}")
    con.register("cep_df", df)
    con.execute(f"""
        CREATE TABLE {CEP_TABLE} AS
        SELECT
            TRIM(cep)        AS cep,
            TRIM(logradouro) AS logradouro,
            TRIM(lado)       AS lado,
            TRIM(bairro)     AS bairro,
            TRIM(id_cidade)  AS id_cidade,
            TRIM(id_bairro)  AS id_bairro
        FROM cep_df
        WHERE cep IS NOT NULL AND TRIM(cep) != ''
    """)
    count = con.execute(f"SELECT COUNT(*) FROM {CEP_TABLE}").fetchone()[0]
    con.close()
    logger.info(f"Loaded {count} rows into {CEP_TABLE}")


if __name__ == "__main__":
    load_dotenv()
    logger = setup_logging()

    db_path = os.environ.get("DB_PATH")
    if not db_path:
        logger.error("DB_PATH environment variable is not set.")
        sys.exit(1)

    if not Path(CEP_CSV_PATH).exists():
        logger.error(f"CSV not found: {CEP_CSV_PATH}")
        sys.exit(1)

    load_cep_lookup(CEP_CSV_PATH, db_path, logger)
