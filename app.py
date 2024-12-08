from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///questions.db'
db = SQLAlchemy(app)

class Question(db.Model):
    __tablename__ = 'geography'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()

correct_answers = 0
wrong_answers = 0
questions_list = []
questions_loaded = False

@app.before_request
def load_questions():
    global questions_list, questions_loaded
    if not questions_loaded:
        questions_list = Question.query.all()
        questions_loaded = True

@app.route('/')
def index():
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
    global correct_answers, wrong_answers, questions_list
    question_text = request.form['question']
    answer_text = request.form['answer']
    table_name = request.form['table_name']
    question = next((q for q in questions_list if q.question == question_text), None)
    if question:
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
    return render_template('quiz_completed.html', correct_percentage=correct_percentage, wrong_percentage=wrong_percentage)

if __name__ == '__main__':
    app.run()