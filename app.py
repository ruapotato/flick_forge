# Flick Forge - Flick Store Backend
# Copyright (C) 2025 Flick Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Flick Forge - The Flick Store Backend

A Flask-based backend for the Flick app store, supporting:
- Multi-tier user system (anonymous, trusted, promoted, admin)
- App repository with package management
- AI-generated app requests and prompts
- Community reviews and ratings
- Wild West testing area for new apps
- Feedback and rebuild system

Run with: python app.py
Or with gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 app:app
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import get_config
from models import db, init_db


def create_app(config_name=None):
    """Application factory for creating the Flask app."""
    app = Flask(__name__)

    # Load configuration
    if config_name:
        from config import config
        app.config.from_object(config[config_name])
    else:
        app.config.from_object(get_config())

    # Ensure directories exist
    os.makedirs(app.config.get("UPLOAD_FOLDER", "static/packages"), exist_ok=True)
    os.makedirs(app.config.get("SCREENSHOTS_FOLDER", "static/screenshots"), exist_ok=True)

    # Initialize extensions
    init_db(app)

    # Configure CORS
    CORS(
        app,
        origins=app.config.get("CORS_ORIGINS", ["*"]),
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    # Configure rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[app.config.get("RATELIMIT_DEFAULT", "100 per minute")],
        storage_uri=app.config.get("RATELIMIT_STORAGE_URL", "memory://"),
    )

    # Configure logging
    if not app.debug:
        if not os.path.exists("logs"):
            os.mkdir("logs")
        file_handler = RotatingFileHandler(
            "logs/flick_forge.log", maxBytes=10240000, backupCount=10
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("Flick Forge startup")

    # Register blueprints
    from routes import auth_bp, apps_bp, reviews_bp, requests_bp, feedback_bp, admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(apps_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(admin_bp)

    # Apply rate limits to specific endpoints
    # Note: auth/me is called on every page load, so needs higher limit
    limiter.limit("120 per minute")(auth_bp)
    limiter.limit("60 per minute")(reviews_bp)
    limiter.limit("60 per minute")(requests_bp)
    limiter.limit("60 per minute")(feedback_bp)

    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "message": str(error)}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Forbidden", "message": "Access denied"}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found", "message": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(409)
    def conflict(error):
        return jsonify({"error": "Conflict", "message": str(error)}), 409

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return (
            jsonify(
                {
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please slow down.",
                }
            ),
            429,
        )

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"Internal error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    # Web page routes
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/browse")
    def browse():
        return render_template("browse.html")

    @app.route("/app/<slug>")
    def app_page(slug):
        return render_template("app.html", slug=slug)

    @app.route("/wildwest")
    def wildwest():
        return render_template("wildwest.html")

    @app.route("/request")
    def request_page():
        return render_template("request.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/register")
    def register_page():
        return render_template("register.html")

    @app.route("/profile")
    def profile_page():
        return render_template("profile.html")

    @app.route("/admin")
    def admin_page():
        return render_template("admin.html")

    # API info endpoint
    @app.route("/api")
    def api_info():
        return jsonify(
            {
                "name": "Flick Forge",
                "version": "1.0.0",
                "description": "Flick Store Backend API",
                "documentation": "/api/docs",
                "endpoints": {
                    "auth": "/api/auth",
                    "apps": "/api/apps",
                    "reviews": "/api/reviews",
                    "requests": "/api/requests",
                    "feedback": "/api/feedback",
                    "admin": "/api/admin",
                },
            }
        )

    # API documentation endpoint
    @app.route("/api/docs")
    def api_docs():
        return jsonify(
            {
                "title": "Flick Forge API Documentation",
                "version": "1.0.0",
                "base_url": request.host_url.rstrip("/"),
                "authentication": {
                    "type": "session",
                    "description": "Session-based authentication. Use /api/auth/login to authenticate.",
                },
                "user_tiers": {
                    "anonymous": "No login required. Can browse, download, review, upvote.",
                    "trusted": "Registered users. Can submit app requests/prompts.",
                    "promoted": "Can approve requests, manage feedback, promote apps.",
                    "admin": "Full access. Can manage users and system.",
                },
                "endpoints": {
                    "auth": {
                        "POST /api/auth/register": "Register new account",
                        "POST /api/auth/login": "Login",
                        "POST /api/auth/logout": "Logout",
                        "GET /api/auth/me": "Get current user profile",
                        "PATCH /api/auth/me": "Update profile",
                    },
                    "apps": {
                        "GET /api/apps": "List apps (with filters)",
                        "GET /api/apps/search": "Search apps",
                        "GET /api/apps/categories": "List categories",
                        "GET /api/apps/wild-west": "List Wild West apps",
                        "GET /api/apps/featured": "Get featured apps",
                        "GET /api/apps/<slug>": "Get app details",
                        "GET /api/apps/<slug>/download": "Download app",
                        "POST /api/apps": "Create app (promoted+)",
                        "PATCH /api/apps/<slug>": "Update app",
                        "DELETE /api/apps/<slug>": "Delete app (admin)",
                    },
                    "reviews": {
                        "GET /api/reviews/app/<slug>": "List reviews for app",
                        "POST /api/reviews/app/<slug>": "Create review",
                        "PATCH /api/reviews/<id>": "Update review",
                        "DELETE /api/reviews/<id>": "Delete review",
                        "POST /api/reviews/<id>/vote": "Upvote review",
                        "DELETE /api/reviews/<id>/vote": "Remove upvote",
                    },
                    "requests": {
                        "GET /api/requests": "List app requests",
                        "POST /api/requests": "Create request (trusted+)",
                        "GET /api/requests/<id>": "Get request details",
                        "POST /api/requests/<id>/upvote": "Upvote request",
                        "POST /api/requests/<id>/approve": "Approve request (promoted+)",
                        "POST /api/requests/<id>/reject": "Reject request (promoted+)",
                    },
                    "feedback": {
                        "GET /api/feedback/app/<slug>": "List feedback for app",
                        "POST /api/feedback/app/<slug>": "Create feedback",
                        "POST /api/feedback/<id>/approve-rebuild": "Approve rebuild (promoted+)",
                    },
                    "admin": {
                        "GET /api/admin/users": "List users",
                        "POST /api/admin/users/<id>/promote": "Promote user",
                        "GET /api/admin/stats": "Get system stats",
                        "POST /api/admin/apps/<slug>/approve-to-stable": "Promote app to stable",
                    },
                },
            }
        )

    # Static file serving for packages and screenshots
    @app.route("/static/packages/<path:filename>")
    def serve_package(filename):
        from flask import send_from_directory

        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/static/screenshots/<path:filename>")
    def serve_screenshot(filename):
        from flask import send_from_directory

        return send_from_directory(app.config["SCREENSHOTS_FOLDER"], filename)

    return app


# Create the application instance
app = create_app()


def init_admin():
    """Initialize the first admin user if none exists."""
    from models import User, UserTier

    with app.app_context():
        admin = User.query.filter_by(tier=UserTier.ADMIN.value).first()
        if not admin:
            # Create default admin (should be changed in production)
            admin_username = os.environ.get("ADMIN_USERNAME", "admin")
            admin_email = os.environ.get("ADMIN_EMAIL", "admin@255.one")
            admin_password = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")

            admin = User(
                username=admin_username,
                email=admin_email,
                tier=UserTier.ADMIN.value,
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"Created admin user: {admin_username}")
            print("IMPORTANT: Change the admin password in production!")


if __name__ == "__main__":
    # Initialize admin user
    init_admin()

    # Run the development server
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

    print(f"\n{'=' * 60}")
    print("Flick Forge - Flick Store Backend")
    print(f"{'=' * 60}")
    print(f"Running on http://0.0.0.0:{port}")
    print(f"Debug mode: {debug}")
    print(f"{'=' * 60}\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
