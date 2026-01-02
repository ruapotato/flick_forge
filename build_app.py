#!/usr/bin/env python3
# Flick Forge - Flick Store Backend
# Copyright (C) 2025 Flick Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
Flick App Builder - Invokes Claude Code to build apps from requests.

Usage:
    python build_app.py <request_id>
    python build_app.py --list-pending
    python build_app.py --build-next

This script:
1. Creates a temp build directory
2. Sets up CLAUDE.md with build instructions
3. Invokes `claude` CLI to generate the app
4. Packages result into .flick format
5. Updates database with build status
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import zipfile
import re
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, AppRequest, App, AppStatus, RequestStatus, UserTier


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:50]


def log(message, build_log=None):
    """Log message to console and optionally to build log."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    if build_log is not None:
        build_log.append(line)


def create_claude_md(build_dir, request):
    """Create CLAUDE.md with build instructions."""

    claude_md = f"""# Flick App Build Task

## App Request
- **Title**: {request.title}
- **Category**: {request.category or 'utility'}
- **Request ID**: {request.id}

## User Prompt
{request.prompt}

## Your Task
Build a complete Flick app based on the user's request above.

## Reference Template
See templates/app_templates/audiobook-player/ for a complete example of a Flick app structure.

## Flick App Structure
Create the following files:

### 1. manifest.json (required)
```json
{{
  "format_version": 1,
  "id": "com.flick.{slugify(request.title)}",
  "name": "{request.title}",
  "version": "1.0.0",
  "description": "Brief description here",
  "author": {{
    "name": "AI Generated",
    "email": "ai@255.one"
  }},
  "license": "AGPL-3.0",
  "categories": ["{request.category or 'Utility'}"],
  "app": {{
    "type": "qml",
    "entry": "main.qml",
    "min_flick_version": "1.0.0"
  }},
  "permissions": [],
  "ai_generated": {{
    "is_ai_generated": true,
    "generator_version": "claude-code",
    "original_prompt": "See request",
    "generation_date": "{datetime.utcnow().isoformat()}Z"
  }},
  "store": {{
    "maturity_rating": "everyone",
    "price": "free",
    "testing_status": "wild_west"
  }}
}}
```

### 2. app/main.qml (required)
The main QML entry point. Use Qt 5.15 / QtQuick 2.15.

Example structure:
```qml
import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Window {{
    id: root
    visible: true
    width: 1080
    height: 2400
    title: "{request.title}"
    color: "#0a0a0f"

    // Your app content here
}}
```

### 3. icon.svg or icon.png (required)
Create a simple SVG icon for the app.

## Design Guidelines
- Use dark theme (background: #0a0a0f, text: #ffffff)
- Accent color: #6366f1 (indigo)
- Mobile-first design (1080x2400 reference)
- Large touch targets (min 48px)
- Clean, modern UI

## Important
- All code must be AGPL-3.0 licensed
- No external network calls unless essential
- Handle errors gracefully
- Include helpful comments

## Output Files
Create all files in the current directory:
- manifest.json
- app/main.qml (and any additional .qml files)
- icon.svg

Start building now!
"""

    claude_path = os.path.join(build_dir, "CLAUDE.md")
    with open(claude_path, "w") as f:
        f.write(claude_md)

    return claude_path


def create_default_icon(build_dir, title):
    """Create a simple default SVG icon."""
    # Get first letter of title
    letter = title[0].upper() if title else "A"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="48" fill="#6366f1"/>
  <text x="128" y="170" font-family="Arial, sans-serif" font-size="140"
        font-weight="bold" fill="white" text-anchor="middle">{letter}</text>
</svg>'''

    icon_path = os.path.join(build_dir, "icon.svg")
    with open(icon_path, "w") as f:
        f.write(svg)

    return icon_path


def run_claude_build(build_dir, build_log):
    """Run Claude Code to build the app."""
    log("Starting Claude Code build...", build_log)

    # Find claude binary
    claude_paths = [
        "/usr/local/bin/claude",
        "/root/.local/bin/claude",
        "claude"
    ]

    claude_bin = None
    for path in claude_paths:
        if os.path.exists(path):
            claude_bin = path
            break

    if not claude_bin:
        log("ERROR: Claude CLI not found", build_log)
        return False

    # Build the claude command - use --print for non-interactive mode
    prompt = "Read CLAUDE.md and build the complete Flick app as specified. Create all required files: manifest.json, app/main.qml, and icon.svg. Output the files directly, do not ask questions."

    # Check if running as root - need to use sudo to run as flick user
    is_root = os.geteuid() == 0

    if is_root:
        log("Running as root, will use sudo to run as 'flick' user", build_log)
        # Make build directory accessible to flick user
        os.chmod(build_dir, 0o777)
        for root, dirs, files in os.walk(build_dir):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o777)
            for f in files:
                os.chmod(os.path.join(root, f), 0o666)

        # Use sudo to run as flick user with dangerously-skip-permissions
        cmd = [
            "sudo", "-u", "flick",
            claude_bin,
            "--print",
            "--dangerously-skip-permissions",
            prompt
        ]
        log(f"Running: sudo -u flick {claude_bin} --print --dangerously-skip-permissions", build_log)
    else:
        cmd = [
            claude_bin,
            "--print",
            "--dangerously-skip-permissions",
            prompt
        ]
        log(f"Running: {claude_bin} --print --dangerously-skip-permissions", build_log)

    try:
        result = subprocess.run(
            cmd,
            cwd=build_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env={**os.environ, "ANTHROPIC_MODEL": "claude-sonnet-4-20250514"}
        )

        log(f"Claude exit code: {result.returncode}", build_log)

        if result.stdout:
            log("=== Claude Output ===", build_log)
            for line in result.stdout.split("\n")[:100]:  # Limit output
                log(line, build_log)

        if result.stderr:
            log("=== Claude Errors ===", build_log)
            for line in result.stderr.split("\n")[:50]:
                log(line, build_log)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        log("ERROR: Claude build timed out after 5 minutes", build_log)
        return False
    except FileNotFoundError:
        log("ERROR: 'claude' command not found. Install Claude Code CLI.", build_log)
        return False
    except Exception as e:
        log(f"ERROR: Build failed: {e}", build_log)
        return False


def validate_build(build_dir, build_log):
    """Validate that required files were created."""
    required_files = [
        "manifest.json",
        "app/main.qml",
    ]

    missing = []
    for f in required_files:
        path = os.path.join(build_dir, f)
        if not os.path.exists(path):
            missing.append(f)

    if missing:
        log(f"ERROR: Missing required files: {missing}", build_log)
        return False

    # Validate manifest.json
    try:
        with open(os.path.join(build_dir, "manifest.json")) as f:
            manifest = json.load(f)
        if "name" not in manifest or "app" not in manifest:
            log("ERROR: manifest.json missing required fields", build_log)
            return False
    except json.JSONDecodeError as e:
        log(f"ERROR: Invalid manifest.json: {e}", build_log)
        return False

    log("Build validation passed!", build_log)
    return True


def package_app(build_dir, output_path, build_log):
    """Package the build into a .flick file."""
    log(f"Packaging app to {output_path}...", build_log)

    try:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(build_dir):
                # Skip CLAUDE.md and other build artifacts
                if "CLAUDE.md" in files:
                    files.remove("CLAUDE.md")

                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, build_dir)
                    zf.write(file_path, arc_name)
                    log(f"  Added: {arc_name}", build_log)

        log(f"Package created: {output_path}", build_log)
        return True
    except Exception as e:
        log(f"ERROR: Packaging failed: {e}", build_log)
        return False


def build_request(request_id):
    """Build an app from a request ID."""
    build_log = []

    with app.app_context():
        # Get the request
        request = AppRequest.query.get(request_id)
        if not request:
            log(f"ERROR: Request {request_id} not found", build_log)
            return False, "\n".join(build_log)

        if request.status != RequestStatus.APPROVED.value:
            log(f"ERROR: Request {request_id} is not approved (status: {request.status})", build_log)
            return False, "\n".join(build_log)

        log(f"Building request #{request_id}: {request.title}", build_log)

        # Update status to building
        request.status = RequestStatus.BUILDING.value
        request.build_started_at = datetime.utcnow()
        db.session.commit()

        # Create temp build directory
        build_dir = tempfile.mkdtemp(prefix=f"flick_build_{request_id}_")
        log(f"Build directory: {build_dir}", build_log)

        try:
            # Create app subdirectory
            os.makedirs(os.path.join(build_dir, "app"), exist_ok=True)

            # Create CLAUDE.md
            create_claude_md(build_dir, request)
            log("Created CLAUDE.md with build instructions", build_log)

            # Create default icon (Claude can overwrite it)
            create_default_icon(build_dir, request.title)
            log("Created default icon", build_log)

            # Run Claude Code build
            if not run_claude_build(build_dir, build_log):
                request.status = RequestStatus.FAILED.value
                request.build_log = "\n".join(build_log)
                db.session.commit()
                return False, "\n".join(build_log)

            # Validate the build
            if not validate_build(build_dir, build_log):
                request.status = RequestStatus.FAILED.value
                request.build_log = "\n".join(build_log)
                db.session.commit()
                return False, "\n".join(build_log)

            # Generate slug and package name
            slug = slugify(request.title)
            base_slug = slug
            counter = 1
            while App.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1

            # Package the app
            packages_dir = os.path.join(os.path.dirname(__file__), "static", "packages")
            os.makedirs(packages_dir, exist_ok=True)
            package_filename = f"{slug}-1.0.0.flick"
            package_path = os.path.join(packages_dir, package_filename)

            if not package_app(build_dir, package_path, build_log):
                request.status = RequestStatus.FAILED.value
                request.build_log = "\n".join(build_log)
                db.session.commit()
                return False, "\n".join(build_log)

            # Read manifest for app details
            with open(os.path.join(build_dir, "manifest.json")) as f:
                manifest = json.load(f)

            # Create the App entry
            new_app = App(
                name=manifest.get("name", request.title),
                slug=slug,
                description=manifest.get("description", request.prompt[:500]),
                version="1.0.0",
                author_id=request.requester_id,
                category=request.category or "utility",
                status=AppStatus.WILD_WEST.value,
                package_path=f"/static/packages/{package_filename}",
                ai_generated=True,
                source_request_id=request.id,
            )
            db.session.add(new_app)

            # Update request status
            request.status = RequestStatus.COMPLETED.value
            request.build_completed_at = datetime.utcnow()
            request.build_log = "\n".join(build_log)

            db.session.commit()

            log(f"SUCCESS! App '{new_app.name}' created with slug '{slug}'", build_log)
            log(f"App is now in Wild West for testing", build_log)

            # Notify subscribers if this is a rebuild (app already existed)
            try:
                from routes.subscriptions import notify_subscribers_of_new_build
                notified = notify_subscribers_of_new_build(new_app, new_app.version)
                if notified > 0:
                    log(f"Notified {notified} subscribers of new build", build_log)
            except Exception as e:
                log(f"Warning: Failed to notify subscribers: {e}", build_log)

            return True, "\n".join(build_log)

        finally:
            # Cleanup build directory
            try:
                shutil.rmtree(build_dir)
                log(f"Cleaned up build directory", build_log)
            except Exception as e:
                log(f"Warning: Failed to cleanup build dir: {e}", build_log)


def list_pending():
    """List all approved requests waiting to be built."""
    with app.app_context():
        requests = AppRequest.query.filter_by(status=RequestStatus.APPROVED.value).all()

        if not requests:
            print("No approved requests waiting to be built.")
            return

        print(f"\n{'ID':<6} {'Title':<30} {'Category':<15} {'Requested By':<20}")
        print("-" * 75)
        for req in requests:
            user = req.requester.username if req.requester else "Unknown"
            print(f"{req.id:<6} {req.title[:28]:<30} {(req.category or 'other')[:13]:<15} {user[:18]:<20}")
        print()


def build_next():
    """Build the next approved request."""
    with app.app_context():
        request = AppRequest.query.filter_by(
            status=RequestStatus.APPROVED.value
        ).order_by(AppRequest.created_at.asc()).first()

        if not request:
            print("No approved requests to build.")
            return

        print(f"Building next request: #{request.id} - {request.title}")
        success, log = build_request(request.id)

        if success:
            print("\n=== BUILD SUCCESSFUL ===")
        else:
            print("\n=== BUILD FAILED ===")

        print("\nFull build log saved to database.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python build_app.py <request_id>    - Build specific request")
        print("  python build_app.py --list-pending  - List approved requests")
        print("  python build_app.py --build-next    - Build next approved request")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--list-pending":
        list_pending()
    elif arg == "--build-next":
        build_next()
    else:
        try:
            request_id = int(arg)
            success, log = build_request(request_id)
            sys.exit(0 if success else 1)
        except ValueError:
            print(f"Invalid request ID: {arg}")
            sys.exit(1)
