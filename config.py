"""Environment-specific configuration for ButcherBridge."""

from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ITEMS_PER_PAGE = 20
    CSRF_ENABLED = True


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{BASE_DIR / 'instance' / 'butcherbridge-demo.db'}"
        if os.getenv("USE_SQLITE_DEMO") == "1"
        else os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://butcherbridge:change-me@127.0.0.1:3306/butcherbridge",
        )
    )


class TestingConfig(BaseConfig):
    TESTING = True
    CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}

