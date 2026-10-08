"""
MySQL connectivity helpers (replaces the earlier Google Sheets backend).

Connection details come from .streamlit/secrets.toml, e.g.:

    [mysql]
    host = "mysql-xxxx.aivencloud.com"
    port = 15575
    user = "avnadmin"
    password = "..."
    db = "defaultdb"

Table structure is generated directly from utils/schemas.SCHEMAS, so the
schema file is the single source of truth for both the UI forms and the
database DDL.
"""

from contextlib import contextmanager

import pandas as pd
import pymysql
import streamlit as st

from utils.schemas import SCHEMAS, CREATION_ORDER

CONNECT_TIMEOUT = 10

# Field type -> MySQL column type
_SQL_TYPE = {
    "text": "VARCHAR(255)",
    "select": "VARCHAR(50)",
    "date": "DATE",
    "number": "DOUBLE",
    "computed": "DOUBLE",
}


class DatabaseError(Exception):
    """Friendly, user-facing wrapper around raw pymysql errors."""


@contextmanager
def get_connection():
    # Accept both the grouped format and the flat DB_* keys used by the
    # repository's secrets.toml.example and Streamlit Cloud settings.
    if "mysql" in st.secrets:
        cfg = st.secrets["mysql"]
    else:
        key_map = {
            "host": "DB_HOST",
            "port": "DB_PORT",
            "user": "DB_USER",
            "password": "DB_PASSWORD",
            "db": "DB_NAME",
        }
        missing = [secret_key for secret_key in key_map.values() if secret_key not in st.secrets]
        if missing:
            raise DatabaseError(
                "MySQL secrets are missing. Add DB_HOST, DB_PORT, DB_USER, "
                "DB_PASSWORD, and DB_NAME to Streamlit Cloud app settings "
                "(or configure them under a [mysql] section)."
            )
        cfg = {config_key: st.secrets[secret_key] for config_key, secret_key in key_map.items()}

    conn = pymysql.connect(
        charset="utf8mb4",
        connect_timeout=cfg.get("connect_timeout", CONNECT_TIMEOUT),
        read_timeout=cfg.get("read_timeout", CONNECT_TIMEOUT),
        write_timeout=cfg.get("write_timeout", CONNECT_TIMEOUT),
        cursorclass=pymysql.cursors.DictCursor,
        db=cfg["db"],
        host=cfg["host"],
        password=cfg["password"],
        port=int(cfg["port"]),
        user=cfg["user"],
        autocommit=True,
    )
    try:
        yield conn
    finally:
        conn.close()


def _column_ddl(field: dict, is_pk: bool) -> str:
    col_type = _SQL_TYPE[field["type"]]
    notnull = " NOT NULL" if field.get("required") and not is_pk else ""
    return f"`{field['name']}` {col_type}{notnull}"


def _table_ddl(dataset_name: str) -> str:
    schema = SCHEMAS[dataset_name]
    fields = schema["fields"]
    pk = schema["pk"]
    autoincrement = schema["autoincrement_pk"]

    lines = []
    if autoincrement:
        lines.append("`id` INT AUTO_INCREMENT PRIMARY KEY")
        for f in fields:
            lines.append(_column_ddl(f, is_pk=False))
    else:
        for f in fields:
            is_pk = f["name"] == pk
            lines.append(_column_ddl(f, is_pk=is_pk))

    fk = schema.get("foreign_key")
    if fk:
        ref_dataset = SCHEMAS[fk["references_dataset"]]
        ref_table = ref_dataset["table"]
        ref_col = ref_dataset["pk"]
        lines.append(
            f"FOREIGN KEY (`{fk['column']}`) REFERENCES `{ref_table}`(`{ref_col}`) "
            "ON UPDATE CASCADE ON DELETE CASCADE"
        )

    pk_clause = f", PRIMARY KEY (`{pk}`)" if not autoincrement else ""
    body = ",\n    ".join(lines)
    return (
        f"CREATE TABLE IF NOT EXISTS `{schema['table']}` (\n    {body}{pk_clause}\n"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    )


def init_database():
    """Create every table (if not already present) in FK-safe order."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            for dataset_name in CREATION_ORDER:
                cur.execute(_table_ddl(dataset_name))


def test_connection() -> str:
    """Quick connectivity check. Returns the MySQL version string on success."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION() AS v")
            return cur.fetchone()["v"]


def _translate_error(e: pymysql.err.Error, dataset_name: str) -> DatabaseError:
    code = e.args[0] if e.args else None
    schema = SCHEMAS[dataset_name]
    if code == 1062:  # duplicate primary key
        return DatabaseError(
            f"A record with this {schema['pk']} already exists in '{dataset_name}'."
        )
    if code == 1452:  # FK constraint failure
        fk = schema.get("foreign_key")
        col = fk["column"] if fk else "reference field"
        return DatabaseError(
            f"The {col} you entered was not found in Student Database. "
            "Please add that student first, or check for a typo."
        )
    return DatabaseError(f"Database error: {e}")


def insert_record(dataset_name: str, values: dict):
    """Insert a single row. Raises DatabaseError with a friendly message on failure."""
    schema = SCHEMAS[dataset_name]
    columns = [f["name"] for f in schema["fields"]]
    cols_sql = ", ".join(f"`{c}`" for c in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO `{schema['table']}` ({cols_sql}) VALUES ({placeholders})"
    row = [values.get(c) if values.get(c) not in ("", None) else None for c in columns]

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, row)
    except pymysql.err.Error as e:
        raise _translate_error(e, dataset_name)


def insert_records(dataset_name: str, records: list[dict]):
    """
    Insert many rows, one at a time (so one bad row doesn't sink the whole
    batch). Returns (success_count, list_of_(row_index, error_message)).
    """
    schema = SCHEMAS[dataset_name]
    columns = [f["name"] for f in schema["fields"]]
    cols_sql = ", ".join(f"`{c}`" for c in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO `{schema['table']}` ({cols_sql}) VALUES ({placeholders})"

    success_count = 0
    errors = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            for i, values in enumerate(records):
                row = [values.get(c) if values.get(c) not in ("", None) else None for c in columns]
                try:
                    cur.execute(sql, row)
                    success_count += 1
                except pymysql.err.Error as e:
                    errors.append((i, str(_translate_error(e, dataset_name))))

    return success_count, errors


@st.cache_data(ttl=30, show_spinner=False)
def fetch_dataframe(dataset_name: str) -> pd.DataFrame:
    schema = SCHEMAS[dataset_name]
    columns = [f["name"] for f in schema["fields"]]
    cols_sql = ", ".join(f"`{c}`" for c in columns)
    sql = f"SELECT {cols_sql} FROM `{schema['table']}`"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=columns)
    return df


def clear_cache():
    fetch_dataframe.clear()
