import os
import random
import json
from pathlib import Path

from flask import abort, current_app, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import Column, Integer, MetaData, Table, Text, create_engine, inspect, select

from ..models import is_valid_table_name, db, TestAttempt
from ..services.ai_grader import AIModelUnavailableError, AIRateLimitError


def _reset_quiz_state() -> None:
    session["quiz_state"] = {
        "active_quiz_table": None,
        "remaining_question_ids": [],
        "user_answers": [],
        "total_points": 0,
    }
    session.modified = True


def _get_quiz_state() -> dict:
    state = session.get("quiz_state")
    if not isinstance(state, dict):
        _reset_quiz_state()
        return session["quiz_state"]

    state.setdefault("active_quiz_table", None)
    state.setdefault("remaining_question_ids", [])
    state.setdefault("user_answers", [])
    state.setdefault("total_points", 0)
    return state


def _save_quiz_state(state: dict) -> None:
    session["quiz_state"] = state
    session.modified = True


def _get_user_engine():
    user = g.get("current_user")
    if user is None:
        abort(401)

    base_dir = current_app.config.get("USER_QUIZ_DB_DIR", current_app.instance_path)
    if current_app.config.get("TESTING") and os.path.abspath(str(base_dir)) == os.path.abspath(current_app.instance_path):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(current_app.root_path), "tests", ".tmp_user_quiz_dbs")
        )
    os.makedirs(base_dir, exist_ok=True)
    db_path = Path(base_dir) / f"quiz_user_{user.id}.db"
    return create_engine(f"sqlite:///{db_path.as_posix()}")


def _is_quiz_table(engine, table_name: str) -> bool:
    inspector = inspect(engine)
    column_names = {column["name"] for column in inspector.get_columns(table_name)}
    return {"question", "answer"}.issubset(column_names)


def _list_user_quiz_tables(engine) -> list[str]:
    inspector = inspect(engine)
    return [name for name in inspector.get_table_names() if _is_quiz_table(engine, name)]


def _get_table_or_abort(engine, table_name: str):
    if not is_valid_table_name(table_name):
        abort(400)

    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        abort(404)

    if not _is_quiz_table(engine, table_name):
        abort(404)

    return Table(table_name, MetaData(), autoload_with=engine)


def _require_login():
    if g.get("current_user") is None:
        return redirect(url_for("login"))
    return None


def index():
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    _reset_quiz_state()
    engine = _get_user_engine()
    table_names = _list_user_quiz_tables(engine)
    return render_template("index.html", table_names=table_names)


def quiz(table_name):
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    engine = _get_user_engine()
    state = _get_quiz_state()

    is_new_table = state["active_quiz_table"] != table_name
    if is_new_table:
        state = {
            "active_quiz_table": table_name,
            "remaining_question_ids": [],
            "user_answers": [],
            "total_points": 0,
        }

    if not state["remaining_question_ids"]:
        table = _get_table_or_abort(engine, table_name)
        with engine.connect() as connection:
            question_ids = [row.id for row in connection.execute(select(table.c.id)).all()]
        state["remaining_question_ids"] = question_ids
        state["active_quiz_table"] = table_name
        _save_quiz_state(state)

    total_questions = len(state["remaining_question_ids"])
    if total_questions == 0:
        return redirect(url_for("quiz_completed"))

    question_id = random.choice(state["remaining_question_ids"])
    table = _get_table_or_abort(engine, table_name)
    with engine.connect() as connection:
        question = connection.execute(select(table).where(table.c.id == question_id)).first()

    if question is None:
        state["remaining_question_ids"] = [qid for qid in state["remaining_question_ids"] if qid != question_id]
        _save_quiz_state(state)
        return redirect(url_for("quiz", table_name=table_name))

    answer_lines = question.answer_lines or 1
    return render_template(
        "quiz.html",
        question=question.question,
        question_id=question.id,
        table_name=table_name,
        total_points=state["total_points"],
        total_questions=total_questions,
        answer_lines=answer_lines,
    )


def answer():
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    table_name = request.form.get("table_name", "")
    question_id_raw = request.form.get("question_id", "")
    try:
        question_id = int(question_id_raw)
    except (TypeError, ValueError):
        abort(400)

    answer_text = request.form.get("answer", "").strip()

    state = _get_quiz_state()
    if state.get("active_quiz_table") != table_name:
        abort(400)

    remaining_ids = state.get("remaining_question_ids", [])
    if question_id not in remaining_ids:
        abort(400)

    engine = _get_user_engine()
    table = _get_table_or_abort(engine, table_name)
    with engine.connect() as connection:
        question = connection.execute(select(table).where(table.c.id == question_id)).first()

    if question is None:
        abort(404)

    ref_answer = question.answer
    try:
        score = current_app.ai_grader.score(question.question, ref_answer, answer_text)
    except AIModelUnavailableError:
        flash(
            "AI grading service is temporarily unavailable. Your answer was graded using fallback logic.",
            "error",
        )
        score = 10 if answer_text.strip().lower() == str(ref_answer).strip().lower() else 0
    except AIRateLimitError:
        flash(
            "AI grading is rate-limited right now. Your answer was graded using fallback logic — try again shortly.",
            "error",
        )
        score = 10 if answer_text.strip().lower() == str(ref_answer).strip().lower() else 0
    score_label = f"{score}/10"

    state["user_answers"].append(
        {
            "question": question.question,
            "answer": answer_text,
            "expected": ref_answer,
            "score": score,
            "score_label": score_label,
        }
    )
    state["total_points"] += score
    state["remaining_question_ids"] = [qid for qid in remaining_ids if qid != question_id]
    _save_quiz_state(state)

    if len(state["remaining_question_ids"]) == 0:
        return redirect(url_for("quiz_completed"))
    return redirect(url_for("quiz", table_name=table_name))


def quiz_completed():
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    state = _get_quiz_state()
    total_attempts = len(state["user_answers"])
    max_points = total_attempts * 10
    table_name = state.get("active_quiz_table", "Unknown")
    user = g.get("current_user")

    if user and state["user_answers"]:
        attempt = TestAttempt(
            user_id=user.id,
            test_name=table_name,
            score=state["total_points"],
            max_score=max_points,
            answers=json.dumps(state["user_answers"]),
        )
        db.session.add(attempt)
        db.session.commit()

    return render_template(
        "quiz_completed.html",
        total_points=state["total_points"],
        max_points=max_points,
        attempted_answers=state["user_answers"],
    )


def admin():
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    engine = _get_user_engine()
    table_names = _list_user_quiz_tables(engine)
    return render_template("admin.html", table_names=table_names)


def test_history():
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    user = g.get("current_user")
    attempts = TestAttempt.query.filter_by(user_id=user.id).order_by(TestAttempt.created_at.desc()).all()
    return render_template("test_history.html", attempts=attempts)


def test_details(attempt_id):
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    user = g.get("current_user")
    attempt = TestAttempt.query.filter_by(id=attempt_id, user_id=user.id).first()
    if attempt is None:
        abort(404)

    answers = json.loads(attempt.answers)
    return render_template("attempt_details.html", attempt=attempt, answers=answers)


def create_table():
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    table_name = request.form["table_name"]
    if not is_valid_table_name(table_name):
        abort(400)
    if table_name == "users":
        abort(400)

    engine = _get_user_engine()
    metadata = MetaData()
    quiz_table = Table(
        table_name,
        metadata,
        Column("id", Integer, primary_key=True),
        Column("question", Text),
        Column("answer", Text),
        Column("answer_lines", Integer, nullable=False, default=1),
    )
    metadata.create_all(engine, tables=[quiz_table], checkfirst=True)
    return redirect(url_for("admin"))


def edit_table(table_name):
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    engine = _get_user_engine()
    table = _get_table_or_abort(engine, table_name)
    with engine.connect() as connection:
        questions = connection.execute(select(table)).all()
    return render_template("edit_table.html", table_name=table_name, questions=questions)


def add_question(table_name):
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    question = request.form["question"]
    answer = request.form["answer"]
    try:
        answer_lines = int(request.form.get("answer_lines", 1))
    except (TypeError, ValueError):
        abort(400)
    if answer_lines < 1:
        abort(400)

    engine = _get_user_engine()
    table = _get_table_or_abort(engine, table_name)
    with engine.begin() as connection:
        connection.execute(table.insert().values(question=question, answer=answer, answer_lines=answer_lines))
    return redirect(url_for("edit_table", table_name=table_name))


def edit_question(table_name, question_id):
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    engine = _get_user_engine()
    table = _get_table_or_abort(engine, table_name)
    if request.method == "POST":
        new_question = request.form["question"]
        new_answer = request.form["answer"]
        try:
            answer_lines = int(request.form.get("answer_lines", 1))
        except (TypeError, ValueError):
            abort(400)
        if answer_lines < 1:
            abort(400)

        with engine.begin() as connection:
            connection.execute(
                table.update()
                .where(table.c.id == question_id)
                .values(question=new_question, answer=new_answer, answer_lines=answer_lines)
            )
        return redirect(url_for("edit_table", table_name=table_name))

    with engine.connect() as connection:
        question = connection.execute(select(table).where(table.c.id == question_id)).first()
    if question is None:
        abort(404)
    return render_template("edit_question.html", table_name=table_name, question=question)


def delete_question(table_name, question_id):
    login_redirect = _require_login()
    if login_redirect is not None:
        return login_redirect

    engine = _get_user_engine()
    table = _get_table_or_abort(engine, table_name)
    with engine.begin() as connection:
        connection.execute(table.delete().where(table.c.id == question_id))
    return redirect(url_for("edit_table", table_name=table_name))


def register_quiz_routes(app):
    app.add_url_rule("/", view_func=index)
    app.add_url_rule("/quiz/<table_name>", view_func=quiz)
    app.add_url_rule("/answer", view_func=answer, methods=["POST"])
    app.add_url_rule("/end_screen", view_func=quiz_completed)
    app.add_url_rule("/history", view_func=test_history)
    app.add_url_rule("/history/<int:attempt_id>", view_func=test_details)
    app.add_url_rule("/admin", view_func=admin)
    app.add_url_rule("/admin/create_table", view_func=create_table, methods=["POST"])
    app.add_url_rule("/admin/edit_table/<table_name>", view_func=edit_table)
    app.add_url_rule("/admin/add_question/<table_name>", view_func=add_question, methods=["POST"])
    app.add_url_rule(
        "/admin/edit_question/<table_name>/<int:question_id>",
        view_func=edit_question,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/admin/delete_question/<table_name>/<int:question_id>",
        view_func=delete_question,
        methods=["POST"],
    )

