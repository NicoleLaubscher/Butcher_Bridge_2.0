"""Jinja-rendered application pages."""

from flask import Blueprint, current_app, render_template, send_from_directory
from flask_login import login_required

from ..db_models import Scenario
from ..extensions import db


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
@login_required
def dashboard():
    scenarios = db.session.execute(db.select(Scenario).order_by(Scenario.id)).scalars().all()
    return render_template("dashboard.html", scenarios=scenarios)


@main_bp.get("/methodology")
@login_required
def methodology():
    return render_template("methodology.html")


@main_bp.get("/api-contract")
@login_required
def api_contract():
    return send_from_directory(current_app.root_path + "/../docs", "openapi.json")


@main_bp.get("/health")
def health():
    return {"status": "ok", "service": "ButcherBridge"}

