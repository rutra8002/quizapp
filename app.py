from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
import random


db = SQLAlchemy()

class Question:
    def __init__(self, id, question, answer):
        self.id = id
        self.question = question
        self.answer = answer

class QuizApp(Flask):
    def __init__(self, import_name):
        super().__init__(import_name)
        self.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///questions.db'
        db.init_app(self)

        self.correct_answers = 0
        self.wrong_answers = 0
        self.questions_list = []
        self.questions_loaded = False

        self.user_answers = []

        # bind routes to bound instance methods
        self.add_url_rule('/', view_func=self.index)
        self.add_url_rule('/quiz/<table_name>', view_func=self.quiz)
        self.add_url_rule('/answer', view_func=self.answer, methods=['POST'])
        self.add_url_rule('/end_screen', view_func=self.quiz_completed)

        # admin routes
        self.add_url_rule('/admin', view_func=self.admin)
        self.add_url_rule('/admin/create_table', view_func=self.create_table, methods=['POST'])
        self.add_url_rule('/admin/edit_table/<table_name>', view_func=self.edit_table)
        self.add_url_rule('/admin/add_question/<table_name>', view_func=self.add_question, methods=['POST'])
        self.add_url_rule('/admin/edit_question/<table_name>/<int:question_id>', view_func=self.edit_question, methods=['GET', 'POST'])
        self.add_url_rule('/admin/delete_question/<table_name>/<int:question_id>', view_func=self.delete_question, methods=['POST'])


    def index(self):
        self.questions_list = []
        self.questions_loaded = False
        self.correct_answers = 0
        self.wrong_answers = 0
        self.user_answers = []
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        return render_template('index.html', table_names=table_names)

    def quiz(self, table_name):
        if not self.questions_loaded:
            self.questions_list = db.session.execute(text(f'SELECT * FROM {table_name}')).fetchall()
            self.questions_loaded = True
        total_questions = len(self.questions_list)
        if total_questions == 0:
            return redirect(url_for('quiz_completed'))
        question = random.choice(self.questions_list)
        return render_template('quiz.html', question=question.question, table_name=table_name, correct_answers=self.correct_answers, total_questions=total_questions)

    def answer(self):
        question_text = request.form['question']
        answer_text = request.form['answer']
        table_name = request.form['table_name']
        question = next((q for q in self.questions_list if q.question == question_text), None)
        if question:
            self.user_answers.append({'question': question_text, 'answer': answer_text})
            if question.answer == answer_text:
                self.correct_answers += 1
            else:
                self.wrong_answers += 1
            self.questions_list.remove(question)

        if len(self.questions_list) == 0:
            return redirect(url_for('quiz_completed'))
        return redirect(url_for('quiz', table_name=table_name))

    def quiz_completed(self):
        total_attempts = self.correct_answers + self.wrong_answers
        correct_percentage = round((self.correct_answers / total_attempts) * 100, 2) if total_attempts > 0 else 0
        wrong_percentage = (self.wrong_answers / total_attempts) * 100 if total_attempts > 0 else 0
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        all_questions = []
        for table_name in table_names:
            questions = db.session.execute(text(f'SELECT * FROM {table_name}')).fetchall()
            for q in questions:
                all_questions.append(Question(q.id, q.question, q.answer))

        # Sort user_answers based on the order of all_questions
        sorted_user_answers = [next(ua['answer'] for ua in self.user_answers if ua['question'] == q.question) for q in all_questions]

        return render_template('quiz_completed.html', correct_percentage=correct_percentage,
                               wrong_percentage=wrong_percentage, all_questions=all_questions,
                               user_answers=sorted_user_answers, zip=zip)

    ### admin things ###

    def admin(self):
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        return render_template('admin.html', table_names=table_names)

    def create_table(self):
        table_name = request.form['table_name']
        db.session.execute(text(f'CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, question TEXT, answer TEXT)'))
        db.session.commit()
        return redirect(url_for('admin'))

    def edit_table(self, table_name):
        questions = db.session.execute(text(f'SELECT * FROM {table_name}')).fetchall()
        return render_template('edit_table.html', table_name=table_name, questions=questions)

    def add_question(self, table_name):
        question = request.form['question']
        answer = request.form['answer']
        db.session.execute(text(f'INSERT INTO {table_name} (question, answer) VALUES (:question, :answer)'), {'question': question, 'answer': answer})
        db.session.commit()
        return redirect(url_for('edit_table', table_name=table_name))

    def edit_question(self, table_name, question_id):
        if request.method == 'POST':
            new_question = request.form['question']
            new_answer = request.form['answer']
            db.session.execute(text(f'UPDATE {table_name} SET question = :question, answer = :answer WHERE id = :id'), {'question': new_question, 'answer': new_answer, 'id': question_id})
            db.session.commit()
            return redirect(url_for('edit_table', table_name=table_name))
        question = db.session.execute(text(f'SELECT * FROM {table_name} WHERE id = :id'), {'id': question_id}).fetchone()
        return render_template('edit_question.html', table_name=table_name, question=question)

    def delete_question(self, table_name, question_id):
        db.session.execute(text(f'DELETE FROM {table_name} WHERE id = :id'), {'id': question_id})
        db.session.commit()
        return redirect(url_for('edit_table', table_name=table_name))


app = QuizApp(__name__)

if __name__ == '__main__':
    app.run()