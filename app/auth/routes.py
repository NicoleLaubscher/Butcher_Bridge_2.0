"""Session authentication with role-aware demo users."""

from __future__ import annotations

import hmac

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

from ..db_models import User
from ..extensions import db


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        if current_app.config.get("CSRF_ENABLED", True) and not hmac.compare_digest(request.form.get("csrf_token", ""), session.get("csrf_token", "")):
            flash("Your form expired. Please try again.", "danger")
            return render_template("login.html"), 400
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none()
        if not user or not user.check_password(password) or not user.active:
            flash("Incorrect email or password.", "danger")
            return render_template("login.html"), 401
        login_user(user, remember=bool(request.form.get("remember")))
        return redirect(request.args.get("next") or url_for("main.dashboard"))
    return render_template("login.html")


@auth_bp.post("/logout")
def logout():
    if current_app.config.get("CSRF_ENABLED", True) and not hmac.compare_digest(request.form.get("csrf_token", ""), session.get("csrf_token", "")):
        flash("Your form expired. Please try again.", "danger")
        return redirect(url_for("main.dashboard"))
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))

