# Flick Forge - Flick Store Backend
# Copyright (C) 2025 Flick Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Seed the database with Flick apps from the apps directory."""

import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, App, AppStatus, User, UserTier


# Flick apps with their metadata - these are the real QML apps
FLICK_APPS = [
    {
        "name": "Music Player",
        "slug": "music",
        "description": "A beautiful Qt/QML music player for Flick. Browse your music library, create playlists, and enjoy your favorite tracks with a modern mobile-first interface.",
        "version": "1.0.0",
        "category": "multimedia",
        "icon": "music-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 1250,
    },
    {
        "name": "eBook Reader",
        "slug": "ebooks",
        "description": "Read your favorite books with this elegant eBook reader. Supports EPUB format with customizable fonts, themes, and reading progress tracking.",
        "version": "1.0.0",
        "category": "productivity",
        "icon": "ebooks-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 890,
    },
    {
        "name": "Audiobook Player",
        "slug": "audiobooks",
        "description": "Listen to audiobooks on the go. Features chapter navigation, playback speed control, sleep timer, and automatic position saving.",
        "version": "1.0.0",
        "category": "multimedia",
        "icon": "audiobooks-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 720,
    },
    {
        "name": "Sandbox",
        "slug": "sandbox",
        "description": "A fun falling sand simulation game. Draw with different materials like sand, water, and fire and watch them interact with realistic physics.",
        "version": "1.0.0",
        "category": "games",
        "icon": "sandbox-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 2100,
    },
    {
        "name": "Calculator",
        "slug": "calculator",
        "description": "A sleek calculator app with standard and scientific modes. Perfect for quick calculations on your Flick device.",
        "version": "1.0.0",
        "category": "utilities",
        "icon": "calculator-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 3400,
    },
    {
        "name": "Calendar",
        "slug": "calendar",
        "description": "Stay organized with this Qt/QML calendar app. View your schedule, add events, and never miss an important date.",
        "version": "1.0.0",
        "category": "productivity",
        "icon": "calendar-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 1800,
    },
    {
        "name": "Clock",
        "slug": "clock",
        "description": "Alarm clock, timer, and stopwatch all in one. Set multiple alarms and track time with a beautiful interface.",
        "version": "1.0.0",
        "category": "utilities",
        "icon": "clock-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 2900,
    },
    {
        "name": "Contacts",
        "slug": "contacts",
        "description": "Manage your contacts with ease. Store phone numbers, emails, and organize your address book.",
        "version": "1.0.0",
        "category": "productivity",
        "icon": "contacts-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 1500,
    },
    {
        "name": "Files",
        "slug": "files",
        "description": "Browse and manage files on your device. Navigate folders, copy, move, and organize your data.",
        "version": "1.0.0",
        "category": "utilities",
        "icon": "files-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 4200,
    },
    {
        "name": "Notes",
        "slug": "notes",
        "description": "Quick and simple note-taking app. Jot down ideas, make lists, and keep your thoughts organized.",
        "version": "1.0.0",
        "category": "productivity",
        "icon": "notes-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 2600,
    },
    {
        "name": "Weather",
        "slug": "weather",
        "description": "Check the weather forecast with a beautiful Qt interface. See current conditions and multi-day forecasts.",
        "version": "1.0.0",
        "category": "utilities",
        "icon": "weather-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 3100,
    },
    {
        "name": "Photos",
        "slug": "photos",
        "description": "View and organize your photo gallery. Browse images with smooth animations and gestures.",
        "version": "1.0.0",
        "category": "multimedia",
        "icon": "photos-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 2800,
    },
    {
        "name": "Video Player",
        "slug": "video",
        "description": "Watch videos with this Qt multimedia player. Supports common formats with playback controls.",
        "version": "1.0.0",
        "category": "multimedia",
        "icon": "video-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 1900,
    },
    {
        "name": "Web Browser",
        "slug": "web",
        "description": "Browse the web with this lightweight Qt WebEngine browser. Fast and mobile-optimized.",
        "version": "1.0.0",
        "category": "internet",
        "icon": "web-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 5200,
    },
    {
        "name": "Maps",
        "slug": "maps",
        "description": "Navigate with Qt Location. View maps, search for places, and get directions.",
        "version": "1.0.0",
        "category": "utilities",
        "icon": "maps-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 1700,
    },
    {
        "name": "Podcasts",
        "slug": "podcast",
        "description": "Subscribe to and listen to your favorite podcasts. Download episodes for offline listening.",
        "version": "1.0.0",
        "category": "multimedia",
        "icon": "podcast-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 980,
    },
    {
        "name": "Voice Recorder",
        "slug": "recorder",
        "description": "Record audio notes and voice memos. Simple interface for capturing sounds on the go.",
        "version": "1.0.0",
        "category": "utilities",
        "icon": "recorder-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 1100,
    },
    {
        "name": "Terminal",
        "slug": "terminal",
        "description": "Access the command line with this Qt terminal emulator. Full shell access for power users.",
        "version": "1.0.0",
        "category": "development",
        "icon": "terminal-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 4800,
    },
    {
        "name": "Settings",
        "slug": "settings",
        "description": "Configure your Flick device. Adjust display, sound, network, and system preferences.",
        "version": "1.0.0",
        "category": "system",
        "icon": "settings-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 6000,
    },
    {
        "name": "Messages",
        "slug": "messages",
        "description": "Send and receive SMS messages. Modern chat-style interface for text communication.",
        "version": "1.0.0",
        "category": "communication",
        "icon": "messages-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 3800,
    },
    {
        "name": "Phone",
        "slug": "phone",
        "description": "Make and receive phone calls with this dialer app. Call history and contact integration.",
        "version": "1.0.0",
        "category": "communication",
        "icon": "phone-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 5500,
    },
    {
        "name": "Email",
        "slug": "email",
        "description": "Read and send emails. Supports IMAP/SMTP with a clean mobile-first interface.",
        "version": "1.0.0",
        "category": "communication",
        "icon": "email-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 2200,
    },
    {
        "name": "Password Safe",
        "slug": "passwordsafe",
        "description": "Securely store your passwords and sensitive data. Encrypted local storage for your credentials.",
        "version": "1.0.0",
        "category": "security",
        "icon": "passwordsafe-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 1400,
    },
    {
        "name": "Distract",
        "slug": "distract",
        "description": "A fun distraction game to pass the time. Simple but addictive Qt game.",
        "version": "1.0.0",
        "category": "games",
        "icon": "distract-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 1600,
    },
    {
        "name": "Welcome",
        "slug": "welcome",
        "description": "Welcome to Flick! An introduction app to help you get started with your new mobile shell.",
        "version": "1.0.0",
        "category": "system",
        "icon": "welcome-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 8000,
    },
    {
        "name": "Flick Store",
        "slug": "store",
        "description": "Browse, discover, and install Flick apps. The official app store client for Flick.",
        "version": "1.0.0",
        "category": "system",
        "icon": "store-icon.png",
        "status": AppStatus.STABLE.value,
        "download_count": 7500,
    },
]


def seed_database():
    """Seed the database with Flick apps."""
    with app.app_context():
        # Check if we already have apps
        existing_count = App.query.count()
        if existing_count > 0:
            print(f"Database already has {existing_count} apps. Clearing and reseeding...")
            App.query.delete()
            db.session.commit()

        # Get or create a system user for the apps
        system_user = User.query.filter_by(username="flick").first()
        if not system_user:
            system_user = User(
                username="flick",
                email="apps@flick.local",
                tier=UserTier.ADMIN.value,
            )
            system_user.set_password("FlickSystemUser2025!")
            db.session.add(system_user)
            db.session.commit()
            print("Created 'flick' system user")

        # Add all Flick apps
        for app_data in FLICK_APPS:
            app_obj = App(
                name=app_data["name"],
                slug=app_data["slug"],
                description=app_data["description"],
                version=app_data["version"],
                category=app_data["category"],
                status=app_data["status"],
                download_count=app_data["download_count"],
                author_id=system_user.id,
                ai_generated=False,
                safety_checked=True,
                safety_score=1.0,
            )
            db.session.add(app_obj)
            print(f"Added: {app_data['name']}")

        db.session.commit()
        print(f"\nSeeded {len(FLICK_APPS)} Flick apps successfully!")

        # Print category summary
        from sqlalchemy import func
        categories = db.session.query(
            App.category, func.count(App.id)
        ).group_by(App.category).all()

        print("\nCategories:")
        for cat, count in sorted(categories):
            print(f"  {cat}: {count} apps")


if __name__ == "__main__":
    seed_database()
