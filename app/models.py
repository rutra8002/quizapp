import re
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import MetaData, Table, inspect
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    __bind_key__ = "auth"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


class TestAttempt(db.Model):
    __tablename__ = "test_attempts"
    __bind_key__ = "auth"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    test_name = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    answers = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "test_name": self.test_name,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": round((self.score / self.max_score * 100) if self.max_score > 0 else 0),
            "created_at": self.created_at,
        }


def is_valid_table_name(table_name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name or ""))


def get_table(table_name: str) -> Table:
    if not is_valid_table_name(table_name):
        raise ValueError("Invalid table name")

    inspector = inspect(db.engine)
    if table_name not in inspector.get_table_names():
        raise LookupError("Table not found")

    return Table(table_name, MetaData(), autoload_with=db.engine)

