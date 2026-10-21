"""Centralised API errors and JSON handlers."""

from flask import jsonify, request


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def register_error_handlers(app) -> None:
    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        return jsonify({"error": error.message, "details": error.details}), error.status_code

    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found."}), 404
        return error

    @app.errorhandler(500)
    def handle_server_error(error):
        app.logger.exception("Unhandled application error")
        if request.path.startswith("/api/"):
            return jsonify({"error": "An unexpected server error occurred."}), 500
        return error

