"""Workflow scheduler service using APScheduler with MemoryJobStore.

Manages cron-based scheduling for published workflows. Schedules are
persisted in the published_workflows table and loaded into APScheduler
on startup.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.api.http_execution.utils.constants import sanitize_graph_name

logger = logging.getLogger(__name__)
LOG_PREFIX = "[SCHEDULER]"


class WorkflowSchedulerService:
    """Manages cron-based scheduling for published workflows."""

    def __init__(self):
        self._scheduler: Optional[BackgroundScheduler] = None

    def initialize(self):
        """Start APScheduler with MemoryJobStore and load active schedules from DB."""
        self._scheduler = BackgroundScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            }
        )
        self._scheduler.start()
        logger.info("%s APScheduler started", LOG_PREFIX)
        self._load_active_schedules()

    def shutdown(self):
        """Graceful shutdown of the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            logger.info("%s APScheduler shutdown complete", LOG_PREFIX)

    def _load_active_schedules(self):
        """Query published_workflows where cron_is_active=True and add each as a job."""
        from backend.models.workflows.publishing.published_workflow import (
            PublishedWorkflow,
        )
        from backend.services.database import get_db

        try:
            with get_db() as db:
                workflows = (
                    db.query(PublishedWorkflow)
                    .filter(
                        PublishedWorkflow.cron_is_active == True,  # noqa: E712
                        PublishedWorkflow.cron_expression.isnot(None),
                        PublishedWorkflow.is_published == True,  # noqa: E712
                    )
                    .all()
                )
                count = 0
                for wf in workflows:
                    try:
                        self._add_job(
                            str(wf.id),
                            wf.cron_expression,
                            wf.cron_timezone or "UTC",
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(
                            "%s Failed to load schedule for workflow %s: %s",
                            LOG_PREFIX,
                            wf.id,
                            e,
                        )
                logger.info(
                    "%s Loaded %d active schedules from database", LOG_PREFIX, count
                )
        except Exception as e:
            logger.warning("%s Failed to load active schedules: %s", LOG_PREFIX, e)

    def _add_job(self, published_workflow_id: str, cron_expression: str, timezone: str):
        """Add a CronTrigger job to APScheduler."""
        if not self._scheduler:
            return

        job_id = f"schedule_{published_workflow_id}"

        # Remove existing job if any
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        trigger = CronTrigger.from_crontab(cron_expression, timezone=ZoneInfo(timezone))
        self._scheduler.add_job(
            self._execute_workflow,
            trigger=trigger,
            id=job_id,
            args=[published_workflow_id],
            replace_existing=True,
        )
        logger.info(
            "%s Added job %s with cron '%s' tz=%s",
            LOG_PREFIX,
            job_id,
            cron_expression,
            timezone,
        )

    def add_or_update_schedule(
        self, published_workflow_id: str, cron_expression: str, timezone: str
    ):
        """Add or update a schedule in APScheduler (called after DB update)."""
        self._add_job(published_workflow_id, cron_expression, timezone)

    def remove_schedule(self, published_workflow_id: str):
        """Remove a job from APScheduler."""
        if not self._scheduler:
            return
        job_id = f"schedule_{published_workflow_id}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info("%s Removed job %s", LOG_PREFIX, job_id)

    @staticmethod
    def is_valid_cron(cron_expression: str) -> bool:
        """Validate a cron expression using APScheduler's CronTrigger."""
        try:
            CronTrigger.from_crontab(cron_expression)
            return True
        except (ValueError, KeyError):
            return False

    def get_next_run_time(
        self, cron_expression: str, timezone: str = "UTC"
    ) -> Optional[datetime]:
        """Calculate the next run time for a cron expression."""
        try:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
            trigger = CronTrigger.from_crontab(cron_expression, timezone=tz)
            return trigger.get_next_fire_time(None, now)
        except Exception:
            return None

    def _execute_workflow(self, published_workflow_id: str):
        """Execute a published workflow. Called by APScheduler in a background thread."""
        from backend.api.graph.services.execution_manager import execution_manager
        from backend.models.workflows.publishing.published_workflow import (
            PublishedWorkflow,
        )
        from backend.services.database import get_db
        from backend.services.dependency_injection import get_graph_manager

        logger.info(
            "%s Executing scheduled workflow %s",
            LOG_PREFIX,
            published_workflow_id,
        )

        try:
            with get_db() as db:
                published_workflow = (
                    db.query(PublishedWorkflow)
                    .filter(PublishedWorkflow.id == published_workflow_id)
                    .first()
                )

                if not published_workflow:
                    logger.warning(
                        "%s Published workflow %s not found, removing schedule",
                        LOG_PREFIX,
                        published_workflow_id,
                    )
                    self.remove_schedule(published_workflow_id)
                    return

                if (
                    not published_workflow.is_published
                    or not published_workflow.cron_is_active
                ):
                    logger.info(
                        "%s Workflow %s is no longer active/published, skipping",
                        LOG_PREFIX,
                        published_workflow_id,
                    )
                    return

                # Load the graph
                graph = get_graph_manager().load_graph_by_workflow_id(
                    workflow_id=published_workflow.workflow_id,
                    username=published_workflow.user_id,
                )

                if not graph:
                    logger.error(
                        "%s Could not load graph for workflow %s",
                        LOG_PREFIX,
                        published_workflow_id,
                    )
                    published_workflow.cron_failure_count = (
                        published_workflow.cron_failure_count or 0
                    ) + 1
                    return

                # Generate execution ID
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                execution_id = f"exec_{timestamp}_{sanitize_graph_name(published_workflow.graph_name)}_{uuid.uuid4().hex[:6]}"

                # Submit execution (bypasses auth Î“Ã‡Ã¶ this is an internal scheduled run)
                execution_manager.submit_execution(
                    graph=graph,
                    initial_input={
                        "messages": [
                            {
                                "role": "user",
                                "content": "Scheduled execution",
                            }
                        ]
                    },
                    execution_id=execution_id,
                    user_id=published_workflow.user_id,
                    workflow_id=published_workflow.workflow_id,
                    graph_definition_id=None,
                    trigger_type="scheduler",
                )

                # Update counters
                published_workflow.cron_last_run_at = datetime.now(
                    ZoneInfo(published_workflow.cron_timezone or "UTC")
                )
                published_workflow.cron_run_count = (
                    published_workflow.cron_run_count or 0
                ) + 1

                # Compute next run time
                next_run = self.get_next_run_time(
                    published_workflow.cron_expression,
                    published_workflow.cron_timezone or "UTC",
                )
                published_workflow.cron_next_run_at = next_run

                logger.info(
                    "%s Scheduled execution %s submitted for workflow %s",
                    LOG_PREFIX,
                    execution_id,
                    published_workflow_id,
                )

        except Exception as e:
            logger.error(
                "%s Scheduled execution failed for workflow %s: %s",
                LOG_PREFIX,
                published_workflow_id,
                e,
            )
            # Increment failure count
            try:
                with get_db() as db:
                    wf = (
                        db.query(PublishedWorkflow)
                        .filter(PublishedWorkflow.id == published_workflow_id)
                        .first()
                    )
                    if wf:
                        wf.cron_failure_count = (wf.cron_failure_count or 0) + 1
            except Exception as inner_e:
                logger.error(
                    "%s Failed to update failure count: %s", LOG_PREFIX, inner_e
                )