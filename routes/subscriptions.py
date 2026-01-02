# Flick Forge - Flick Store Backend
# Copyright (C) 2025 Flick Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Subscription and notification routes for Flick Forge."""

from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, App, AppSubscription, Notification
from routes.auth import get_current_user, login_required

subscriptions_bp = Blueprint("subscriptions", __name__, url_prefix="/api/subscriptions")


# ============================================================================
# Subscription Endpoints
# ============================================================================


@subscriptions_bp.route("/app/<slug>", methods=["POST"])
@login_required
def subscribe_to_app(slug):
    """Subscribe to app updates."""
    user = get_current_user()
    app = App.query.filter_by(slug=slug).first()

    if not app:
        return jsonify({"error": "App not found"}), 404

    # Check if already subscribed
    existing = AppSubscription.query.filter_by(
        app_id=app.id, user_id=user.id
    ).first()

    if existing:
        return jsonify({"error": "Already subscribed", "subscription": existing.to_dict()}), 400

    subscription = AppSubscription(
        app_id=app.id,
        user_id=user.id,
    )
    db.session.add(subscription)
    db.session.commit()

    return jsonify({
        "message": f"Subscribed to {app.name}",
        "subscription": subscription.to_dict()
    }), 201


@subscriptions_bp.route("/app/<slug>", methods=["DELETE"])
@login_required
def unsubscribe_from_app(slug):
    """Unsubscribe from app updates."""
    user = get_current_user()
    app = App.query.filter_by(slug=slug).first()

    if not app:
        return jsonify({"error": "App not found"}), 404

    subscription = AppSubscription.query.filter_by(
        app_id=app.id, user_id=user.id
    ).first()

    if not subscription:
        return jsonify({"error": "Not subscribed"}), 404

    db.session.delete(subscription)
    db.session.commit()

    return jsonify({"message": f"Unsubscribed from {app.name}"})


@subscriptions_bp.route("/app/<slug>/status", methods=["GET"])
@login_required
def get_subscription_status(slug):
    """Check if user is subscribed to an app."""
    user = get_current_user()
    app = App.query.filter_by(slug=slug).first()

    if not app:
        return jsonify({"error": "App not found"}), 404

    subscription = AppSubscription.query.filter_by(
        app_id=app.id, user_id=user.id
    ).first()

    return jsonify({
        "subscribed": subscription is not None,
        "subscription": subscription.to_dict() if subscription else None
    })


@subscriptions_bp.route("/my", methods=["GET"])
@login_required
def get_my_subscriptions():
    """Get all subscriptions for current user."""
    user = get_current_user()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)

    query = AppSubscription.query.filter_by(user_id=user.id)
    query = query.order_by(AppSubscription.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "subscriptions": [s.to_dict() for s in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page,
    })


# ============================================================================
# Notification Endpoints
# ============================================================================


@subscriptions_bp.route("/notifications", methods=["GET"])
@login_required
def get_notifications():
    """Get notifications for current user."""
    user = get_current_user()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    unread_only = request.args.get("unread", "false").lower() == "true"

    query = Notification.query.filter_by(user_id=user.id)

    if unread_only:
        query = query.filter_by(read=False)

    query = query.order_by(Notification.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Count unread
    unread_count = Notification.query.filter_by(user_id=user.id, read=False).count()

    return jsonify({
        "notifications": [n.to_dict() for n in pagination.items],
        "unread_count": unread_count,
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page,
    })


@subscriptions_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    user = get_current_user()
    notification = Notification.query.get(notification_id)

    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    if notification.user_id != user.id:
        return jsonify({"error": "Permission denied"}), 403

    notification.read = True
    db.session.commit()

    return jsonify({"message": "Notification marked as read"})


@subscriptions_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read."""
    user = get_current_user()

    Notification.query.filter_by(user_id=user.id, read=False).update({"read": True})
    db.session.commit()

    return jsonify({"message": "All notifications marked as read"})


@subscriptions_bp.route("/notifications/<int:notification_id>", methods=["DELETE"])
@login_required
def delete_notification(notification_id):
    """Delete a notification."""
    user = get_current_user()
    notification = Notification.query.get(notification_id)

    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    if notification.user_id != user.id:
        return jsonify({"error": "Permission denied"}), 403

    db.session.delete(notification)
    db.session.commit()

    return jsonify({"message": "Notification deleted"})


# ============================================================================
# Helper Functions for Creating Notifications
# ============================================================================


def notify_subscribers_of_new_build(app, new_version):
    """
    Notify all subscribers when an app gets a new build.
    Called from build_app.py when a build completes.
    """
    subscriptions = AppSubscription.query.filter_by(app_id=app.id).all()

    for sub in subscriptions:
        notification = Notification(
            user_id=sub.user_id,
            notification_type="new_build",
            title=f"New build: {app.name}",
            message=f"{app.name} has been rebuilt with version {new_version}. Check it out!",
            app_id=app.id,
        )
        db.session.add(notification)

    db.session.commit()
    return len(subscriptions)


def notify_subscribers_of_promotion(app, from_status, to_status):
    """
    Notify subscribers when an app is promoted (e.g., wild_west -> stable).
    """
    subscriptions = AppSubscription.query.filter_by(app_id=app.id).all()

    status_names = {
        "wild_west": "Wild West (Testing)",
        "stable": "Stable",
        "pending": "Pending",
    }

    for sub in subscriptions:
        notification = Notification(
            user_id=sub.user_id,
            notification_type="app_promoted",
            title=f"{app.name} promoted!",
            message=f"{app.name} has been promoted from {status_names.get(from_status, from_status)} to {status_names.get(to_status, to_status)}.",
            app_id=app.id,
        )
        db.session.add(notification)

    db.session.commit()
    return len(subscriptions)
