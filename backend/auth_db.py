import psycopg2
from psycopg2 import sql

from backend.config import Settings


def is_auth_configured(settings: Settings) -> bool:
    return bool(settings.database_url)


def _table_identifier(table_name: str) -> sql.Identifier:
    parts = [part for part in table_name.split(".") if part]
    if not parts:
        parts = ["usuarios"]
    return sql.Identifier(*parts)


def verify_user_credentials(username: str, password: str, settings: Settings) -> bool:
    if not username or not password:
        return False

    db_url = settings.database_url
    if not db_url:
        raise RuntimeError("DATABASE_URL no configurada.")

    user_value = username.strip()
    if not user_value:
        return False

    table = _table_identifier(settings.auth_users_table or "usuarios")
    user_col = sql.Identifier("username")
    pass_col = sql.Identifier("password_hash")

    query = sql.SQL(
        "SELECT 1 FROM {table} "
        "WHERE {user_col} = %s AND {pass_col} = crypt(%s, {pass_col}) "
        "LIMIT 1"
    ).format(table=table, user_col=user_col, pass_col=pass_col)

    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_value, password))
            return cur.fetchone() is not None
