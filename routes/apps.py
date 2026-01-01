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

"""App repository routes for Flick Forge."""

import os
import re
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from models import db, App, AppStatus, Screenshot, AppDownload
from routes.auth import (
    get_current_user,
    get_anonymous_id,
    login_required,
    promoted_required,
    admin_required,
)

apps_bp = Blueprint("apps", __name__, url_prefix="/api/apps")


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:100]


def allowed_file(filename):
    """Check if file extension is allowed."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config.get("ALLOWED_EXTENSIONS", {"flick"})
    )


@apps_bp.route("", methods=["GET"])
def list_apps():
    """List all apps with pagination and filtering."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    category = request.args.get("category")
    status = request.args.get("status", "stable")  # Default to stable apps
    sort_by = request.args.get("sort", "created_at")  # created_at, downloads, rating, name
    order = request.args.get("order", "desc")  # asc or desc

    # Build query
    query = App.query

    # Filter by status
    if status == "all":
        # Only admins can see all statuses
        user = get_current_user()
        if not user or not user.is_admin():
            query = query.filter(
                App.status.in_([AppStatus.STABLE.value, AppStatus.WILD_WEST.value])
            )
    elif status == "wild_west":
        query = query.filter(App.status == AppStatus.WILD_WEST.value)
    else:
        query = query.filter(App.status == AppStatus.STABLE.value)

    # Filter by category
    if category:
        query = query.filter(App.category == category)

    # Sorting
    if sort_by == "downloads":
        order_col = App.download_count
    elif sort_by == "name":
        order_col = App.name
    elif sort_by == "updated":
        order_col = App.updated_at
    else:
        order_col = App.created_at

    if order == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "apps": [app.to_dict() for app in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
            "per_page": per_page,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
    )


@apps_bp.route("/search", methods=["GET"])
def search_apps():
    """Full-text search of apps."""
    query_text = request.args.get("q", "").strip()
    if not query_text:
        return jsonify({"error": "Search query required"}), 400

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status = request.args.get("status", "stable")

    # Build search query
    search_pattern = f"%{query_text}%"
    query = App.query.filter(
        or_(
            App.name.ilike(search_pattern),
            App.description.ilike(search_pattern),
            App.slug.ilike(search_pattern),
        )
    )

    # Filter by status
    if status == "all":
        user = get_current_user()
        if not user or not user.is_admin():
            query = query.filter(
                App.status.in_([AppStatus.STABLE.value, AppStatus.WILD_WEST.value])
            )
    elif status == "wild_west":
        query = query.filter(App.status == AppStatus.WILD_WEST.value)
    else:
        query = query.filter(App.status == AppStatus.STABLE.value)

    # Order by relevance (name matches first, then description)
    query = query.order_by(
        App.name.ilike(search_pattern).desc(), App.download_count.desc()
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "query": query_text,
            "apps": [app.to_dict() for app in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@apps_bp.route("/categories", methods=["GET"])
def list_categories():
    """List all app categories with counts (dynamic from database)."""
    # Get distinct categories from apps that are visible (stable or wild_west)
    from sqlalchemy import func

    results = db.session.query(
        App.category,
        func.count(App.id).label('count')
    ).filter(
        App.status.in_([AppStatus.STABLE.value, AppStatus.WILD_WEST.value]),
        App.category.isnot(None),
        App.category != ''
    ).group_by(App.category).order_by(func.count(App.id).desc()).all()

    return jsonify(
        {
            "categories": [
                {"name": cat, "count": count} for cat, count in results
            ]
        }
    )


@apps_bp.route("/category/<category>", methods=["GET"])
def get_apps_by_category(category):
    """Get apps in a specific category."""
    # Category is now free-form, just filter by whatever category string is provided
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status = request.args.get("status", "stable")

    query = App.query.filter(App.category == category)

    if status == "wild_west":
        query = query.filter(App.status == AppStatus.WILD_WEST.value)
    else:
        query = query.filter(App.status == AppStatus.STABLE.value)

    query = query.order_by(App.download_count.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "category": category,
            "apps": [app.to_dict() for app in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@apps_bp.route("/wild-west", methods=["GET"])
def get_wild_west_apps():
    """Get apps in the Wild West testing area."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = App.query.filter(App.status == AppStatus.WILD_WEST.value)
    query = query.order_by(App.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "apps": [app.to_dict() for app in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@apps_bp.route("/<slug>", methods=["GET"])
def get_app(slug):
    """Get detailed information about a specific app."""
    app = App.query.filter_by(slug=slug).first()
    if not app:
        return jsonify({"error": "App not found"}), 404

    # Check if app is accessible
    if app.status not in [AppStatus.STABLE.value, AppStatus.WILD_WEST.value]:
        user = get_current_user()
        if not user or not user.is_admin():
            return jsonify({"error": "App not found"}), 404

    return jsonify({"app": app.to_dict()})


@apps_bp.route("/<slug>/download", methods=["GET"])
def download_app(slug):
    """Download an app package."""
    app = App.query.filter_by(slug=slug).first()
    if not app:
        return jsonify({"error": "App not found"}), 404

    # Check if app is downloadable
    if app.status not in [AppStatus.STABLE.value, AppStatus.WILD_WEST.value]:
        user = get_current_user()
        if not user or not user.is_admin():
            return jsonify({"error": "App not available for download"}), 403

    if not app.package_path or not os.path.exists(app.package_path):
        return jsonify({"error": "Package file not found"}), 404

    # Record download
    user = get_current_user()
    download = AppDownload(
        app_id=app.id,
        user_id=user.id if user else None,
        anonymous_id=get_anonymous_id() if not user else None,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:500] if request.user_agent.string else None,
    )
    db.session.add(download)

    # Increment download count
    app.download_count += 1
    db.session.commit()

    return send_file(
        app.package_path,
        as_attachment=True,
        download_name=f"{app.slug}-{app.version}.flick",
    )


@apps_bp.route("", methods=["POST"])
@promoted_required
def create_app():
    """Create a new app (promoted users only)."""
    user = get_current_user()

    # Handle form data for file upload
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    version = request.form.get("version", "1.0.0").strip()
    category = request.form.get("category", "other")

    if not name or not description:
        return jsonify({"error": "Name and description are required"}), 400

    # Category is now free-form text (no validation needed)

    # Generate slug
    slug = slugify(name)
    base_slug = slug
    counter = 1
    while App.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Handle package file upload
    package_path = None
    if "package" in request.files:
        file = request.files["package"]
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{slug}-{version}.flick")
            upload_folder = current_app.config.get("UPLOAD_FOLDER")
            os.makedirs(upload_folder, exist_ok=True)
            package_path = os.path.join(upload_folder, filename)
            file.save(package_path)

    # Create app
    app_obj = App(
        name=name,
        slug=slug,
        description=description,
        version=version,
        author_id=user.id,
        category=category,
        status=AppStatus.PENDING.value,
        package_path=package_path,
        ai_generated=False,
    )

    db.session.add(app_obj)
    db.session.commit()

    return jsonify({"message": "App created", "app": app_obj.to_dict()}), 201


@apps_bp.route("/<slug>", methods=["PATCH"])
@login_required
def update_app(slug):
    """Update an app (author or admin only)."""
    user = get_current_user()
    app = App.query.filter_by(slug=slug).first()

    if not app:
        return jsonify({"error": "App not found"}), 404

    # Check permissions
    if app.author_id != user.id and not user.is_admin():
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json() or request.form

    # Update allowed fields
    if "description" in data:
        app.description = data["description"].strip()

    if "version" in data:
        app.version = data["version"].strip()

    if "category" in data:
        categories = current_app.config.get("CATEGORIES", [])
        if data["category"] in categories:
            app.category = data["category"]

    db.session.commit()
    return jsonify({"message": "App updated", "app": app.to_dict()})


@apps_bp.route("/<slug>", methods=["DELETE"])
@admin_required
def delete_app(slug):
    """Delete an app (admin only)."""
    app = App.query.filter_by(slug=slug).first()
    if not app:
        return jsonify({"error": "App not found"}), 404

    # Delete package file if exists
    if app.package_path and os.path.exists(app.package_path):
        os.remove(app.package_path)

    # Delete screenshot files
    for screenshot in app.screenshots.all():
        if os.path.exists(screenshot.path):
            os.remove(screenshot.path)

    db.session.delete(app)
    db.session.commit()

    return jsonify({"message": "App deleted"})


@apps_bp.route("/<slug>/screenshots", methods=["POST"])
@login_required
def add_screenshot(slug):
    """Add a screenshot to an app."""
    user = get_current_user()
    app = App.query.filter_by(slug=slug).first()

    if not app:
        return jsonify({"error": "App not found"}), 404

    if app.author_id != user.id and not user.is_admin():
        return jsonify({"error": "Permission denied"}), 403

    if "screenshot" not in request.files:
        return jsonify({"error": "No screenshot file provided"}), 400

    file = request.files["screenshot"]
    if not file or not file.filename:
        return jsonify({"error": "Invalid file"}), 400

    # Validate file type
    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        return jsonify({"error": "Invalid file type"}), 400

    # Save file
    screenshots_folder = current_app.config.get("SCREENSHOTS_FOLDER")
    os.makedirs(screenshots_folder, exist_ok=True)

    screenshot_count = app.screenshots.count()
    filename = secure_filename(f"{slug}-{screenshot_count + 1}.{ext}")
    filepath = os.path.join(screenshots_folder, filename)
    file.save(filepath)

    # Create screenshot record
    caption = request.form.get("caption", "")
    screenshot = Screenshot(
        app_id=app.id, path=filepath, caption=caption, order=screenshot_count
    )

    db.session.add(screenshot)
    db.session.commit()

    return jsonify({"message": "Screenshot added", "screenshot": screenshot.to_dict()}), 201


@apps_bp.route("/<slug>/screenshots/<int:screenshot_id>", methods=["DELETE"])
@login_required
def delete_screenshot(slug, screenshot_id):
    """Delete a screenshot from an app."""
    user = get_current_user()
    app = App.query.filter_by(slug=slug).first()

    if not app:
        return jsonify({"error": "App not found"}), 404

    if app.author_id != user.id and not user.is_admin():
        return jsonify({"error": "Permission denied"}), 403

    screenshot = Screenshot.query.filter_by(id=screenshot_id, app_id=app.id).first()
    if not screenshot:
        return jsonify({"error": "Screenshot not found"}), 404

    # Delete file
    if os.path.exists(screenshot.path):
        os.remove(screenshot.path)

    db.session.delete(screenshot)
    db.session.commit()

    return jsonify({"message": "Screenshot deleted"})


@apps_bp.route("/featured", methods=["GET"])
def get_featured_apps():
    """Get featured/popular apps."""
    # Get top downloaded stable apps
    top_apps = (
        App.query.filter(App.status == AppStatus.STABLE.value)
        .order_by(App.download_count.desc())
        .limit(10)
        .all()
    )

    # Get recently added stable apps
    recent_apps = (
        App.query.filter(App.status == AppStatus.STABLE.value)
        .order_by(App.created_at.desc())
        .limit(10)
        .all()
    )

    return jsonify(
        {
            "popular": [app.to_dict() for app in top_apps],
            "recent": [app.to_dict() for app in recent_apps],
        }
    )
