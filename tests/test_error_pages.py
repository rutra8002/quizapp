import os
import shutil
import tempfile
import unittest

from app import create_app
from app.models import db


class ErrorPagesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls._quiz_db_file = tempfile.mkstemp(prefix="quizapp_error_quiz_", suffix=".db")
        os.close(fd)
        fd, cls._users_db_file = tempfile.mkstemp(prefix="quizapp_error_users_", suffix=".db")
        os.close(fd)
        cls._user_quiz_db_dir = tempfile.mkdtemp(prefix="quizapp_error_user_quiz_")

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

    def setUp(self):
        self.client = self.app.test_client()

    def test_404_uses_custom_template(self):
        response = self.client.get("/missing-page")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 404)
        self.assertIn("<title>404 - Not Found</title>", body)
        self.assertIn("Not Found", body)
        self.assertIn("404", body)

    def test_405_uses_custom_template(self):
        response = self.client.get("/logout")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 405)
        self.assertIn("<title>405 - Method Not Allowed</title>", body)
        self.assertIn("Method Not Allowed", body)
        self.assertIn("405", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)

