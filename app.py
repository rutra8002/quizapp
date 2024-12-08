from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
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

@app.route('/')
def index():
    total_questions = Question.query.count()
    if total_questions == 0:
        return redirect(url_for('end_screen'))
    question = random.choice(Question.query.all())
    return render_template('index.html', question=question.question, correct_answers=correct_answers, total_questions=total_questions)

@app.route('/answer', methods=['POST'])
def answer():
    global correct_answers, wrong_answers
    question_text = request.form['question']
    answer_text = request.form['answer']
    question = Question.query.filter_by(question=question_text).first()
    if question:
        if question.answer == answer_text:
            correct_answers += 1
        else:
            wrong_answers += 1
        db.session.delete(question)
        db.session.commit()

    if Question.query.count() == 0:
        return redirect(url_for('end_screen'))
    return redirect(url_for('index'))

@app.route('/end_screen')
def end_screen():
    total_attempts = correct_answers + wrong_answers
    correct_percentage = (correct_answers / total_attempts) * 100 if total_attempts > 0 else 0
    wrong_percentage = (wrong_answers / total_attempts) * 100 if total_attempts > 0 else 0
    return render_template('end_screen.html', correct_percentage=correct_percentage, wrong_percentage=wrong_percentage)

if __name__ == '__main__':
    app.run()