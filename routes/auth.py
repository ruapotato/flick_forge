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

"""Authentication routes for Flick Forge."""

import re
import hashlib
from functools import wraps
from flask import Blueprint, request, jsonify, session, current_app
from models import db, User, UserTier

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def get_anonymous_id():
    """Generate a consistent anonymous ID based on IP and user agent."""
    ip = request.remote_addr or "unknown"
    user_agent = request.user_agent.string or "unknown"
    raw = f"{ip}:{user_agent}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def get_current_user():
    """Get the currently logged in user, if any."""
    user_id = session.get("user_id")
    if user_id:
        return User.query.get(user_id)
    return None


def login_required(f):
    """Decorator to require authentication."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        user = User.query.get(session["user_id"])
        if not user or not user.is_active:
            session.pop("user_id", None)
            return jsonify({"error": "Invalid session"}), 401
        return f(*args, **kwargs)

    return decorated_function


def trusted_required(f):
    """Decorator to require trusted user tier or higher."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        user = User.query.get(session["user_id"])
        if not user or not user.is_active:
            session.pop("user_id", None)
            return jsonify({"error": "Invalid session"}), 401
        if not user.is_trusted():
            return jsonify({"error": "Trusted user status required"}), 403
        return f(*args, **kwargs)

    return decorated_function


def promoted_required(f):
    """Decorator to require promoted user tier or higher."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        user = User.query.get(session["user_id"])
        if not user or not user.is_active:
            session.pop("user_id", None)
            return jsonify({"error": "Invalid session"}), 401
        if not user.is_promoted():
            return jsonify({"error": "Promoted user status required"}), 403
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to require admin tier."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        user = User.query.get(session["user_id"])
        if not user or not user.is_active:
            session.pop("user_id", None)
            return jsonify({"error": "Invalid session"}), 401
        if not user.is_admin():
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated_function


def validate_email(email):
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_username(username):
    """Validate username format."""
    pattern = r"^[a-zA-Z0-9_-]{3,30}$"
    return re.match(pattern, username) is not None


def validate_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    return True, None


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # Validate inputs
    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required"}), 400

    if not validate_username(username):
        return (
            jsonify(
                {
                    "error": "Username must be 3-30 characters, containing only letters, numbers, underscores, and hyphens"
                }
            ),
            400,
        )

    if not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    valid, error = validate_password(password)
    if not valid:
        return jsonify({"error": error}), 400

    # Check for existing user
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # Create user
    user = User(username=username, email=email, tier=UserTier.TRUSTED.value)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Log in the user
    session["user_id"] = user.id
    session.permanent = True

    return (
        jsonify(
            {"message": "Registration successful", "user": user.to_dict(include_email=True)}
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    """Log in to an existing account."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    username_or_email = data.get("username", "").strip()
    password = data.get("password", "")

    if not username_or_email or not password:
        return jsonify({"error": "Username/email and password are required"}), 400

    # Find user by username or email
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email.lower())
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_active:
        return jsonify({"error": "Account is disabled"}), 403

    # Create session
    session["user_id"] = user.id
    session.permanent = True

    return jsonify({"message": "Login successful", "user": user.to_dict(include_email=True)})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Log out the current user."""
    session.pop("user_id", None)
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route("/me", methods=["GET"])
def get_profile():
    """Get the current user's profile."""
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False, "anonymous_id": get_anonymous_id()})

    return jsonify({"authenticated": True, "user": user.to_dict(include_email=True)})


@auth_bp.route("/me", methods=["PATCH"])
@login_required
def update_profile():
    """Update the current user's profile."""
    user = get_current_user()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Update email if provided
    new_email = data.get("email", "").strip().lower()
    if new_email and new_email != user.email:
        if not validate_email(new_email):
            return jsonify({"error": "Invalid email format"}), 400
        if User.query.filter_by(email=new_email).first():
            return jsonify({"error": "Email already in use"}), 409
        user.email = new_email

    # Update password if provided
    new_password = data.get("new_password", "")
    if new_password:
        current_password = data.get("current_password", "")
        if not user.check_password(current_password):
            return jsonify({"error": "Current password is incorrect"}), 401
        valid, error = validate_password(new_password)
        if not valid:
            return jsonify({"error": error}), 400
        user.set_password(new_password)

    db.session.commit()
    return jsonify({"message": "Profile updated", "user": user.to_dict(include_email=True)})


@auth_bp.route("/check-username", methods=["GET"])
def check_username():
    """Check if a username is available."""
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username required"}), 400

    if not validate_username(username):
        return jsonify({"available": False, "error": "Invalid username format"})

    exists = User.query.filter_by(username=username).first() is not None
    return jsonify({"available": not exists})


@auth_bp.route("/check-email", methods=["GET"])
def check_email():
    """Check if an email is already registered."""
    email = request.args.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    if not validate_email(email):
        return jsonify({"available": False, "error": "Invalid email format"})

    exists = User.query.filter_by(email=email).first() is not None
    return jsonify({"available": not exists})
