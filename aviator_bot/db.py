"""MySQL helpers for persisting multipliers and predictions."""

from __future__ import annotations

import contextlib
from typing import List, Sequence

import mysql.connector

from . import config


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS multipliers (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    value DECIMAL(10, 2) NOT NULL,
    observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB;
"""

INSERT_SQL = "INSERT INTO multipliers (value) VALUES (%s)"

FETCH_RECENT_SQL = """
SELECT value
FROM multipliers
ORDER BY observed_at DESC, id DESC
LIMIT %s;
"""

COUNT_SQL = "SELECT COUNT(*) FROM multipliers"


@contextlib.contextmanager
def get_connection(settings=None):
    cfg = settings or config.get_settings()
    conn = mysql.connector.connect(
        host=cfg.mysql_host,
        port=cfg.mysql_port,
        user=cfg.mysql_user,
        password=cfg.mysql_password,
        database=cfg.mysql_database,
        autocommit=False,
    )
    try:
        yield conn
    finally:
        conn.close()


def initialize_schema(settings=None) -> None:
    with get_connection(settings) as conn:
        cursor = conn.cursor()
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()


def ping(settings=None) -> None:
    """Fail fast when a conexão MySQL não responde."""

    with get_connection(settings) as conn:
        conn.ping(reconnect=True, attempts=2, delay=1)


def insert_multipliers(values: Sequence[float], settings=None) -> int:
    if not values:
        return 0
    with get_connection(settings) as conn:
        cursor = conn.cursor()
        cursor.executemany(INSERT_SQL, [(v,) for v in values])
        conn.commit()
        return cursor.rowcount


def fetch_recent_multipliers(limit: int, settings=None) -> List[float]:
    with get_connection(settings) as conn:
        cursor = conn.cursor()
        cursor.execute(FETCH_RECENT_SQL, (limit,))
        return [float(row[0]) for row in cursor.fetchall()]


def count_multipliers(settings=None) -> int:
    with get_connection(settings) as conn:
        cursor = conn.cursor()
        cursor.execute(COUNT_SQL)
        (count,) = cursor.fetchone()
        return int(count)
