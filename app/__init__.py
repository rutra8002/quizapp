import os

from dotenv import load_dotenv
from flask import Flask

from .errors import register_error_handlers
from .models import db
from .routes.auth import register_auth_routes
from .routes.quiz import register_quiz_routes
from .services.ai_grader import AIGrader


load_dotenv()


def create_app(config_overrides=None):
    app = Flask(__name__, template_folder="../templates")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_BINDS"] = {"auth": "sqlite:///users.db"}
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["USER_QUIZ_DB_DIR"] = app.instance_path
    if config_overrides:
        app.config.update(config_overrides)

    has_custom_user_db_dir = bool(config_overrides and "USER_QUIZ_DB_DIR" in config_overrides)
    if app.config.get("TESTING") and not has_custom_user_db_dir:
        app.config["USER_QUIZ_DB_DIR"] = os.path.abspath(
            os.path.join(os.path.dirname(app.root_path), "tests", ".tmp_user_quiz_dbs")
        )
    db.init_app(app)

    with app.app_context():
        db.create_all()


    api_key = os.getenv("GEMINI_API_KEY")
    app.ai_grader = AIGrader(api_key=api_key, model_name="gemini-2.5-flash")

    register_auth_routes(app)
    register_quiz_routes(app)
    register_error_handlers(app)
    return app

