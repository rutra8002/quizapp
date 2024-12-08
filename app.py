from flask import Flask, render_template, request, redirect, url_for
import json
import random

app = Flask(__name__)

with open('questions.json') as f:
    questions = json.load(f)

@app.route('/')
def index():
    if not questions:
        return "No more questions!"
    question = random.choice(list(questions.keys()))
    return render_template('index.html', question=question)

@app.route('/answer', methods=['POST'])
def answer():
    question = request.form['question']
    answer = request.form['answer']
    print(questions)
    if question in questions and questions[question] == answer:
        del questions[question]
    if not questions:
        return "No more questions!"
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
