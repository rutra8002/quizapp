from flask import flash, g, redirect, render_template, request, session, url_for

from ..models import User, db


def _normalize_username(value: str) -> str:
    return (value or "").strip()


def _get_session_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login():
    if g.current_user:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = _normalize_username(request.form.get("username"))
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("login.html", username=username), 400

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return render_template("login.html", username=username), 401

        session.pop("quiz_state", None)
        session["user_id"] = user.id
        flash("Logged in successfully.", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


def register():
    if g.current_user:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = _normalize_username(request.form.get("username"))
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("register.html", username=username), 400

        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
            return render_template("register.html", username=username), 400

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html", username=username), 400

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html", username=username), 400

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username is already taken.", "error")
            return render_template("register.html", username=username), 409

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session.pop("quiz_state", None)
        session["user_id"] = user.id
        flash("Registration successful.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


def logout():
    session.pop("user_id", None)
    session.pop("quiz_state", None)
    flash("Logged out.", "success")
    return redirect(url_for("index"))


def register_auth_routes(app):
    @app.before_request
    def load_current_user():
        g.current_user = _get_session_user()

    @app.context_processor
    def inject_auth_user():
        return {"current_user": g.get("current_user")}

    app.add_url_rule("/login", view_func=login, methods=["GET", "POST"])
    app.add_url_rule("/register", view_func=register, methods=["GET", "POST"])
    app.add_url_rule("/logout", view_func=logout, methods=["POST"])

