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

"""App request/prompt routes for Flick Forge."""

from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from models import db, AppRequest, RequestVote, RequestStatus
from routes.auth import (
    get_current_user,
    login_required,
    limited_required,
    promoted_required,
    admin_required,
)

requests_bp = Blueprint("requests", __name__, url_prefix="/api/requests")


@requests_bp.route("", methods=["GET"])
def list_requests():
    """List all app requests."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status = request.args.get("status")  # pending, approved, building, completed, rejected
    sort_by = request.args.get("sort", "created_at")  # created_at, upvotes

    query = AppRequest.query

    # Filter by status
    if status:
        if status in [s.value for s in RequestStatus]:
            query = query.filter(AppRequest.status == status)
    else:
        # By default, show pending and approved (not rejected)
        query = query.filter(
            AppRequest.status.in_(
                [
                    RequestStatus.PENDING.value,
                    RequestStatus.APPROVED.value,
                    RequestStatus.BUILDING.value,
                    RequestStatus.COMPLETED.value,
                ]
            )
        )

    # Sorting
    if sort_by == "upvotes":
        query = query.order_by(AppRequest.upvotes.desc())
    else:
        query = query.order_by(AppRequest.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "requests": [req.to_dict() for req in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
    )


@requests_bp.route("/<int:request_id>", methods=["GET"])
def get_request(request_id):
    """Get detailed information about a specific request."""
    app_request = AppRequest.query.get(request_id)
    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    return jsonify({"request": app_request.to_dict()})


@requests_bp.route("", methods=["POST"])
@login_required
def create_request():
    """Create a new app request (any logged-in user)."""
    user = get_current_user()
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    title = data.get("title", "").strip()
    prompt = data.get("prompt", "").strip()
    category = data.get("category")

    if not title or not prompt:
        return jsonify({"error": "Title and prompt are required"}), 400

    if len(title) > 200:
        return jsonify({"error": "Title must be 200 characters or less"}), 400

    if len(prompt) > 10000:
        return jsonify({"error": "Prompt must be 10000 characters or less"}), 400

    # Validate category if provided
    if category:
        categories = current_app.config.get("CATEGORIES", [])
        if category not in categories:
            return jsonify({"error": "Invalid category"}), 400

    # Create request
    app_request = AppRequest(
        title=title,
        prompt=prompt,
        requester_id=user.id,
        category=category,
        status=RequestStatus.PENDING.value,
    )

    db.session.add(app_request)
    db.session.commit()

    # Trigger AI safety check asynchronously (stub for now)
    trigger_safety_check(app_request.id)

    return jsonify({"message": "Request created", "request": app_request.to_dict()}), 201


@requests_bp.route("/<int:request_id>", methods=["PATCH"])
@limited_required
def update_request(request_id):
    """Update a request (requester only, before approval)."""
    user = get_current_user()
    app_request = AppRequest.query.get(request_id)

    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    # Only requester can update
    if app_request.requester_id != user.id and not user.is_admin():
        return jsonify({"error": "Permission denied"}), 403

    # Can only update pending requests
    if app_request.status != RequestStatus.PENDING.value:
        return jsonify({"error": "Cannot modify request after approval process started"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "title" in data:
        title = data["title"].strip()
        if len(title) > 200:
            return jsonify({"error": "Title must be 200 characters or less"}), 400
        app_request.title = title

    if "prompt" in data:
        prompt = data["prompt"].strip()
        if len(prompt) > 10000:
            return jsonify({"error": "Prompt must be 10000 characters or less"}), 400
        app_request.prompt = prompt
        # Re-trigger safety check
        app_request.safety_checked = False
        trigger_safety_check(app_request.id)

    if "category" in data:
        categories = current_app.config.get("CATEGORIES", [])
        if data["category"] in categories:
            app_request.category = data["category"]

    db.session.commit()
    return jsonify({"message": "Request updated", "request": app_request.to_dict()})


@requests_bp.route("/<int:request_id>", methods=["DELETE"])
@limited_required
def delete_request(request_id):
    """Delete a request (requester or admin only)."""
    user = get_current_user()
    app_request = AppRequest.query.get(request_id)

    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    # Only requester or admin can delete
    if app_request.requester_id != user.id and not user.is_admin():
        return jsonify({"error": "Permission denied"}), 403

    # Can only delete pending or rejected requests
    if app_request.status not in [RequestStatus.PENDING.value, RequestStatus.REJECTED.value]:
        return jsonify({"error": "Cannot delete request in progress"}), 400

    db.session.delete(app_request)
    db.session.commit()

    return jsonify({"message": "Request deleted"})


@requests_bp.route("/<int:request_id>/upvote", methods=["POST"])
@limited_required
def upvote_request(request_id):
    """Upvote a request (limited users and above)."""
    user = get_current_user()
    app_request = AppRequest.query.get(request_id)

    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    # Check if already voted
    existing_vote = RequestVote.query.filter_by(
        request_id=request_id, user_id=user.id
    ).first()

    if existing_vote:
        return jsonify({"error": "Already voted on this request"}), 409

    # Create vote
    vote = RequestVote(request_id=request_id, user_id=user.id)
    db.session.add(vote)
    app_request.upvotes += 1
    db.session.commit()

    return jsonify({"message": "Vote recorded", "upvotes": app_request.upvotes})


@requests_bp.route("/<int:request_id>/upvote", methods=["DELETE"])
@limited_required
def remove_upvote(request_id):
    """Remove upvote from a request."""
    user = get_current_user()
    app_request = AppRequest.query.get(request_id)

    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    vote = RequestVote.query.filter_by(request_id=request_id, user_id=user.id).first()

    if not vote:
        return jsonify({"error": "Vote not found"}), 404

    db.session.delete(vote)
    app_request.upvotes = max(0, app_request.upvotes - 1)
    db.session.commit()

    return jsonify({"message": "Vote removed", "upvotes": app_request.upvotes})


@requests_bp.route("/<int:request_id>/approve", methods=["POST"])
@promoted_required
def approve_request(request_id):
    """Approve a request for building (promoted users or admin)."""
    user = get_current_user()
    app_request = AppRequest.query.get(request_id)

    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    if app_request.status != RequestStatus.PENDING.value:
        return jsonify({"error": "Request is not pending approval"}), 400

    # Check safety status
    if not app_request.safety_checked:
        return jsonify({"error": "Request has not been safety checked yet"}), 400

    if app_request.safety_passed is False:
        return jsonify({"error": "Request failed safety check"}), 400

    # Approve
    app_request.status = RequestStatus.APPROVED.value
    app_request.approved_by_id = user.id
    app_request.approved_at = datetime.utcnow()

    db.session.commit()

    # Trigger build process (stub for now)
    trigger_build(app_request.id)

    return jsonify({"message": "Request approved", "request": app_request.to_dict()})


@requests_bp.route("/<int:request_id>/reject", methods=["POST"])
@promoted_required
def reject_request(request_id):
    """Reject a request (promoted users or admin)."""
    user = get_current_user()
    app_request = AppRequest.query.get(request_id)

    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    if app_request.status != RequestStatus.PENDING.value:
        return jsonify({"error": "Request is not pending"}), 400

    data = request.get_json() or {}
    reason = data.get("reason", "").strip()

    if not reason:
        return jsonify({"error": "Rejection reason is required"}), 400

    app_request.status = RequestStatus.REJECTED.value
    app_request.rejection_reason = reason
    app_request.approved_by_id = user.id
    app_request.approved_at = datetime.utcnow()

    db.session.commit()

    return jsonify({"message": "Request rejected", "request": app_request.to_dict()})


@requests_bp.route("/<int:request_id>/status", methods=["GET"])
def get_request_status(request_id):
    """Get the current status of a request."""
    app_request = AppRequest.query.get(request_id)
    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    status_info = {
        "id": app_request.id,
        "status": app_request.status,
        "safety_checked": app_request.safety_checked,
        "safety_passed": app_request.safety_passed,
        "approved_at": app_request.approved_at.isoformat() if app_request.approved_at else None,
        "build_started_at": (
            app_request.build_started_at.isoformat()
            if app_request.build_started_at
            else None
        ),
        "build_completed_at": (
            app_request.build_completed_at.isoformat()
            if app_request.build_completed_at
            else None
        ),
        "resulting_app_id": (
            app_request.resulting_app.id if app_request.resulting_app else None
        ),
    }

    return jsonify({"status": status_info})


@requests_bp.route("/<int:request_id>/build-log", methods=["GET"])
def get_build_log(request_id):
    """Get the build log for a request (public)."""
    app_request = AppRequest.query.get(request_id)
    if not app_request:
        return jsonify({"error": "Request not found"}), 404

    return jsonify({
        "id": app_request.id,
        "title": app_request.title,
        "status": app_request.status,
        "build_log": app_request.build_log or "No build log available yet.",
        "build_started_at": (
            app_request.build_started_at.isoformat()
            if app_request.build_started_at
            else None
        ),
        "build_completed_at": (
            app_request.build_completed_at.isoformat()
            if app_request.build_completed_at
            else None
        ),
    })


@requests_bp.route("/pending-approval", methods=["GET"])
@promoted_required
def list_pending_approval():
    """List requests pending approval (for promoted users)."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = AppRequest.query.filter(
        AppRequest.status == RequestStatus.PENDING.value,
        AppRequest.safety_checked == True,
        AppRequest.safety_passed == True,
    ).order_by(AppRequest.upvotes.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "requests": [req.to_dict() for req in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@requests_bp.route("/my-requests", methods=["GET"])
@limited_required
def get_my_requests():
    """Get requests by the current user."""
    user = get_current_user()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    pagination = (
        AppRequest.query.filter_by(requester_id=user.id)
        .order_by(AppRequest.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify(
        {
            "requests": [req.to_dict() for req in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


# ============================================================================
# STUBS FOR AI INTEGRATION
# These functions are stubs that will be replaced with actual Claude Code
# integration when ready.
# ============================================================================


def trigger_safety_check(request_id):
    """
    Trigger AI safety check for a request.

    STUB: This will integrate with Claude Code or another AI safety
    verification system. For now, it auto-approves all requests.

    The safety check should:
    1. Analyze the prompt for potentially harmful content
    2. Check for attempts to create malware or harmful software
    3. Verify the request doesn't violate terms of service
    4. Flag anything that needs human review

    In production, this should be an async task (Celery, etc.)
    """
    from models import AppRequest

    app_request = AppRequest.query.get(request_id)
    if not app_request:
        return

    # STUB: Auto-approve for now
    # In production, this would call an AI safety endpoint
    if current_app.config.get("AI_SAFETY_ENABLED"):
        # Call external AI safety service
        # endpoint = current_app.config.get("AI_SAFETY_ENDPOINT")
        # response = requests.post(endpoint, json={"prompt": app_request.prompt})
        # app_request.safety_passed = response.json().get("safe", False)
        # app_request.safety_notes = response.json().get("notes", "")
        pass
    else:
        # Auto-pass for development
        app_request.safety_passed = True
        app_request.safety_notes = "Auto-approved (safety check disabled)"

    app_request.safety_checked = True
    db.session.commit()


def trigger_build(request_id):
    """
    Trigger build process for an approved request.

    STUB: This will integrate with Claude Code to actually build
    the app from the prompt. For now, it just marks the request
    as building.

    The build process should:
    1. Send the prompt to Claude Code
    2. Monitor the build process
    3. Package the resulting app as a .flick file
    4. Create an App entry in the database
    5. Move the app to Wild West testing

    In production, this should be an async task (Celery, etc.)
    """
    from models import AppRequest, RequestStatus

    app_request = AppRequest.query.get(request_id)
    if not app_request:
        return

    app_request.status = RequestStatus.BUILDING.value
    app_request.build_started_at = datetime.utcnow()
    db.session.commit()

    # STUB: In production, this would trigger an async build job
    # that calls Claude Code with the prompt and creates the app
    if current_app.config.get("CLAUDE_CODE_ENABLED"):
        # endpoint = current_app.config.get("CLAUDE_CODE_ENDPOINT")
        # Start async build job
        pass
    else:
        # For now, just log that a build would be triggered
        app_request.build_log = (
            "Build would be triggered here.\n"
            "Claude Code integration not yet implemented.\n"
            f"Prompt: {app_request.prompt[:200]}..."
        )
        db.session.commit()
