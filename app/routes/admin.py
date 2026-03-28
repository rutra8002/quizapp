from flask import abort, redirect, render_template, request, url_for
from sqlalchemy import Column, Integer, MetaData, Table, Text, inspect, select

from ..models import db, get_table, is_valid_table_name


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


def admin():
    inspector = inspect(db.engine)
    table_names = [name for name in inspector.get_table_names() if _is_quiz_table(name)]
    return render_template("admin.html", table_names=table_names)


def create_table():
    table_name = request.form["table_name"]
    if not is_valid_table_name(table_name):
        abort(400)
    if table_name == "users":
        abort(400)

    metadata = MetaData()
    quiz_table = Table(
        table_name,
        metadata,
        Column("id", Integer, primary_key=True),
        Column("question", Text),
        Column("answer", Text),
        Column("answer_lines", Integer, nullable=False, default=1),
    )
    metadata.create_all(db.engine, tables=[quiz_table], checkfirst=True)
    return redirect(url_for("admin"))


def edit_table(table_name):
    table = _get_table_or_abort(table_name)
    questions = db.session.execute(select(table)).all()
    return render_template("edit_table.html", table_name=table_name, questions=questions)


def add_question(table_name):
    question = request.form["question"]
    answer = request.form["answer"]
    answer_lines = int(request.form.get("answer_lines", 1))

    table = _get_table_or_abort(table_name)
    db.session.execute(table.insert().values(question=question, answer=answer, answer_lines=answer_lines))
    db.session.commit()
    return redirect(url_for("edit_table", table_name=table_name))


def edit_question(table_name, question_id):
    table = _get_table_or_abort(table_name)
    if request.method == "POST":
        new_question = request.form["question"]
        new_answer = request.form["answer"]
        answer_lines = int(request.form.get("answer_lines", 1))

        db.session.execute(
            table.update()
            .where(table.c.id == question_id)
            .values(question=new_question, answer=new_answer, answer_lines=answer_lines)
        )
        db.session.commit()
        return redirect(url_for("edit_table", table_name=table_name))

    question = db.session.execute(select(table).where(table.c.id == question_id)).first()
    return render_template("edit_question.html", table_name=table_name, question=question)


def delete_question(table_name, question_id):
    table = _get_table_or_abort(table_name)
    db.session.execute(table.delete().where(table.c.id == question_id))
    db.session.commit()
    return redirect(url_for("edit_table", table_name=table_name))


def register_admin_routes(app):
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

