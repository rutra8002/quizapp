import os
import tempfile
import unittest

from sqlalchemy import inspect

from app import create_app
from app.models import db


class AdminAccessTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls._quiz_db_file = tempfile.mkstemp(prefix="quizapp_admin_quiz_", suffix=".db")
        os.close(fd)
        fd, cls._users_db_file = tempfile.mkstemp(prefix="quizapp_admin_users_", suffix=".db")
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

    def _register(self, username="editor", password="secret123"):
        return self.client.post(
            "/register",
            data={
                "username": username,
                "password": password,
                "confirm_password": password,
            },
            follow_redirects=False,
        )

    def test_admin_page_requires_login(self):
        response = self.client.get("/admin", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))

    def test_logged_in_user_can_create_quiz_table(self):
        self._register()

        response = self.client.post(
            "/admin/create_table",
            data={"table_name": "public_quiz"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/admin"))

        with self.app.app_context():
            table_names = inspect(db.engine).get_table_names()
            self.assertIn("public_quiz", table_names)


if __name__ == "__main__":
    unittest.main(verbosity=2)

