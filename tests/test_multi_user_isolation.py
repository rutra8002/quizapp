import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.models import db


class MultiUserIsolationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls._quiz_db_file = tempfile.mkstemp(prefix="quizapp_multi_user_quiz_", suffix=".db")
        os.close(fd)
        fd, cls._users_db_file = tempfile.mkstemp(prefix="quizapp_multi_user_users_", suffix=".db")
        os.close(fd)
        cls._user_quiz_db_dir = tempfile.mkdtemp(prefix="quizapp_multi_user_user_quiz_")

        cls.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{cls._quiz_db_file}",
                "SQLALCHEMY_BINDS": {"auth": f"sqlite:///{cls._users_db_file}"},
                "USER_QUIZ_DB_DIR": cls._user_quiz_db_dir,
                "SECRET_KEY": "test-secret",
            }
        )

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_user_quiz_dbs(cls.app)
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
            db.engines["auth"].dispose()

        if os.path.exists(cls._quiz_db_file):
            os.remove(cls._quiz_db_file)
        if os.path.exists(cls._users_db_file):
            os.remove(cls._users_db_file)
        shutil.rmtree(cls._user_quiz_db_dir, ignore_errors=True)

    @staticmethod
    def _cleanup_user_quiz_dbs(app):
        user_quiz_path = Path(app.config.get("USER_QUIZ_DB_DIR", app.instance_path))
        if not user_quiz_path.exists():
            return

        for file_path in user_quiz_path.glob("quiz_user_*.db"):
            try:
                file_path.unlink()
            except OSError:
                pass

    @staticmethod
    def _extract_question_id(html: str) -> int:
        match = re.search(r'name="question_id"\s+value="(\d+)"', html)
        if not match:
            raise AssertionError("question_id hidden input not found in quiz page")
        return int(match.group(1))

    def setUp(self):
        self._cleanup_user_quiz_dbs(self.app)

        with self.app.app_context():
            db.drop_all()
            db.create_all()

        self.client_jeff = self.app.test_client()
        self.client_bob = self.app.test_client()

    def _register(self, client, username):
        return client.post(
            "/register",
            data={"username": username, "password": "secret123", "confirm_password": "secret123"},
            follow_redirects=False,
        )

    def test_two_users_have_isolated_quiz_data_and_state(self):
        self._register(self.client_jeff, "jeff")
        self._register(self.client_bob, "bob")

        self.client_jeff.post("/admin/create_table", data={"table_name": "daily_quiz"}, follow_redirects=False)
        self.client_bob.post("/admin/create_table", data={"table_name": "daily_quiz"}, follow_redirects=False)

        self.client_jeff.post(
            "/admin/add_question/daily_quiz",
            data={"question": "Jeff question", "answer": "A1", "answer_lines": "1"},
            follow_redirects=False,
        )
        self.client_bob.post(
            "/admin/add_question/daily_quiz",
            data={"question": "Bob question", "answer": "B1", "answer_lines": "1"},
            follow_redirects=False,
        )

        jeff_quiz_response = self.client_jeff.get("/quiz/daily_quiz")
        bob_quiz_response = self.client_bob.get("/quiz/daily_quiz")
        jeff_body = jeff_quiz_response.get_data(as_text=True)
        bob_body = bob_quiz_response.get_data(as_text=True)

        self.assertEqual(jeff_quiz_response.status_code, 200)
        self.assertIn("Jeff question", jeff_body)
        self.assertNotIn("Bob question", jeff_body)

        self.assertEqual(bob_quiz_response.status_code, 200)
        self.assertIn("Bob question", bob_body)
        self.assertNotIn("Jeff question", bob_body)

        jeff_question_id = self._extract_question_id(jeff_body)
        bob_question_id = self._extract_question_id(bob_body)

        jeff_finish = self.client_jeff.post(
            "/answer",
            data={"table_name": "daily_quiz", "question_id": str(jeff_question_id), "answer": "A1"},
            follow_redirects=True,
        )
        jeff_finish_body = jeff_finish.get_data(as_text=True)
        self.assertEqual(jeff_finish.status_code, 200)
        self.assertIn("Quiz completed", jeff_finish_body)
        self.assertIn("10", jeff_finish_body)

        bob_still_active = self.client_bob.get("/quiz/daily_quiz")
        bob_still_active_body = bob_still_active.get_data(as_text=True)
        self.assertEqual(bob_still_active.status_code, 200)
        self.assertIn("Bob question", bob_still_active_body)

        bob_finish = self.client_bob.post(
            "/answer",
            data={"table_name": "daily_quiz", "question_id": str(bob_question_id), "answer": "B1"},
            follow_redirects=True,
        )
        bob_finish_body = bob_finish.get_data(as_text=True)
        self.assertEqual(bob_finish.status_code, 200)
        self.assertIn("Quiz completed", bob_finish_body)
        self.assertIn("10", bob_finish_body)


if __name__ == "__main__":
    unittest.main(verbosity=2)

