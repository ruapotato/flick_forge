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

"""Configuration settings for Flick Forge."""

import os
from datetime import timedelta


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///flick_forge.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # CORS
    CORS_ORIGINS = [
        "https://255.one",
        "https://www.255.one",
        "https://store.255.one",
    ]

    # Rate Limiting
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"

    # File Upload
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB max upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "packages")
    SCREENSHOTS_FOLDER = os.path.join(os.path.dirname(__file__), "static", "screenshots")
    ALLOWED_EXTENSIONS = {"flick"}

    # App Categories
    CATEGORIES = [
        "productivity",
        "utilities",
        "games",
        "entertainment",
        "social",
        "education",
        "development",
        "graphics",
        "audio",
        "video",
        "communication",
        "system",
        "other",
    ]

    # User Tiers
    USER_TIERS = {
        "anonymous": 0,
        "limited": 1,
        "promoted": 2,
        "admin": 3,
    }

    # AI Safety Check (stub endpoint for Claude Code integration)
    AI_SAFETY_ENDPOINT = os.environ.get("AI_SAFETY_ENDPOINT", None)
    AI_SAFETY_ENABLED = os.environ.get("AI_SAFETY_ENABLED", "false").lower() == "true"

    # Claude Code Build Integration (stub)
    CLAUDE_CODE_ENDPOINT = os.environ.get("CLAUDE_CODE_ENDPOINT", None)
    CLAUDE_CODE_ENABLED = os.environ.get("CLAUDE_CODE_ENABLED", "false").lower() == "true"


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SESSION_COOKIE_SECURE = False
    CORS_ORIGINS = ["*"]  # Allow all origins in development


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    # In production, ensure SECRET_KEY is set via environment variable
    # SESSION_COOKIE_SECURE should remain True for HTTPS


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """Get configuration based on environment."""
    env = os.environ.get("FLASK_ENV", "development")
    return config.get(env, config["default"])
