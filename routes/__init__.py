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

"""Routes package for Flick Forge API."""

from .auth import auth_bp
from .apps import apps_bp
from .reviews import reviews_bp
from .requests import requests_bp
from .feedback import feedback_bp
from .admin import admin_bp

__all__ = [
    "auth_bp",
    "apps_bp",
    "reviews_bp",
    "requests_bp",
    "feedback_bp",
    "admin_bp",
]
