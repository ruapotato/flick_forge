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

"""Admin routes for Flick Forge."""

from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, User, App, AppRequest, Feedback, UserTier, AppStatus, RequestStatus
from routes.auth import get_current_user, admin_required, promoted_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ============================================================================
# User Management
# ============================================================================


@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """List all users with filters."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    tier = request.args.get("tier")
    search = request.args.get("search", "").strip()

    query = User.query

    # Filter by tier
    if tier:
        try:
            tier_value = UserTier[tier.upper()].value
            query = query.filter(User.tier == tier_value)
        except KeyError:
            pass

    # Search by username or email
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_pattern)) | (User.email.ilike(search_pattern))
        )

    query = query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "users": [user.to_dict(include_email=True) for user in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_required
def get_user(user_id):
    """Get detailed user information."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Include statistics
    stats = {
        "apps_submitted": user.apps.count(),
        "reviews_written": user.reviews.count(),
        "requests_submitted": user.requests.count(),
        "feedback_submitted": user.feedback.count(),
    }

    user_data = user.to_dict(include_email=True)
    user_data["stats"] = stats

    return jsonify({"user": user_data})


@admin_bp.route("/users/<int:user_id>/tier", methods=["PUT"])
@admin_required
def set_user_tier(user_id):
    """Set a user's tier directly."""
    admin = get_current_user()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.id == admin.id:
        return jsonify({"error": "Cannot modify your own tier"}), 400

    data = request.get_json() or {}
    target_tier = data.get("tier", "").lower()

    tier_map = {
        "anonymous": UserTier.ANONYMOUS.value,
        "limited": UserTier.LIMITED.value,
        "promoted": UserTier.PROMOTED.value,
        "admin": UserTier.ADMIN.value,
    }

    if target_tier not in tier_map:
        return jsonify({"error": f"Invalid tier. Must be one of: {', '.join(tier_map.keys())}"}), 400

    # Cannot demote other admins
    if user.tier == UserTier.ADMIN.value and target_tier != "admin":
        return jsonify({"error": "Cannot demote admin users"}), 400

    user.tier = tier_map[target_tier]
    db.session.commit()

    return jsonify(
        {
            "message": f"User tier set to {target_tier}",
            "user": user.to_dict(include_email=True),
        }
    )


@admin_bp.route("/users/<int:user_id>/promote", methods=["POST"])
@admin_required
def promote_user(user_id):
    """Promote a user to a higher tier."""
    admin = get_current_user()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.id == admin.id:
        return jsonify({"error": "Cannot modify your own tier"}), 400

    data = request.get_json() or {}
    target_tier = data.get("tier", "").lower()

    # Validate tier
    tier_map = {
        "limited": UserTier.LIMITED.value,
        "promoted": UserTier.PROMOTED.value,
        "admin": UserTier.ADMIN.value,
    }

    if target_tier not in tier_map:
        return jsonify({"error": f"Invalid tier. Must be one of: {', '.join(tier_map.keys())}"}), 400

    new_tier_value = tier_map[target_tier]

    # Cannot demote admins (safety measure)
    if user.tier == UserTier.ADMIN.value and new_tier_value < UserTier.ADMIN.value:
        return jsonify({"error": "Cannot demote admin users through this endpoint"}), 400

    user.tier = new_tier_value
    db.session.commit()

    return jsonify(
        {
            "message": f"User promoted to {target_tier}",
            "user": user.to_dict(include_email=True),
        }
    )


@admin_bp.route("/users/<int:user_id>/demote", methods=["POST"])
@admin_required
def demote_user(user_id):
    """Demote a user to a lower tier (admin only, with confirmation)."""
    admin = get_current_user()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.id == admin.id:
        return jsonify({"error": "Cannot modify your own tier"}), 400

    data = request.get_json() or {}
    target_tier = data.get("tier", "").lower()
    confirm = data.get("confirm", False)

    if not confirm:
        return jsonify({"error": "Demotion requires confirmation. Set 'confirm': true"}), 400

    tier_map = {
        "limited": UserTier.LIMITED.value,
        "promoted": UserTier.PROMOTED.value,
    }

    if target_tier not in tier_map:
        return jsonify({"error": f"Invalid tier. Must be one of: {', '.join(tier_map.keys())}"}), 400

    user.tier = tier_map[target_tier]
    db.session.commit()

    return jsonify(
        {
            "message": f"User demoted to {target_tier}",
            "user": user.to_dict(include_email=True),
        }
    )


@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@admin_required
def deactivate_user(user_id):
    """Deactivate a user account."""
    admin = get_current_user()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.id == admin.id:
        return jsonify({"error": "Cannot deactivate your own account"}), 400

    user.is_active = False
    db.session.commit()

    return jsonify({"message": "User deactivated", "user": user.to_dict(include_email=True)})


@admin_bp.route("/users/<int:user_id>/activate", methods=["POST"])
@admin_required
def activate_user(user_id):
    """Reactivate a user account."""
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    user.is_active = True
    db.session.commit()

    return jsonify({"message": "User activated", "user": user.to_dict(include_email=True)})


# ============================================================================
# App Management
# ============================================================================


@admin_bp.route("/apps/pending", methods=["GET"])
@promoted_required
def list_pending_apps():
    """List apps pending approval."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = App.query.filter(App.status == AppStatus.PENDING.value)
    query = query.order_by(App.created_at.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "apps": [app.to_dict() for app in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@admin_bp.route("/apps/<slug>/approve-to-wildwest", methods=["POST"])
@promoted_required
def approve_to_wild_west(slug):
    """Move an app from pending to Wild West testing."""
    user = get_current_user()
    app = App.query.filter_by(slug=slug).first()

    if not app:
        return jsonify({"error": "App not found"}), 404

    if app.status != AppStatus.PENDING.value:
        return jsonify({"error": "App is not pending approval"}), 400

    app.status = AppStatus.WILD_WEST.value
    db.session.commit()

    return jsonify({"message": "App moved to Wild West", "app": app.to_dict()})


@admin_bp.route("/apps/<slug>/approve-to-stable", methods=["POST"])
@promoted_required
def approve_to_stable(slug):
    """Promote an app from Wild West to stable."""
    user = get_current_user()
    app = App.query.filter_by(slug=slug).first()

    if not app:
        return jsonify({"error": "App not found"}), 404

    if app.status != AppStatus.WILD_WEST.value:
        return jsonify({"error": "App must be in Wild West before promotion to stable"}), 400

    old_status = app.status
    app.status = AppStatus.STABLE.value
    db.session.commit()

    # Notify subscribers of promotion
    try:
        from routes.subscriptions import notify_subscribers_of_promotion
        notify_subscribers_of_promotion(app, old_status, AppStatus.STABLE.value)
    except Exception as e:
        pass  # Don't fail the promotion if notification fails

    return jsonify({"message": "App promoted to stable", "app": app.to_dict()})


@admin_bp.route("/apps/<slug>/reject", methods=["POST"])
@promoted_required
def reject_app(slug):
    """Reject an app (move to rejected status)."""
    user = get_current_user()
    app = App.query.filter_by(slug=slug).first()

    if not app:
        return jsonify({"error": "App not found"}), 404

    data = request.get_json() or {}
    reason = data.get("reason", "").strip()

    if not reason:
        return jsonify({"error": "Rejection reason is required"}), 400

    app.status = AppStatus.REJECTED.value
    app.safety_notes = f"Rejected: {reason}"
    db.session.commit()

    return jsonify({"message": "App rejected", "app": app.to_dict()})


@admin_bp.route("/apps/<slug>/demote", methods=["POST"])
@admin_required
def demote_app(slug):
    """Demote a stable app back to Wild West."""
    app = App.query.filter_by(slug=slug).first()

    if not app:
        return jsonify({"error": "App not found"}), 404

    if app.status != AppStatus.STABLE.value:
        return jsonify({"error": "Can only demote stable apps"}), 400

    data = request.get_json() or {}
    reason = data.get("reason", "").strip()

    app.status = AppStatus.WILD_WEST.value
    if reason:
        app.safety_notes = f"Demoted to Wild West: {reason}"
    db.session.commit()

    return jsonify({"message": "App demoted to Wild West", "app": app.to_dict()})


# ============================================================================
# Request Management
# ============================================================================


@admin_bp.route("/requests/pending", methods=["GET"])
@promoted_required
def list_pending_requests():
    """List pending app requests for review (promoted+ users)."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)

    query = AppRequest.query.filter(AppRequest.status == RequestStatus.PENDING.value)
    query = query.order_by(AppRequest.created_at.asc())  # Oldest first
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "requests": [req.to_dict() for req in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@admin_bp.route("/requests/<int:request_id>/approve", methods=["POST"])
@promoted_required
def approve_request(request_id):
    """Approve a pending request for building."""
    app_request = AppRequest.query.get(request_id)

    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    if app_request.status != RequestStatus.PENDING.value:
        return jsonify({"error": "Request is not pending"}), 400

    app_request.status = RequestStatus.APPROVED.value
    db.session.commit()

    return jsonify(
        {
            "message": "Request approved for building",
            "request": app_request.to_dict(),
        }
    )


@admin_bp.route("/requests/<int:request_id>/reject", methods=["POST"])
@promoted_required
def reject_request(request_id):
    """Reject a pending request."""
    app_request = AppRequest.query.get(request_id)

    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    if app_request.status != RequestStatus.PENDING.value:
        return jsonify({"error": "Request is not pending"}), 400

    data = request.get_json() or {}
    reason = data.get("reason", "").strip()

    app_request.status = RequestStatus.REJECTED.value
    if reason:
        app_request.rejection_reason = reason
    db.session.commit()

    return jsonify(
        {
            "message": "Request rejected",
            "request": app_request.to_dict(),
        }
    )


@admin_bp.route("/requests/all", methods=["GET"])
@admin_required
def list_all_requests():
    """List all app requests (admin view)."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    status = request.args.get("status")

    query = AppRequest.query

    if status and status in [s.value for s in RequestStatus]:
        query = query.filter(AppRequest.status == status)

    query = query.order_by(AppRequest.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "requests": [req.to_dict() for req in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@admin_bp.route("/requests/<int:request_id>/force-complete", methods=["POST"])
@admin_required
def force_complete_request(request_id):
    """Force complete a request (for when build is done externally)."""
    app_request = AppRequest.query.get(request_id)

    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    data = request.get_json() or {}
    app_slug = data.get("app_slug")

    if not app_slug:
        return jsonify({"error": "app_slug is required"}), 400

    # Find the app
    app = App.query.filter_by(slug=app_slug).first()
    if not app:
        return jsonify({"error": "App not found"}), 404

    # Link the app to the request
    app.source_request_id = app_request.id
    app.ai_generated = True

    app_request.status = RequestStatus.COMPLETED.value
    app_request.build_completed_at = datetime.utcnow()

    db.session.commit()

    return jsonify(
        {
            "message": "Request marked as completed",
            "request": app_request.to_dict(),
        }
    )


# ============================================================================
# Statistics & Dashboard
# ============================================================================


@admin_bp.route("/stats", methods=["GET"])
@admin_required
def get_admin_stats():
    """Get admin dashboard statistics."""
    stats = {
        "users": {
            "total": User.query.count(),
            "limited": User.query.filter(User.tier == UserTier.LIMITED.value).count(),
            "promoted": User.query.filter(User.tier == UserTier.PROMOTED.value).count(),
            "admin": User.query.filter(User.tier == UserTier.ADMIN.value).count(),
            "active": User.query.filter(User.is_active == True).count(),
        },
        "apps": {
            "total": App.query.count(),
            "pending": App.query.filter(App.status == AppStatus.PENDING.value).count(),
            "wild_west": App.query.filter(App.status == AppStatus.WILD_WEST.value).count(),
            "stable": App.query.filter(App.status == AppStatus.STABLE.value).count(),
            "rejected": App.query.filter(App.status == AppStatus.REJECTED.value).count(),
            "ai_generated": App.query.filter(App.ai_generated == True).count(),
        },
        "requests": {
            "total": AppRequest.query.count(),
            "pending": AppRequest.query.filter(
                AppRequest.status == RequestStatus.PENDING.value
            ).count(),
            "approved": AppRequest.query.filter(
                AppRequest.status == RequestStatus.APPROVED.value
            ).count(),
            "building": AppRequest.query.filter(
                AppRequest.status == RequestStatus.BUILDING.value
            ).count(),
            "completed": AppRequest.query.filter(
                AppRequest.status == RequestStatus.COMPLETED.value
            ).count(),
            "rejected": AppRequest.query.filter(
                AppRequest.status == RequestStatus.REJECTED.value
            ).count(),
        },
        "feedback": {
            "total": Feedback.query.count(),
            "bugs": Feedback.query.filter(Feedback.feedback_type == "bug").count(),
            "suggestions": Feedback.query.filter(
                Feedback.feedback_type == "suggestion"
            ).count(),
            "rebuild_requests": Feedback.query.filter(
                Feedback.feedback_type == "rebuild_request"
            ).count(),
            "pending_rebuilds": Feedback.query.filter(
                Feedback.feedback_type == "rebuild_request",
                Feedback.rebuild_approved == None,
            ).count(),
        },
    }

    return jsonify({"stats": stats})


@admin_bp.route("/activity", methods=["GET"])
@admin_required
def get_recent_activity():
    """Get recent activity for admin dashboard."""
    from models import Review, AppDownload

    # Recent users
    recent_users = (
        User.query.order_by(User.created_at.desc()).limit(10).all()
    )

    # Recent apps
    recent_apps = (
        App.query.order_by(App.created_at.desc()).limit(10).all()
    )

    # Recent requests
    recent_requests = (
        AppRequest.query.order_by(AppRequest.created_at.desc()).limit(10).all()
    )

    # Recent reviews
    recent_reviews = (
        Review.query.order_by(Review.created_at.desc()).limit(10).all()
    )

    return jsonify(
        {
            "recent_users": [u.to_dict() for u in recent_users],
            "recent_apps": [a.to_dict() for a in recent_apps],
            "recent_requests": [r.to_dict() for r in recent_requests],
            "recent_reviews": [r.to_dict() for r in recent_reviews],
        }
    )


# ============================================================================
# System Configuration
# ============================================================================


@admin_bp.route("/config", methods=["GET"])
@admin_required
def get_config():
    """Get current system configuration (safe values only)."""
    from flask import current_app

    config = {
        "categories": current_app.config.get("CATEGORIES", []),
        "max_upload_size_mb": current_app.config.get("MAX_CONTENT_LENGTH", 0)
        // (1024 * 1024),
        "cors_origins": current_app.config.get("CORS_ORIGINS", []),
        "ai_safety_enabled": current_app.config.get("AI_SAFETY_ENABLED", False),
        "claude_code_enabled": current_app.config.get("CLAUDE_CODE_ENABLED", False),
    }

    return jsonify({"config": config})


@admin_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint (no auth required)."""
    try:
        # Test database connection
        db.session.execute(db.text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return jsonify(
        {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "database": db_status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# ============================================================================
# Feedback Management
# ============================================================================


@admin_bp.route("/feedback", methods=["GET"])
@promoted_required
def list_all_feedback():
    """List all feedback across all apps for review."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    feedback_type = request.args.get("type")
    app_slug = request.args.get("app")
    priority = request.args.get("priority")
    sort_by = request.args.get("sort", "created_at")

    query = Feedback.query

    # Filter by type
    if feedback_type and feedback_type in ["bug", "suggestion", "rebuild_request"]:
        query = query.filter(Feedback.feedback_type == feedback_type)

    # Filter by app
    if app_slug:
        app = App.query.filter_by(slug=app_slug).first()
        if app:
            query = query.filter(Feedback.app_id == app.id)

    # Filter by priority
    priority_map = {"low": 0, "medium": 1, "high": 2}
    if priority and priority in priority_map:
        query = query.filter(Feedback.priority == priority_map[priority])

    # Sorting
    if sort_by == "priority":
        query = query.order_by(Feedback.priority.desc(), Feedback.created_at.desc())
    else:
        query = query.order_by(Feedback.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Include app info in response
    feedback_list = []
    for fb in pagination.items:
        fb_dict = fb.to_dict()
        fb_dict["app_slug"] = fb.app.slug if fb.app else None
        fb_dict["app_name"] = fb.app.name if fb.app else None
        feedback_list.append(fb_dict)

    return jsonify(
        {
            "feedback": feedback_list,
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@admin_bp.route("/feedback/<int:feedback_id>/promote-to-rebuild", methods=["POST"])
@promoted_required
def promote_feedback_to_rebuild(feedback_id):
    """Promote a bug/suggestion to trigger an AI rebuild of the app."""
    user = get_current_user()
    feedback = Feedback.query.get(feedback_id)

    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404

    app = App.query.get(feedback.app_id)
    if not app:
        return jsonify({"error": "App not found"}), 404

    # Get original request for this app
    original_request = app.source_request
    if not original_request:
        return jsonify({"error": "No original request found for this app"}), 400

    data = request.get_json() or {}
    additional_context = data.get("context", "").strip()

    # Create a new request that incorporates the feedback
    new_prompt = f"""Original Request:
{original_request.prompt}

---
User Feedback ({feedback.feedback_type}):
Title: {feedback.title}
{feedback.content}
"""
    if additional_context:
        new_prompt += f"\n---\nAdditional Context from Reviewer:\n{additional_context}"

    # Create new rebuild request
    rebuild_request = AppRequest(
        title=f"{app.name} v{_get_next_version(app.version)} (rebuild)",
        prompt=new_prompt,
        requester_id=original_request.requester_id,
        category=app.category,
        status=RequestStatus.APPROVED.value,  # Auto-approve for rebuild
        safety_checked=True,
        safety_passed=True,
        approved_by_id=user.id,
        approved_at=datetime.utcnow(),
    )
    db.session.add(rebuild_request)

    # Mark feedback as triggering rebuild
    feedback.triggers_rebuild = True
    feedback.rebuild_approved = True
    feedback.rebuild_approved_by_id = user.id
    feedback.rebuild_requested_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "message": "Rebuild request created from feedback",
        "request_id": rebuild_request.id,
        "feedback": feedback.to_dict(),
    })


@admin_bp.route("/feedback/<int:feedback_id>/dismiss", methods=["POST"])
@promoted_required
def dismiss_feedback(feedback_id):
    """Dismiss feedback (mark as reviewed but not actionable)."""
    feedback = Feedback.query.get(feedback_id)

    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404

    data = request.get_json() or {}
    reason = data.get("reason", "").strip()

    # Mark rebuild as rejected if it was a rebuild request
    if feedback.feedback_type == "rebuild_request":
        feedback.rebuild_approved = False

    # Add dismissal note
    if reason:
        feedback.content += f"\n\n[Dismissed: {reason}]"

    db.session.commit()

    return jsonify({"message": "Feedback dismissed", "feedback": feedback.to_dict()})


def _get_next_version(current_version):
    """Increment version number."""
    try:
        parts = current_version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    except:
        return "1.0.1"
