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

"""Feedback and bug report routes for Flick Forge."""

from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, App, Feedback, AppStatus
from routes.auth import (
    get_current_user,
    get_anonymous_id,
    promoted_required,
    admin_required,
)

feedback_bp = Blueprint("feedback", __name__, url_prefix="/api/feedback")

VALID_FEEDBACK_TYPES = ["bug", "suggestion", "rebuild_request"]
PRIORITY_LEVELS = {"low": 0, "medium": 1, "high": 2}


@feedback_bp.route("/app/<slug>", methods=["GET"])
def list_feedback(slug):
    """List all feedback for an app."""
    app = App.query.filter_by(slug=slug).first()
    if not app:
        return jsonify({"error": "App not found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    feedback_type = request.args.get("type")
    sort_by = request.args.get("sort", "created_at")  # created_at, priority

    query = Feedback.query.filter_by(app_id=app.id)

    # Filter by type
    if feedback_type and feedback_type in VALID_FEEDBACK_TYPES:
        query = query.filter(Feedback.feedback_type == feedback_type)

    # Sorting
    if sort_by == "priority":
        query = query.order_by(Feedback.priority.desc())
    else:
        query = query.order_by(Feedback.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Count by type
    type_counts = {}
    for ft in VALID_FEEDBACK_TYPES:
        type_counts[ft] = Feedback.query.filter_by(app_id=app.id, feedback_type=ft).count()

    return jsonify(
        {
            "app_slug": slug,
            "feedback": [fb.to_dict() for fb in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
            "type_counts": type_counts,
        }
    )


@feedback_bp.route("/app/<slug>", methods=["POST"])
def create_feedback(slug):
    """Create feedback for an app (anonymous users allowed for basic feedback)."""
    app = App.query.filter_by(slug=slug).first()
    if not app:
        return jsonify({"error": "App not found"}), 404

    # Only allow feedback on accessible apps
    if app.status not in [AppStatus.STABLE.value, AppStatus.WILD_WEST.value]:
        return jsonify({"error": "App is not available for feedback"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    feedback_type = data.get("type", "").strip()
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    priority = data.get("priority", "low")

    # Validate type
    if feedback_type not in VALID_FEEDBACK_TYPES:
        return jsonify({"error": f"Type must be one of: {', '.join(VALID_FEEDBACK_TYPES)}"}), 400

    # Validate required fields
    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400

    if len(title) > 200:
        return jsonify({"error": "Title must be 200 characters or less"}), 400

    if len(content) > 5000:
        return jsonify({"error": "Content must be 5000 characters or less"}), 400

    # Validate priority
    if priority not in PRIORITY_LEVELS:
        priority = "low"

    user = get_current_user()
    anonymous_id = get_anonymous_id() if not user else None

    # Rebuild requests require authentication for promoted users
    triggers_rebuild = False
    if feedback_type == "rebuild_request":
        if not user:
            return jsonify({"error": "Authentication required for rebuild requests"}), 401
        if not user.is_promoted():
            # Non-promoted users can submit rebuild requests but they need approval
            triggers_rebuild = False
        else:
            # Promoted users' rebuild requests are auto-approved
            triggers_rebuild = True

    # Create feedback
    feedback = Feedback(
        app_id=app.id,
        author_id=user.id if user else None,
        anonymous_id=anonymous_id,
        feedback_type=feedback_type,
        title=title,
        content=content,
        priority=PRIORITY_LEVELS.get(priority, 0),
        triggers_rebuild=triggers_rebuild,
        rebuild_requested_at=datetime.utcnow() if triggers_rebuild else None,
    )

    db.session.add(feedback)
    db.session.commit()

    # If triggers rebuild, start the rebuild process
    if triggers_rebuild:
        trigger_app_rebuild(app.id, feedback.id)

    return jsonify({"message": "Feedback submitted", "feedback": feedback.to_dict()}), 201


@feedback_bp.route("/<int:feedback_id>", methods=["GET"])
def get_feedback(feedback_id):
    """Get a specific feedback item."""
    feedback = Feedback.query.get(feedback_id)
    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404

    return jsonify({"feedback": feedback.to_dict()})


@feedback_bp.route("/<int:feedback_id>", methods=["PATCH"])
def update_feedback(feedback_id):
    """Update feedback (author only)."""
    user = get_current_user()
    feedback = Feedback.query.get(feedback_id)

    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404

    # Check permissions
    if user:
        if feedback.author_id != user.id and not user.is_admin():
            return jsonify({"error": "Permission denied"}), 403
    else:
        anonymous_id = get_anonymous_id()
        if feedback.anonymous_id != anonymous_id:
            return jsonify({"error": "Permission denied"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "title" in data:
        title = data["title"].strip()
        if len(title) > 200:
            return jsonify({"error": "Title must be 200 characters or less"}), 400
        feedback.title = title

    if "content" in data:
        content = data["content"].strip()
        if len(content) > 5000:
            return jsonify({"error": "Content must be 5000 characters or less"}), 400
        feedback.content = content

    if "priority" in data:
        if data["priority"] in PRIORITY_LEVELS:
            feedback.priority = PRIORITY_LEVELS[data["priority"]]

    db.session.commit()
    return jsonify({"message": "Feedback updated", "feedback": feedback.to_dict()})


@feedback_bp.route("/<int:feedback_id>", methods=["DELETE"])
def delete_feedback(feedback_id):
    """Delete feedback (author or admin only)."""
    user = get_current_user()
    feedback = Feedback.query.get(feedback_id)

    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404

    # Check permissions
    if user:
        if feedback.author_id != user.id and not user.is_admin():
            return jsonify({"error": "Permission denied"}), 403
    else:
        anonymous_id = get_anonymous_id()
        if feedback.anonymous_id != anonymous_id:
            return jsonify({"error": "Permission denied"}), 403

    db.session.delete(feedback)
    db.session.commit()

    return jsonify({"message": "Feedback deleted"})


@feedback_bp.route("/<int:feedback_id>/approve-rebuild", methods=["POST"])
@promoted_required
def approve_rebuild(feedback_id):
    """Approve a rebuild request (promoted users only)."""
    user = get_current_user()
    feedback = Feedback.query.get(feedback_id)

    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404

    if feedback.feedback_type != "rebuild_request":
        return jsonify({"error": "This feedback is not a rebuild request"}), 400

    if feedback.rebuild_approved:
        return jsonify({"error": "Rebuild already approved"}), 400

    feedback.rebuild_approved = True
    feedback.rebuild_approved_by_id = user.id
    feedback.triggers_rebuild = True
    feedback.rebuild_requested_at = datetime.utcnow()

    db.session.commit()

    # Trigger the rebuild
    trigger_app_rebuild(feedback.app_id, feedback.id)

    return jsonify({"message": "Rebuild approved", "feedback": feedback.to_dict()})


@feedback_bp.route("/<int:feedback_id>/reject-rebuild", methods=["POST"])
@promoted_required
def reject_rebuild(feedback_id):
    """Reject a rebuild request (promoted users only)."""
    feedback = Feedback.query.get(feedback_id)

    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404

    if feedback.feedback_type != "rebuild_request":
        return jsonify({"error": "This feedback is not a rebuild request"}), 400

    feedback.rebuild_approved = False
    feedback.triggers_rebuild = False

    db.session.commit()

    return jsonify({"message": "Rebuild rejected", "feedback": feedback.to_dict()})


@feedback_bp.route("/rebuild-queue", methods=["GET"])
@promoted_required
def list_rebuild_queue():
    """List pending rebuild requests (promoted users only)."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = Feedback.query.filter(
        Feedback.feedback_type == "rebuild_request",
        Feedback.rebuild_approved == None,
    ).order_by(Feedback.priority.desc(), Feedback.created_at.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "feedback": [fb.to_dict() for fb in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@feedback_bp.route("/my-feedback", methods=["GET"])
def get_my_feedback():
    """Get feedback submitted by the current user or anonymous ID."""
    user = get_current_user()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    if user:
        query = Feedback.query.filter_by(author_id=user.id)
    else:
        anonymous_id = get_anonymous_id()
        query = Feedback.query.filter_by(anonymous_id=anonymous_id)

    pagination = query.order_by(Feedback.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "feedback": [fb.to_dict() for fb in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@feedback_bp.route("/stats/<slug>", methods=["GET"])
def get_feedback_stats(slug):
    """Get feedback statistics for an app."""
    app = App.query.filter_by(slug=slug).first()
    if not app:
        return jsonify({"error": "App not found"}), 404

    stats = {
        "total": Feedback.query.filter_by(app_id=app.id).count(),
        "by_type": {},
        "by_priority": {},
        "pending_rebuilds": Feedback.query.filter(
            Feedback.app_id == app.id,
            Feedback.feedback_type == "rebuild_request",
            Feedback.rebuild_approved == None,
        ).count(),
    }

    for ft in VALID_FEEDBACK_TYPES:
        stats["by_type"][ft] = Feedback.query.filter_by(
            app_id=app.id, feedback_type=ft
        ).count()

    for priority_name, priority_value in PRIORITY_LEVELS.items():
        stats["by_priority"][priority_name] = Feedback.query.filter_by(
            app_id=app.id, priority=priority_value
        ).count()

    return jsonify({"app_slug": slug, "stats": stats})


# ============================================================================
# STUBS FOR BUILD INTEGRATION
# ============================================================================


def trigger_app_rebuild(app_id, feedback_id):
    """
    Trigger a rebuild of an app based on feedback.

    STUB: This will integrate with Claude Code to rebuild the app
    with the feedback incorporated. For now, it just logs the request.

    The rebuild process should:
    1. Fetch the original app request prompt
    2. Append the feedback as additional context
    3. Trigger a new build with Claude Code
    4. Create a new version of the app
    5. Move the new version to Wild West for testing

    In production, this should be an async task (Celery, etc.)
    """
    from flask import current_app

    app = App.query.get(app_id)
    feedback = Feedback.query.get(feedback_id)

    if not app or not feedback:
        return

    if current_app.config.get("CLAUDE_CODE_ENABLED"):
        # endpoint = current_app.config.get("CLAUDE_CODE_ENDPOINT")
        # Start async rebuild job
        pass
    else:
        # Log that a rebuild would be triggered
        current_app.logger.info(
            f"Rebuild triggered for app {app.slug} based on feedback {feedback_id}: "
            f"{feedback.title}"
        )
