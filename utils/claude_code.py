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

"""
Claude Code Integration for Flick Forge.

This module provides integration with Claude Code for building apps
from user prompts. Currently implemented as stubs that can be connected
to Claude Code when ready.

The build process:
1. Receive approved app request with prompt
2. Send prompt to Claude Code with Flick SDK context
3. Monitor build progress
4. Receive generated code and assets
5. Package into .flick format
6. Run safety checks on generated code
7. Create App entry and move to Wild West
"""

import os
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable


class BuildStatus(Enum):
    """Status of a build job."""

    QUEUED = "queued"
    STARTING = "starting"
    GENERATING = "generating"
    PACKAGING = "packaging"
    CHECKING = "checking"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BuildResult:
    """Result of a build job."""

    status: BuildStatus
    app_slug: Optional[str] = None
    package_path: Optional[str] = None
    build_log: str = ""
    error_message: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "app_slug": self.app_slug,
            "package_path": self.package_path,
            "build_log": self.build_log,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class BuildJob:
    """A build job for Claude Code."""

    id: str
    request_id: int
    prompt: str
    category: Optional[str]
    status: BuildStatus = BuildStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[BuildResult] = None
    progress_callback: Optional[Callable] = None


class ClaudeCodeBuilder:
    """
    Claude Code integration for building Flick apps.

    This class manages the process of:
    1. Sending prompts to Claude Code
    2. Monitoring build progress
    3. Receiving and packaging generated code
    4. Running safety checks
    5. Creating App entries

    STUB: Most methods are placeholders for actual Claude Code integration.

    Usage:
        builder = ClaudeCodeBuilder(config)
        job = builder.create_build_job(request_id, prompt, category)
        builder.start_build(job.id)

        # Check status
        status = builder.get_build_status(job.id)

        # When complete
        result = builder.get_build_result(job.id)
    """

    # System prompt for Claude Code to understand Flick app requirements
    FLICK_SYSTEM_PROMPT = """
You are building a Flick app - a lightweight application for the Flick operating system.

Flick apps should:
1. Be self-contained with minimal dependencies
2. Follow the Flick SDK patterns
3. Include a manifest.json with app metadata
4. Use the Flick UI toolkit for consistent look and feel
5. Handle errors gracefully
6. Be accessible and keyboard-navigable

The generated app will be packaged as a .flick file and distributed through
the Flick Store.

Please generate clean, well-documented code that follows best practices.
"""

    def __init__(self, config=None):
        """
        Initialize the Claude Code builder.

        Args:
            config: Optional configuration dictionary with:
                - claude_code_endpoint: URL for Claude Code API
                - claude_code_enabled: Whether Claude Code is available
                - claude_code_api_key: API key for Claude Code
                - packages_dir: Directory for generated packages
        """
        self.config = config or {}
        self.enabled = self.config.get("CLAUDE_CODE_ENABLED", False)
        self.endpoint = self.config.get("CLAUDE_CODE_ENDPOINT")
        self.packages_dir = self.config.get("UPLOAD_FOLDER", "static/packages")

        # In-memory job storage (use Redis/database in production)
        self._jobs: dict[str, BuildJob] = {}

    def create_build_job(
        self,
        request_id: int,
        prompt: str,
        category: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> BuildJob:
        """
        Create a new build job.

        Args:
            request_id: ID of the AppRequest
            prompt: The user's app prompt
            category: Optional app category
            progress_callback: Optional callback for progress updates

        Returns:
            BuildJob instance
        """
        job_id = self._generate_job_id(request_id, prompt)

        job = BuildJob(
            id=job_id,
            request_id=request_id,
            prompt=prompt,
            category=category,
            progress_callback=progress_callback,
        )

        self._jobs[job_id] = job
        return job

    def start_build(self, job_id: str) -> bool:
        """
        Start a build job.

        STUB: In production, this would send the job to Claude Code.

        Args:
            job_id: The job ID to start

        Returns:
            True if started successfully
        """
        job = self._jobs.get(job_id)
        if not job:
            return False

        job.status = BuildStatus.STARTING
        job.started_at = datetime.utcnow()

        if self.enabled and self.endpoint:
            # STUB: Send to Claude Code
            # self._send_to_claude_code(job)
            pass
        else:
            # Simulate build for development
            self._simulate_build(job)

        return True

    def get_build_status(self, job_id: str) -> Optional[BuildStatus]:
        """
        Get the current status of a build job.

        Args:
            job_id: The job ID to check

        Returns:
            BuildStatus or None if job not found
        """
        job = self._jobs.get(job_id)
        return job.status if job else None

    def get_build_result(self, job_id: str) -> Optional[BuildResult]:
        """
        Get the result of a completed build job.

        Args:
            job_id: The job ID

        Returns:
            BuildResult or None
        """
        job = self._jobs.get(job_id)
        return job.result if job else None

    def cancel_build(self, job_id: str) -> bool:
        """
        Cancel a running build job.

        Args:
            job_id: The job ID to cancel

        Returns:
            True if cancelled successfully
        """
        job = self._jobs.get(job_id)
        if not job or job.status in [BuildStatus.COMPLETED, BuildStatus.FAILED]:
            return False

        job.status = BuildStatus.FAILED
        job.result = BuildResult(
            status=BuildStatus.FAILED,
            error_message="Build cancelled by user",
        )
        return True

    def _generate_job_id(self, request_id: int, prompt: str) -> str:
        """Generate a unique job ID."""
        data = f"{request_id}:{prompt}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _simulate_build(self, job: BuildJob):
        """
        Simulate a build for development/testing.

        This creates a minimal .flick package structure.
        """
        job.status = BuildStatus.GENERATING
        self._notify_progress(job, "Generating app code...")

        # Create a minimal app structure
        app_name = f"app_{job.request_id}"
        app_slug = app_name.lower().replace(" ", "-")

        # Simulated generated code
        manifest = {
            "name": app_name,
            "version": "1.0.0",
            "description": job.prompt[:200],
            "category": job.category or "other",
            "author": "AI Generated",
            "ai_generated": True,
            "source_request_id": job.request_id,
        }

        job.status = BuildStatus.PACKAGING
        self._notify_progress(job, "Packaging app...")

        # In a real implementation, we would:
        # 1. Create actual app files from Claude Code output
        # 2. Package them into a .flick archive
        # 3. Run safety checks

        # For now, just mark as complete with a placeholder
        job.status = BuildStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.result = BuildResult(
            status=BuildStatus.COMPLETED,
            app_slug=app_slug,
            package_path=None,  # No actual package in simulation
            build_log=(
                f"Build job {job.id} simulated.\n"
                f"Prompt: {job.prompt[:100]}...\n"
                "Note: Claude Code integration not yet implemented."
            ),
            duration_seconds=(job.completed_at - job.started_at).total_seconds(),
        )

        self._notify_progress(job, "Build complete (simulated)")

    def _send_to_claude_code(self, job: BuildJob):
        """
        Send a build job to Claude Code.

        STUB: This method would integrate with Claude Code's API.
        """
        # Example implementation:
        #
        # full_prompt = f"{self.FLICK_SYSTEM_PROMPT}\n\nUser request:\n{job.prompt}"
        #
        # response = requests.post(
        #     f"{self.endpoint}/build",
        #     headers={
        #         "Authorization": f"Bearer {self.config['CLAUDE_CODE_API_KEY']}",
        #         "Content-Type": "application/json",
        #     },
        #     json={
        #         "prompt": full_prompt,
        #         "job_id": job.id,
        #         "callback_url": f"{self.config['BASE_URL']}/api/admin/build-callback",
        #     },
        #     timeout=30,
        # )
        #
        # if response.ok:
        #     job.status = BuildStatus.GENERATING
        # else:
        #     job.status = BuildStatus.FAILED
        #     job.result = BuildResult(
        #         status=BuildStatus.FAILED,
        #         error_message=f"Claude Code error: {response.text}",
        #     )
        pass

    def _notify_progress(self, job: BuildJob, message: str):
        """Send progress update via callback if available."""
        if job.progress_callback:
            try:
                job.progress_callback(job.id, job.status.value, message)
            except Exception:
                pass  # Don't fail build due to callback error

    def handle_build_callback(self, job_id: str, data: dict) -> bool:
        """
        Handle callback from Claude Code when build completes.

        STUB: This would process the build results from Claude Code.

        Args:
            job_id: The job ID
            data: Callback data containing generated code/package

        Returns:
            True if handled successfully
        """
        job = self._jobs.get(job_id)
        if not job:
            return False

        # Process the callback data
        # - Extract generated files
        # - Run safety checks
        # - Package into .flick
        # - Update job status

        return True


def build_app_from_request(request_id: int, prompt: str, config: dict = None) -> dict:
    """
    Convenience function to build an app from a request.

    STUB: This would start an async build job.

    Args:
        request_id: The AppRequest ID
        prompt: The user's prompt
        config: Optional configuration

    Returns:
        Dictionary with job info
    """
    builder = ClaudeCodeBuilder(config)
    job = builder.create_build_job(request_id, prompt)
    builder.start_build(job.id)

    return {
        "job_id": job.id,
        "status": job.status.value,
        "message": "Build job started",
    }
