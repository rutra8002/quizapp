from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///questions.db'
db = SQLAlchemy(app)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()

correct_answers = 0

@app.route('/')
def index():
    total_questions = Question.query.count()
    if total_questions == 0:
        return render_template('index.html', question="No more questions!", correct_answers=correct_answers, total_questions=total_questions)
    question = random.choice(Question.query.all())
    return render_template('index.html', question=question.question, correct_answers=correct_answers, total_questions=total_questions)

@app.route('/answer', methods=['POST'])
def answer():
    global correct_answers
    question_text = request.form['question']
    answer_text = request.form['answer']
    question = Question.query.filter_by(question=question_text).first()
    if question and question.answer == answer_text:
        db.session.delete(question)
        db.session.commit()
        correct_answers += 1
    if Question.query.count() == 0:
        return render_template('index.html', question="No more questions!", correct_answers=correct_answers, total_questions=Question.query.count())
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()