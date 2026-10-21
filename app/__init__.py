"""Flask application factory."""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, session

load_dotenv()

from config import CONFIGS
from .extensions import db, login_manager, migrate
from .errors import register_error_handlers


def create_app(config_name: str | None = None) -> Flask:
    load_dotenv()
    selected = config_name or os.getenv("FLASK_ENV", "development")
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(CONFIGS.get(selected, CONFIGS["development"]))
    if selected == "production" and not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is required in production.")

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .db_models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    @app.before_request
    def protect_json_mutations():
        if (
            app.config.get("CSRF_ENABLED", True)
            and request.path.startswith("/api/")
            and request.method in {"POST", "PUT", "PATCH", "DELETE"}
        ):
            supplied = request.headers.get("X-CSRF-Token")
            if not supplied or supplied != session.get("csrf_token"):
                return jsonify({"error": "Invalid or missing CSRF token."}), 400

    @app.context_processor
    def inject_csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(24)
        return {"csrf_token": session["csrf_token"]}

    from .auth.routes import auth_bp
    from .main.routes import main_bp
    from .api.routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    register_error_handlers(app)

    logging.basicConfig(
        level=getattr(logging, str(app.config.get("LOG_LEVEL", "INFO")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return app

