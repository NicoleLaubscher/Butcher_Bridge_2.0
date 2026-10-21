from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db
from seed import seed_database


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        seed_database(reset=True)
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth(client):
    class AuthActions:
        def login(self, email="admin@butcherbridge.local", password="butcherbridge"):
            return client.post("/login", data={"email": email, "password": password}, follow_redirects=False)

        def logout(self):
            return client.post("/logout", follow_redirects=False)

    return AuthActions()

