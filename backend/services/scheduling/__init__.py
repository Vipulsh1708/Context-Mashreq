"""Workflow scheduling service using APScheduler."""

import os

from .scheduler_service import WorkflowSchedulerService

scheduler_service = WorkflowSchedulerService()


def is_scheduling_enabled() -> bool:
    """Single source of truth for the workflow scheduling feature toggle.

    Controlled via the `SCHEDULING_ENABLED` environment variable (default: disabled).
    Flip it to "true" (and restart the backend) to bring the feature back online
    without touching any scheduling code.
    """
    return os.getenv("SCHEDULING_ENABLED", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


__all__ = ["WorkflowSchedulerService", "scheduler_service", "is_scheduling_enabled"] output of 1st