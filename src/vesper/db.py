"""Thin Postgres layer: connections + additive migration runner. Raw SQL only —
the deterministic feature computation lives in tools/history.py as pure
functions so it can be unit-tested without a database."""

import logging
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from vesper.config import settings

log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


def connect() -> psycopg.Connection:
    return psycopg.connect(settings().database_url, row_factory=dict_row)


def migrate(conn: psycopg.Connection) -> None:
    """Apply every migrations/*.sql in name order. Files are idempotent, so we
    simply re-run them all — no version table needed while the set is small."""
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        log.info("applying migration %s", path.name)
        conn.execute(path.read_text())
    conn.commit()
