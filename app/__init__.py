import os

from dotenv import load_dotenv
from flask import Flask

from .models import db
from .routes.auth import register_auth_routes
from .routes.admin import register_admin_routes
from .routes.quiz import register_quiz_routes
from .services.ai_grader import AIGrader


load_dotenv()


def create_app(config_overrides=None):
    app = Flask(__name__, template_folder="../templates")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///questions.db"
    app.config["SQLALCHEMY_BINDS"] = {"auth": "sqlite:///users.db"}
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if config_overrides:
        app.config.update(config_overrides)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.questions_list = []
    app.questions_loaded = False
    app.active_quiz_table = None
    app.user_answers = []
    app.total_points = 0

    api_key = os.getenv("GEMINI_API_KEY")
    app.ai_grader = AIGrader(api_key=api_key, model_name="gemini-2.5-flash")

    register_auth_routes(app)
    register_quiz_routes(app)
    register_admin_routes(app)
    return app

