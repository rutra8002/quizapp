from flask import Flask, render_template, request, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, Table, MetaData, Column, Integer, Text, select
import random
from google import genai
from dotenv import load_dotenv
import re
import os

db = SQLAlchemy()
load_dotenv()

class QuizApp(Flask):
    def __init__(self, import_name):
        super().__init__(import_name)
        self.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///questions.db'
        db.init_app(self)

        self.questions_list = []
        self.questions_loaded = False

        self.user_answers = []

        self.total_points = 0

        api_key = os.getenv("GEMINI_API_KEY")
        self.genai_client = genai.Client(api_key = api_key)
        self.model_name = "gemini-2.5-flash"

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

    def _is_valid_table_name(self, table_name: str) -> bool:
        # Restrict names to SQL identifier-like values to avoid abuse.
        return bool(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', table_name or ''))

    def _get_table(self, table_name: str) -> Table:
        if not self._is_valid_table_name(table_name):
            abort(400)
        inspector = inspect(db.engine)
        if table_name not in inspector.get_table_names():
            abort(404)
        return Table(table_name, MetaData(), autoload_with=db.engine)

    def index(self):
        self.questions_list = []
        self.questions_loaded = False
        self.user_answers = []
        self.total_points = 0
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        return render_template('index.html', table_names=table_names)

    def quiz(self, table_name):
        if not self.questions_loaded:
            table = self._get_table(table_name)
            self.questions_list = db.session.execute(select(table)).all()
            self.questions_loaded = True
        total_questions = len(self.questions_list)
        if total_questions == 0:
            return redirect(url_for('quiz_completed'))
        question = random.choice(self.questions_list)
        answer_lines = question.answer_lines
        return render_template('quiz.html', question=question.question, table_name=table_name, total_points=self.total_points, total_questions=total_questions, answer_lines=answer_lines)

    def answer(self):
        question_text = request.form['question']
        table_name = request.form['table_name']

        # Check if this is a multiline answer or single answer
        if 'answer_0' in request.form:
            # Combine multiple answer fields
            answers = []
            i = 0
            while f'answer_{i}' in request.form:
                answer = request.form[f'answer_{i}'].strip()
                if answer:
                    answers.append(answer)
                i += 1
            answer_text = '\n'.join(answers)
        else:
            answer_text = request.form['answer']

        question = next((q for q in self.questions_list if q.question == question_text), None)
        if question:
            # score with Gemini against the reference answer from DB
            ref_answer = question.answer
            score = self._score_with_gemini(question_text, ref_answer, answer_text)
            score = max(0, min(10, score))  # clamp safety
            score_label = f"{score}/10"

            # record and update totals
            self.user_answers.append({
                'question': question_text,
                'answer': answer_text,
                'expected': ref_answer,
                'score': score,
                'score_label': score_label
            })
            self.total_points += score


            # remove asked question
            self.questions_list.remove(question)

        if len(self.questions_list) == 0:
            return redirect(url_for('quiz_completed'))
        return redirect(url_for('quiz', table_name=table_name))

    def quiz_completed(self):
        total_attempts = len(self.user_answers)
        max_points = total_attempts * 10
        total_points = self.total_points

        return render_template(
            'quiz_completed.html',
            total_points=total_points,
            max_points=max_points,
            attempted_answers=self.user_answers,
        )

    ### admin things ###

    def admin(self):
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        return render_template('admin.html', table_names=table_names)

    def create_table(self):
        table_name = request.form['table_name']
        if not self._is_valid_table_name(table_name):
            abort(400)

        metadata = MetaData()
        quiz_table = Table(
            table_name,
            metadata,
            Column('id', Integer, primary_key=True),
            Column('question', Text),
            Column('answer', Text),
            Column('answer_lines', Integer, nullable=False, default=1),
        )
        metadata.create_all(db.engine, tables=[quiz_table], checkfirst=True)
        return redirect(url_for('admin'))

    def edit_table(self, table_name):
        table = self._get_table(table_name)
        questions = db.session.execute(select(table)).all()
        return render_template('edit_table.html', table_name=table_name, questions=questions)

    def add_question(self, table_name):
        question = request.form['question']
        answer = request.form['answer']
        answer_lines = int(request.form.get('answer_lines', 1))

        table = self._get_table(table_name)
        db.session.execute(
            table.insert().values(question=question, answer=answer, answer_lines=answer_lines)
        )
        db.session.commit()
        return redirect(url_for('edit_table', table_name=table_name))

    def edit_question(self, table_name, question_id):
        table = self._get_table(table_name)
        if request.method == 'POST':
            new_question = request.form['question']
            new_answer = request.form['answer']
            answer_lines = int(request.form.get('answer_lines', 1))

            db.session.execute(
                table.update()
                .where(table.c.id == question_id)
                .values(question=new_question, answer=new_answer, answer_lines=answer_lines)
            )
            db.session.commit()
            return redirect(url_for('edit_table', table_name=table_name))

        question = db.session.execute(
            select(table).where(table.c.id == question_id)
        ).first()
        return render_template('edit_question.html', table_name=table_name, question=question)

    def delete_question(self, table_name, question_id):
        table = self._get_table(table_name)
        db.session.execute(table.delete().where(table.c.id == question_id))
        db.session.commit()
        return redirect(url_for('edit_table', table_name=table_name))


    def _score_with_gemini(self, question_text: str, ref_answer: str, user_answer: str) -> int:
        """
        Ask Gemini to grade the user's answer 0-10.
        Returns an int in [0,10]. Falls back to exact match if no client configured.
        """
        # Fallback if API key not configured
        if not self.genai_client:
            return 10 if user_answer.strip().lower() == str(ref_answer).strip().lower() else 0

        prompt = (
            "You are a strict grader. Grade the user's answer to the question against the reference answer.\n"
            "- Return only a single integer from 0 to 10 inclusive.\n"
            "- 0 means completely incorrect, 10 means fully correct.\n"
            f"Question: {question_text}\n"
            f"Reference answer: {ref_answer}\n"
            f"User answer: {user_answer}\n"
            "Score (0-10):"
        )
        try:
            resp = self.genai_client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            raw = (resp.text or "").strip()
            # extract first integer in response
            m = re.search(r'(-?\d+)', raw)
            score = int(m.group(1)) if m else 0
        except Exception as e:
            print(e)
            score = 0
        return max(0, min(10, score))


app = QuizApp(__name__)

if __name__ == '__main__':
    app.run()