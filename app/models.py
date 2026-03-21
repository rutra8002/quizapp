import re

from sqlalchemy import MetaData, Table, inspect
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def is_valid_table_name(table_name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name or ""))


def get_table(table_name: str) -> Table:
    if not is_valid_table_name(table_name):
        raise ValueError("Invalid table name")

    inspector = inspect(db.engine)
    if table_name not in inspector.get_table_names():
        raise LookupError("Table not found")

    return Table(table_name, MetaData(), autoload_with=db.engine)

