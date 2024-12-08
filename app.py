from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///questions.db'
db = SQLAlchemy(app)

correct_answers = 0
wrong_answers = 0
questions_list = []
questions_loaded = False

user_answers = []

class Question:
    def __init__(self, id, question, answer):
        self.id = id
        self.question = question
        self.answer = answer

@app.route('/')
def index():
    global questions_list, questions_loaded, correct_answers, wrong_answers, user_answers
    questions_list = []
    questions_loaded = False
    correct_answers = 0
    wrong_answers = 0
    user_answers = []
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    return render_template('index.html', table_names=table_names)

@app.route('/quiz/<table_name>')
def quiz(table_name):
    global questions_list, questions_loaded
    if not questions_loaded:
        questions_list = db.session.execute(text(f'SELECT * FROM {table_name}')).fetchall()
        questions_loaded = True
    total_questions = len(questions_list)
    if total_questions == 0:
        return redirect(url_for('quiz_completed'))
    question = random.choice(questions_list)
    return render_template('quiz.html', question=question.question, table_name=table_name, correct_answers=correct_answers, total_questions=total_questions)

@app.route('/answer', methods=['POST'])
def answer():
    global correct_answers, wrong_answers, questions_list, user_answers
    question_text = request.form['question']
    answer_text = request.form['answer']
    table_name = request.form['table_name']
    question = next((q for q in questions_list if q.question == question_text), None)
    if question:
        user_answers.append(answer_text)
        if question.answer == answer_text:
            correct_answers += 1
        else:
            wrong_answers += 1
        questions_list.remove(question)

    if len(questions_list) == 0:
        return redirect(url_for('quiz_completed'))
    return redirect(url_for('quiz', table_name=table_name))

@app.route('/end_screen')
def quiz_completed():
    total_attempts = correct_answers + wrong_answers
    correct_percentage = (correct_answers / total_attempts) * 100 if total_attempts > 0 else 0
    wrong_percentage = (wrong_answers / total_attempts) * 100 if total_attempts > 0 else 0
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    all_questions = []
    for table_name in table_names:
        questions = db.session.execute(text(f'SELECT * FROM {table_name}')).fetchall()
        for q in questions:
            all_questions.append(Question(q.id, q.question, q.answer))
    return render_template('quiz_completed.html', correct_percentage=correct_percentage, wrong_percentage=wrong_percentage, all_questions=all_questions, user_answers=user_answers, zip=zip)


### admin things ###

@app.route('/admin')
def admin():
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    return render_template('admin.html', table_names=table_names)

@app.route('/admin/create_table', methods=['POST'])
def create_table():
    table_name = request.form['table_name']
    db.session.execute(text(f'CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, question TEXT, answer TEXT)'))
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/edit_table/<table_name>')
def edit_table(table_name):
    questions = db.session.execute(text(f'SELECT * FROM {table_name}')).fetchall()
    return render_template('edit_table.html', table_name=table_name, questions=questions)

@app.route('/admin/add_question/<table_name>', methods=['POST'])
def add_question(table_name):
    question = request.form['question']
    answer = request.form['answer']
    db.session.execute(text(f'INSERT INTO {table_name} (question, answer) VALUES (:question, :answer)'), {'question': question, 'answer': answer})
    db.session.commit()
    return redirect(url_for('edit_table', table_name=table_name))

@app.route('/admin/delete_question/<table_name>/<int:question_id>', methods=['POST'])
def delete_question(table_name, question_id):
    db.session.execute(text(f'DELETE FROM {table_name} WHERE id = :id'), {'id': question_id})
    db.session.commit()
    return redirect(url_for('edit_table', table_name=table_name))


if __name__ == '__main__':
    app.run()