import os
import shutil
import tempfile
import unittest

from app import create_app
from app.models import User, db


class AuthRoutesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls._quiz_db_file = tempfile.mkstemp(prefix="quizapp_auth_quiz_", suffix=".db")
        os.close(fd)
        fd, cls._users_db_file = tempfile.mkstemp(prefix="quizapp_auth_users_", suffix=".db")
        os.close(fd)
        cls._user_quiz_db_dir = tempfile.mkdtemp(prefix="quizapp_auth_user_quiz_")

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

        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def _register(self, username="jeff", password="secret123", follow_redirects=True):
        return self.client.post(
            "/register",
            data={
                "username": username,
                "password": password,
                "confirm_password": password,
            },
            follow_redirects=follow_redirects,
        )

    def _login(self, username="jeff", password="secret123", follow_redirects=True):
        return self.client.post(
            "/login",
            data={
                "username": username,
                "password": password,
            },
            follow_redirects=follow_redirects,
        )

    def test_register_success_creates_user_and_logs_in(self):
        response = self._register()
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("jeff", body)
        self.assertIn("Log out", body)

        with self.app.app_context():
            user = User.query.filter_by(username="jeff").first()
            self.assertIsNotNone(user)
            self.assertTrue(user.check_password("secret123"))

    def test_register_duplicate_username_returns_409(self):
        self._register(follow_redirects=False)
        self.client.post("/logout", follow_redirects=False)
        response = self._register(follow_redirects=False)

        self.assertEqual(response.status_code, 409)
        self.assertIn("Username is already taken.", response.get_data(as_text=True))

    def test_login_success(self):
        self._register(follow_redirects=False)
        self.client.post("/logout", follow_redirects=False)

        response = self._login(follow_redirects=True)
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("jeff", body)
        self.assertIn("Log out", body)

    def test_login_invalid_credentials_returns_401(self):
        self._register(follow_redirects=False)
        self.client.post("/logout", follow_redirects=False)

        response = self._login(password="wrongpass", follow_redirects=False)

        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid username or password.", response.get_data(as_text=True))

    def test_logout_clears_user_from_header(self):
        self._register(follow_redirects=False)

        response = self.client.post("/logout", follow_redirects=True)
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Login", body)
        self.assertNotIn("jeff", body)

    def test_login_page_redirects_if_already_authenticated(self):
        self._register(follow_redirects=False)

        response = self.client.get("/login", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/"))

    def test_register_page_redirects_if_already_authenticated(self):
        self._register(follow_redirects=False)

        response = self.client.get("/register", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

