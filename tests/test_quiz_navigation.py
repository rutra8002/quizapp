import os
import tempfile
import unittest

from sqlalchemy import text

from app import create_app
from app.models import db


class QuizNavigationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls._quiz_db_file = tempfile.mkstemp(prefix="quizapp_quiz_nav_", suffix=".db")
        os.close(fd)
        fd, cls._users_db_file = tempfile.mkstemp(prefix="quizapp_quiz_nav_users_", suffix=".db")
        os.close(fd)

        cls.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{cls._quiz_db_file}",
                "SQLALCHEMY_BINDS": {"auth": f"sqlite:///{cls._users_db_file}"},
                "SECRET_KEY": "test-secret",
            }
        )

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
            db.engines["auth"].dispose()

        if os.path.exists(cls._quiz_db_file):
            os.remove(cls._quiz_db_file)
        if os.path.exists(cls._users_db_file):
            os.remove(cls._users_db_file)

    def setUp(self):
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            db.session.execute(
                text(
                    "CREATE TABLE first_quiz ("
                    "id INTEGER PRIMARY KEY, "
                    "question TEXT, "
                    "answer TEXT, "
                    "answer_lines INTEGER NOT NULL DEFAULT 1"
                    ")"
                )
            )
            db.session.execute(
                text(
                    "CREATE TABLE second_quiz ("
                    "id INTEGER PRIMARY KEY, "
                    "question TEXT, "
                    "answer TEXT, "
                    "answer_lines INTEGER NOT NULL DEFAULT 1"
                    ")"
                )
            )
            db.session.execute(
                text(
                    "INSERT INTO first_quiz (question, answer, answer_lines) "
                    "VALUES ('Question from first quiz', 'A1', 1)"
                )
            )
            db.session.execute(
                text(
                    "INSERT INTO second_quiz (question, answer, answer_lines) "
                    "VALUES ('Question from second quiz', 'B1', 1)"
                )
            )
            db.session.commit()

    def test_switching_quiz_table_loads_new_questions(self):
        first_response = self.client.get("/quiz/first_quiz")
        first_body = first_response.get_data(as_text=True)

        second_response = self.client.get("/quiz/second_quiz")
        second_body = second_response.get_data(as_text=True)

        self.assertEqual(first_response.status_code, 200)
        self.assertIn("Question from first quiz", first_body)

        self.assertEqual(second_response.status_code, 200)
        self.assertIn("Question from second quiz", second_body)
        self.assertNotIn("Question from first quiz", second_body)


if __name__ == "__main__":
    unittest.main(verbosity=2)

