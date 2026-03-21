import os

from dotenv import load_dotenv
from flask import Flask

from .models import db
from .routes.admin import register_admin_routes
from .routes.quiz import register_quiz_routes
from .services.ai_grader import AIGrader


load_dotenv()


def create_app():
    app = Flask(__name__, template_folder="../templates")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///questions.db"
    db.init_app(app)

    app.questions_list = []
    app.questions_loaded = False
    app.user_answers = []
    app.total_points = 0

    api_key = os.getenv("GEMINI_API_KEY")
    app.ai_grader = AIGrader(api_key=api_key, model_name="gemini-2.5-flash")

    register_quiz_routes(app)
    register_admin_routes(app)
    return app

