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

"""SQLAlchemy database models for Flick Forge."""

from datetime import datetime
from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class UserTier(Enum):
    """User permission tiers."""

    ANONYMOUS = 0  # Can browse and install, no request submission
    LIMITED = 1    # Can submit requests (was "trusted")
    PROMOTED = 2   # Can approve requests
    ADMIN = 3      # Full access


class AppStatus(Enum):
    """App publication status."""

    PENDING = "pending"  # Awaiting AI safety check
    WILD_WEST = "wild_west"  # In testing area
    STABLE = "stable"  # Approved for general use
    REJECTED = "rejected"  # Failed safety or review


class RequestStatus(Enum):
    """App request/prompt status."""

    PENDING = "pending"  # Awaiting approval
    APPROVED = "approved"  # Approved for building
    BUILDING = "building"  # Being built by Claude Code
    COMPLETED = "completed"  # Built and in wild west
    REJECTED = "rejected"  # Rejected by reviewers
    FAILED = "failed"  # Build failed


class User(db.Model):
    """User model for authenticated users."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    tier = db.Column(db.Integer, default=UserTier.ANONYMOUS.value, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    apps = db.relationship("App", backref="author", lazy="dynamic")
    reviews = db.relationship("Review", backref="author", lazy="dynamic")
    requests = db.relationship("AppRequest", backref="requester", lazy="dynamic", foreign_keys="AppRequest.requester_id")
    feedback = db.relationship("Feedback", backref="author", lazy="dynamic", foreign_keys="Feedback.author_id")

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Check if user is an admin."""
        return self.tier >= UserTier.ADMIN.value

    def is_promoted(self):
        """Check if user is promoted or higher."""
        return self.tier >= UserTier.PROMOTED.value

    def is_limited(self):
        """Check if user is limited tier or higher (can submit requests)."""
        return self.tier >= UserTier.LIMITED.value

    def to_dict(self, include_email=False):
        """Serialize user to dictionary."""
        data = {
            "id": self.id,
            "username": self.username,
            "tier": self.tier,
            "tier_name": UserTier(self.tier).name.lower(),
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
        }
        if include_email:
            data["email"] = self.email
        return data


class App(db.Model):
    """App package model."""

    __tablename__ = "apps"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    version = db.Column(db.String(20), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    status = db.Column(
        db.String(20), default=AppStatus.PENDING.value, nullable=False, index=True
    )
    package_path = db.Column(db.String(500), nullable=True)
    icon_path = db.Column(db.String(500), nullable=True)
    download_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # AI-generated metadata
    ai_generated = db.Column(db.Boolean, default=False, nullable=False)
    source_request_id = db.Column(
        db.Integer, db.ForeignKey("app_requests.id"), nullable=True
    )

    # Safety check results
    safety_checked = db.Column(db.Boolean, default=False, nullable=False)
    safety_score = db.Column(db.Float, nullable=True)
    safety_notes = db.Column(db.Text, nullable=True)

    # Relationships
    screenshots = db.relationship(
        "Screenshot", backref="app", lazy="dynamic", cascade="all, delete-orphan"
    )
    reviews = db.relationship(
        "Review", backref="app", lazy="dynamic", cascade="all, delete-orphan"
    )
    feedback = db.relationship(
        "Feedback", backref="app", lazy="dynamic", cascade="all, delete-orphan"
    )

    def average_rating(self):
        """Calculate the average rating from reviews."""
        reviews = self.reviews.all()
        if not reviews:
            return None
        return sum(r.rating for r in reviews) / len(reviews)

    def to_dict(self, include_package_path=False):
        """Serialize app to dictionary."""
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "version": self.version,
            "author": self.author.username if self.author else "Anonymous",
            "author_id": self.author_id,
            "category": self.category,
            "status": self.status,
            "icon_path": self.icon_path,
            "download_count": self.download_count,
            "average_rating": self.average_rating(),
            "review_count": self.reviews.count(),
            "ai_generated": self.ai_generated,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "screenshots": [s.to_dict() for s in self.screenshots.all()],
        }
        if include_package_path:
            data["package_path"] = self.package_path
        return data


class Screenshot(db.Model):
    """App screenshot model."""

    __tablename__ = "screenshots"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id"), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(200), nullable=True)
    order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Serialize screenshot to dictionary."""
        return {
            "id": self.id,
            "path": self.path,
            "caption": self.caption,
            "order": self.order,
        }


class Review(db.Model):
    """App review and rating model."""

    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anonymous_id = db.Column(
        db.String(64), nullable=True, index=True
    )  # For anonymous reviews
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    title = db.Column(db.String(100), nullable=True)
    content = db.Column(db.Text, nullable=True)
    upvotes = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self):
        """Serialize review to dictionary."""
        return {
            "id": self.id,
            "app_id": self.app_id,
            "author": self.author.username if self.author else "Anonymous",
            "author_id": self.author_id,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "upvotes": self.upvotes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ReviewVote(db.Model):
    """Vote on a review (to prevent duplicate voting)."""

    __tablename__ = "review_votes"

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(
        db.Integer, db.ForeignKey("reviews.id"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anonymous_id = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("review_id", "user_id", name="unique_user_review_vote"),
        db.UniqueConstraint(
            "review_id", "anonymous_id", name="unique_anonymous_review_vote"
        ),
    )


class AppRequest(db.Model):
    """App request/prompt model for AI-generated apps."""

    __tablename__ = "app_requests"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    prompt = db.Column(db.Text, nullable=False)
    requester_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    status = db.Column(
        db.String(20), default=RequestStatus.PENDING.value, nullable=False, index=True
    )
    upvotes = db.Column(db.Integer, default=0, nullable=False)
    category = db.Column(db.String(50), nullable=True)

    # AI Safety check results
    safety_checked = db.Column(db.Boolean, default=False, nullable=False)
    safety_passed = db.Column(db.Boolean, nullable=True)
    safety_notes = db.Column(db.Text, nullable=True)

    # Approval info
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Build info
    build_started_at = db.Column(db.DateTime, nullable=True)
    build_completed_at = db.Column(db.DateTime, nullable=True)
    build_log = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    approver = db.relationship("User", foreign_keys=[approved_by_id])
    resulting_app = db.relationship(
        "App", backref="source_request", uselist=False, foreign_keys="App.source_request_id"
    )

    def to_dict(self):
        """Serialize request to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "prompt": self.prompt,
            "requester": self.requester.username,
            "requester_id": self.requester_id,
            "status": self.status,
            "upvotes": self.upvotes,
            "category": self.category,
            "safety_checked": self.safety_checked,
            "safety_passed": self.safety_passed,
            "approved_by": self.approver.username if self.approver else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "resulting_app_id": self.resulting_app.id if self.resulting_app else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class RequestVote(db.Model):
    """Vote on an app request (to prevent duplicate voting)."""

    __tablename__ = "request_votes"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(
        db.Integer, db.ForeignKey("app_requests.id"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("request_id", "user_id", name="unique_request_vote"),
    )


class Feedback(db.Model):
    """App feedback/bug report model."""

    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anonymous_id = db.Column(db.String(64), nullable=True, index=True)
    feedback_type = db.Column(
        db.String(20), nullable=False
    )  # bug, suggestion, rebuild_request
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.Integer, default=0, nullable=False)  # 0=low, 1=medium, 2=high

    # For rebuild requests
    triggers_rebuild = db.Column(db.Boolean, default=False, nullable=False)
    rebuild_requested_at = db.Column(db.DateTime, nullable=True)
    rebuild_approved = db.Column(db.Boolean, nullable=True)
    rebuild_approved_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )

    # Log file attachment
    log_file_path = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    rebuild_approver = db.relationship("User", foreign_keys=[rebuild_approved_by_id])

    def to_dict(self):
        """Serialize feedback to dictionary."""
        return {
            "id": self.id,
            "app_id": self.app_id,
            "author": self.author.username if self.author else "Anonymous",
            "author_id": self.author_id,
            "feedback_type": self.feedback_type,
            "title": self.title,
            "content": self.content,
            "priority": self.priority,
            "triggers_rebuild": self.triggers_rebuild,
            "rebuild_approved": self.rebuild_approved,
            "log_file_path": self.log_file_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AppDownload(db.Model):
    """Track app downloads for analytics."""

    __tablename__ = "app_downloads"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anonymous_id = db.Column(db.String(64), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 max length
    user_agent = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AppSubscription(db.Model):
    """User subscription to app updates/new builds."""

    __tablename__ = "app_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    app = db.relationship("App", backref="subscriptions")
    user = db.relationship("User", backref="subscriptions")

    __table_args__ = (
        db.UniqueConstraint("app_id", "user_id", name="unique_app_subscription"),
    )

    def to_dict(self):
        """Serialize subscription to dictionary."""
        return {
            "id": self.id,
            "app_id": self.app_id,
            "app_slug": self.app.slug if self.app else None,
            "app_name": self.app.name if self.app else None,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
        }


class Notification(db.Model):
    """User notification for app updates, builds, etc."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    notification_type = db.Column(db.String(50), nullable=False)  # new_build, app_promoted, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id"), nullable=True)
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", backref="notifications")
    app = db.relationship("App")

    def to_dict(self):
        """Serialize notification to dictionary."""
        return {
            "id": self.id,
            "type": self.notification_type,
            "title": self.title,
            "message": self.message,
            "app_id": self.app_id,
            "app_slug": self.app.slug if self.app else None,
            "read": self.read,
            "created_at": self.created_at.isoformat(),
        }


def init_db(app):
    """Initialize the database with the Flask app."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
