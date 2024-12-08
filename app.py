from flask import Flask, render_template, request, redirect, url_for
import json
import random

app = Flask(__name__)

with open('questions.json') as f:
    questions = json.load(f)

total_questions = len(questions)
correct_answers = 0

@app.route('/')
def index():
    if not questions:
        return render_template('index.html', question="No more questions!", correct_answers=correct_answers, total_questions=total_questions)
    question = random.choice(list(questions.keys()))
    return render_template('index.html', question=question, correct_answers=correct_answers, total_questions=total_questions)

@app.route('/answer', methods=['POST'])
def answer():
    global correct_answers
    question = request.form['question']
    answer = request.form['answer']
    if question in questions and questions[question] == answer:
        del questions[question]
        correct_answers += 1
    if not questions:
        return render_template('index.html', question="No more questions!", correct_answers=correct_answers, total_questions=total_questions)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()