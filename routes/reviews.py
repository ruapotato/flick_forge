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

"""Reviews and ratings routes for Flick Forge."""

from flask import Blueprint, request, jsonify
from models import db, App, Review, ReviewVote, AppStatus
from routes.auth import get_current_user, get_anonymous_id, login_required

reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/reviews")


def validate_rating(rating):
    """Validate rating is between 1 and 5."""
    try:
        rating = int(rating)
        return 1 <= rating <= 5
    except (TypeError, ValueError):
        return False


@reviews_bp.route("/app/<slug>", methods=["GET"])
def list_reviews(slug):
    """List all reviews for an app."""
    app = App.query.filter_by(slug=slug).first()
    if not app:
        return jsonify({"error": "App not found"}), 404

    # Check if app is visible
    if app.status not in [AppStatus.STABLE.value, AppStatus.WILD_WEST.value]:
        user = get_current_user()
        if not user or not user.is_admin():
            return jsonify({"error": "App not found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    sort_by = request.args.get("sort", "created_at")  # created_at, rating, upvotes

    query = Review.query.filter_by(app_id=app.id)

    # Sorting
    if sort_by == "rating":
        query = query.order_by(Review.rating.desc())
    elif sort_by == "upvotes":
        query = query.order_by(Review.upvotes.desc())
    else:
        query = query.order_by(Review.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Calculate rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = Review.query.filter_by(app_id=app.id, rating=i).count()

    return jsonify(
        {
            "app_slug": slug,
            "reviews": [review.to_dict() for review in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
            "average_rating": app.average_rating(),
            "rating_distribution": rating_distribution,
        }
    )


@reviews_bp.route("/app/<slug>", methods=["POST"])
def create_review(slug):
    """Create a review for an app (anonymous users allowed)."""
    app = App.query.filter_by(slug=slug).first()
    if not app:
        return jsonify({"error": "App not found"}), 404

    # Check if app is reviewable
    if app.status not in [AppStatus.STABLE.value, AppStatus.WILD_WEST.value]:
        return jsonify({"error": "App is not available for review"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    rating = data.get("rating")
    if not validate_rating(rating):
        return jsonify({"error": "Rating must be between 1 and 5"}), 400

    title = data.get("title", "").strip()[:100]  # Max 100 chars
    content = data.get("content", "").strip()[:2000]  # Max 2000 chars

    user = get_current_user()
    anonymous_id = get_anonymous_id() if not user else None

    # Check if user/anonymous has already reviewed this app
    if user:
        existing_review = Review.query.filter_by(
            app_id=app.id, author_id=user.id
        ).first()
    else:
        existing_review = Review.query.filter_by(
            app_id=app.id, anonymous_id=anonymous_id
        ).first()

    if existing_review:
        return jsonify({"error": "You have already reviewed this app"}), 409

    # Create review
    review = Review(
        app_id=app.id,
        author_id=user.id if user else None,
        anonymous_id=anonymous_id,
        rating=int(rating),
        title=title if title else None,
        content=content if content else None,
    )

    db.session.add(review)
    db.session.commit()

    return jsonify({"message": "Review created", "review": review.to_dict()}), 201


@reviews_bp.route("/<int:review_id>", methods=["GET"])
def get_review(review_id):
    """Get a specific review."""
    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    return jsonify({"review": review.to_dict()})


@reviews_bp.route("/<int:review_id>", methods=["PATCH"])
@login_required
def update_review(review_id):
    """Update a review (author only)."""
    user = get_current_user()
    review = Review.query.get(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Only the author can update (not anonymous reviews)
    if review.author_id != user.id:
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "rating" in data:
        if not validate_rating(data["rating"]):
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
        review.rating = int(data["rating"])

    if "title" in data:
        review.title = data["title"].strip()[:100] or None

    if "content" in data:
        review.content = data["content"].strip()[:2000] or None

    db.session.commit()
    return jsonify({"message": "Review updated", "review": review.to_dict()})


@reviews_bp.route("/<int:review_id>", methods=["DELETE"])
@login_required
def delete_review(review_id):
    """Delete a review (author or admin only)."""
    user = get_current_user()
    review = Review.query.get(review_id)

    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Only author or admin can delete
    if review.author_id != user.id and not user.is_admin():
        return jsonify({"error": "Permission denied"}), 403

    db.session.delete(review)
    db.session.commit()

    return jsonify({"message": "Review deleted"})


@reviews_bp.route("/<int:review_id>/vote", methods=["POST"])
def upvote_review(review_id):
    """Upvote a review (anonymous users allowed)."""
    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    user = get_current_user()
    anonymous_id = get_anonymous_id() if not user else None

    # Check if already voted
    if user:
        existing_vote = ReviewVote.query.filter_by(
            review_id=review_id, user_id=user.id
        ).first()
    else:
        existing_vote = ReviewVote.query.filter_by(
            review_id=review_id, anonymous_id=anonymous_id
        ).first()

    if existing_vote:
        return jsonify({"error": "Already voted on this review"}), 409

    # Create vote
    vote = ReviewVote(
        review_id=review_id,
        user_id=user.id if user else None,
        anonymous_id=anonymous_id,
    )

    db.session.add(vote)
    review.upvotes += 1
    db.session.commit()

    return jsonify({"message": "Vote recorded", "upvotes": review.upvotes})


@reviews_bp.route("/<int:review_id>/vote", methods=["DELETE"])
def remove_vote(review_id):
    """Remove upvote from a review."""
    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    user = get_current_user()
    anonymous_id = get_anonymous_id() if not user else None

    # Find the vote
    if user:
        vote = ReviewVote.query.filter_by(
            review_id=review_id, user_id=user.id
        ).first()
    else:
        vote = ReviewVote.query.filter_by(
            review_id=review_id, anonymous_id=anonymous_id
        ).first()

    if not vote:
        return jsonify({"error": "Vote not found"}), 404

    db.session.delete(vote)
    review.upvotes = max(0, review.upvotes - 1)
    db.session.commit()

    return jsonify({"message": "Vote removed", "upvotes": review.upvotes})


@reviews_bp.route("/user/<username>", methods=["GET"])
def get_user_reviews(username):
    """Get all reviews by a user."""
    from models import User

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    pagination = (
        Review.query.filter_by(author_id=user.id)
        .order_by(Review.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify(
        {
            "username": username,
            "reviews": [review.to_dict() for review in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )


@reviews_bp.route("/my-reviews", methods=["GET"])
def get_my_reviews():
    """Get reviews by the current user or anonymous ID."""
    user = get_current_user()

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    if user:
        query = Review.query.filter_by(author_id=user.id)
    else:
        anonymous_id = get_anonymous_id()
        query = Review.query.filter_by(anonymous_id=anonymous_id)

    pagination = query.order_by(Review.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "reviews": [review.to_dict() for review in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
        }
    )
