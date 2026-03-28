import random

from flask import abort, current_app, redirect, render_template, request, url_for
from sqlalchemy import inspect, select

from ..models import db, get_table


def _reset_quiz_state() -> None:
    current_app.questions_list = []
    current_app.questions_loaded = False
    current_app.active_quiz_table = None
    current_app.user_answers = []
    current_app.total_points = 0


def _is_quiz_table(table_name: str) -> bool:
    inspector = inspect(db.engine)
    column_names = {column["name"] for column in inspector.get_columns(table_name)}
    return {"question", "answer"}.issubset(column_names)


def _get_table_or_abort(table_name: str):
    try:
        table = get_table(table_name)
        if not _is_quiz_table(table_name):
            abort(404)
        return table
    except ValueError:
        abort(400)
    except LookupError:
        abort(404)


def index():
    _reset_quiz_state()

    inspector = inspect(db.engine)
    table_names = [name for name in inspector.get_table_names() if _is_quiz_table(name)]
    return render_template("index.html", table_names=table_names)


def quiz(table_name):
    is_new_table = current_app.active_quiz_table != table_name
    if is_new_table:
        _reset_quiz_state()

    if not current_app.questions_loaded:
        table = _get_table_or_abort(table_name)
        current_app.questions_list = db.session.execute(select(table)).all()
        current_app.questions_loaded = True
        current_app.active_quiz_table = table_name

    total_questions = len(current_app.questions_list)
    if total_questions == 0:
        return redirect(url_for("quiz_completed"))

    question = random.choice(current_app.questions_list)
    answer_lines = question.answer_lines
    return render_template(
        "quiz.html",
        question=question.question,
        table_name=table_name,
        total_points=current_app.total_points,
        total_questions=total_questions,
        answer_lines=answer_lines,
    )


def answer():
    question_text = request.form["question"]
    table_name = request.form["table_name"]

    if "answer_0" in request.form:
        answers = []
        index_value = 0
        while f"answer_{index_value}" in request.form:
            answer_part = request.form[f"answer_{index_value}"].strip()
            if answer_part:
                answers.append(answer_part)
            index_value += 1
        answer_text = "\n".join(answers)
    else:
        answer_text = request.form["answer"]

    question = next((item for item in current_app.questions_list if item.question == question_text), None)
    if question:
        ref_answer = question.answer
        score = current_app.ai_grader.score(question_text, ref_answer, answer_text)
        score_label = f"{score}/10"

        current_app.user_answers.append(
            {
                "question": question_text,
                "answer": answer_text,
                "expected": ref_answer,
                "score": score,
                "score_label": score_label,
            }
        )
        current_app.total_points += score
        current_app.questions_list.remove(question)

    if len(current_app.questions_list) == 0:
        return redirect(url_for("quiz_completed"))
    return redirect(url_for("quiz", table_name=table_name))


def quiz_completed():
    total_attempts = len(current_app.user_answers)
    max_points = total_attempts * 10

    return render_template(
        "quiz_completed.html",
        total_points=current_app.total_points,
        max_points=max_points,
        attempted_answers=current_app.user_answers,
    )


def register_quiz_routes(app):
    app.add_url_rule("/", view_func=index)
    app.add_url_rule("/quiz/<table_name>", view_func=quiz)
    app.add_url_rule("/answer", view_func=answer, methods=["POST"])
    app.add_url_rule("/end_screen", view_func=quiz_completed)

