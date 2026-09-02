"""Workflow scheduling API endpoints for cron-based execution."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.http_execution.utils.constants import sanitize_graph_name

from ..auth.dependencies import get_current_user
from backend.services.auth.scope_enforcer import require_scope
from ...models.workflows.publishing.published_workflow import PublishedWorkflow
from ...services.database import get_db
from ...services.scheduling import scheduler_service

logger = logging.getLogger(__name__)
LOG_PREFIX = "[SCHEDULE-API]"


def _feature_disabled() -> None:
    """Guard dependency: gate schedule endpoints behind the SCHEDULING_ENABLED toggle.

    Set the `SCHEDULING_ENABLED` environment variable to "true" and restart the
    backend to re-enable workflow scheduling Î“Ã‡Ã¶ no code changes required.
    """
    from ...services.scheduling import is_scheduling_enabled

    if not is_scheduling_enabled():
        raise HTTPException(
            status_code=503,
            detail="Workflow scheduling is coming soon and is currently disabled.",
        )


schedule_router = APIRouter(
    prefix="/api/schedules",
    tags=["workflow-scheduling"],
    dependencies=[Depends(_feature_disabled)],
)


def _get_user_identifier(current_user: Dict[str, Any]) -> str:
    """Extract user identifier from JWT claims."""
    user_identifier = current_user.get("sub")
    if not user_identifier:
        raise HTTPException(status_code=401, detail="Token missing user identifier")
    return user_identifier


def _get_published_workflow(workflow_id: str, user_id: str) -> PublishedWorkflow:
    """Load a published workflow and verify ownership."""
    with get_db() as db:
        wf = (
            db.query(PublishedWorkflow)
            .filter(
                PublishedWorkflow.workflow_id == workflow_id,
                PublishedWorkflow.user_id == user_id,
                PublishedWorkflow.is_published == True,  # noqa: E712
            )
            .first()
        )
        if not wf:
            raise HTTPException(
                status_code=404,
                detail="Published workflow not found or you don't have access",
            )
        # Expunge so we can use outside session
        db.expunge(wf)
        return wf


# --- Request / Response models ---


class ScheduleRequest(BaseModel):
    """Request model for creating or updating a schedule."""

    cron_expression: str = Field(
        ..., description="Cron expression (e.g. '0 9 * * 1-5')"
    )
    timezone: str = Field("UTC", description="IANA timezone (e.g. 'America/New_York')")
    is_active: bool = Field(True, description="Whether the schedule is active")


class ScheduleResponse(BaseModel):
    """Response model for schedule information."""

    published_workflow_id: str
    workflow_id: str
    cron_expression: Optional[str] = None
    timezone: str = "UTC"
    is_active: bool = False
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    run_count: int = 0
    failure_count: int = 0


def _build_schedule_response(wf: PublishedWorkflow) -> ScheduleResponse:
    """Build a ScheduleResponse from a PublishedWorkflow."""
    return ScheduleResponse(
        published_workflow_id=str(wf.id),
        workflow_id=wf.workflow_id,
        cron_expression=wf.cron_expression,
        timezone=wf.cron_timezone or "UTC",
        is_active=wf.cron_is_active,
        last_run_at=wf.cron_last_run_at.isoformat() if wf.cron_last_run_at else None,
        next_run_at=wf.cron_next_run_at.isoformat() if wf.cron_next_run_at else None,
        run_count=wf.cron_run_count or 0,
        failure_count=wf.cron_failure_count or 0,
    )


# --- Endpoints ---


@schedule_router.get("/workflow/{workflow_id}", dependencies=[Depends(require_scope("workflow:*:read"))])
async def get_workflow_schedule(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ScheduleResponse:
    """Get the schedule for a published workflow."""
    user_id = _get_user_identifier(current_user)
    wf = _get_published_workflow(workflow_id, user_id)
    return _build_schedule_response(wf)


@schedule_router.put("/workflow/{workflow_id}", dependencies=[Depends(require_scope("workflow:*:write"))])
async def update_workflow_schedule(
    workflow_id: str,
    request: ScheduleRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ScheduleResponse:
    """Create or update a schedule for a published workflow."""
    user_id = _get_user_identifier(current_user)

    # Validate cron expression
    if not scheduler_service.is_valid_cron(request.cron_expression):
        raise HTTPException(status_code=400, detail="Invalid cron expression")

    # Validate timezone
    try:
        ZoneInfo(request.timezone)
    except (KeyError, Exception):
        raise HTTPException(
            status_code=400, detail=f"Invalid timezone: {request.timezone}"
        )

    with get_db() as db:
        wf = (
            db.query(PublishedWorkflow)
            .filter(
                PublishedWorkflow.workflow_id == workflow_id,
                PublishedWorkflow.user_id == user_id,
                PublishedWorkflow.is_published == True,  # noqa: E712
            )
            .first()
        )
        if not wf:
            raise HTTPException(
                status_code=404,
                detail="Published workflow not found or you don't have access",
            )

        wf.cron_expression = request.cron_expression
        wf.cron_timezone = request.timezone
        wf.cron_is_active = request.is_active

        # Compute next run time
        next_run = scheduler_service.get_next_run_time(
            request.cron_expression, request.timezone
        )
        wf.cron_next_run_at = next_run

        db.flush()
        db.refresh(wf)
        response = _build_schedule_response(wf)

    # Update APScheduler
    if request.is_active:
        scheduler_service.add_or_update_schedule(
            response.published_workflow_id,
            request.cron_expression,
            request.timezone,
        )
    else:
        scheduler_service.remove_schedule(response.published_workflow_id)

    logger.info(
        "%s Schedule updated for workflow %s: cron=%s tz=%s active=%s",
        LOG_PREFIX,
        workflow_id,
        request.cron_expression,
        request.timezone,
        request.is_active,
    )
    return response


@schedule_router.delete("/workflow/{workflow_id}", dependencies=[Depends(require_scope("workflow:*:write"))])
async def delete_workflow_schedule(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Remove a schedule from a published workflow."""
    user_id = _get_user_identifier(current_user)

    with get_db() as db:
        wf = (
            db.query(PublishedWorkflow)
            .filter(
                PublishedWorkflow.workflow_id == workflow_id,
                PublishedWorkflow.user_id == user_id,
                PublishedWorkflow.is_published == True,  # noqa: E712
            )
            .first()
        )
        if not wf:
            raise HTTPException(
                status_code=404,
                detail="Published workflow not found or you don't have access",
            )

        published_workflow_id = str(wf.id)
        wf.cron_expression = None
        wf.cron_timezone = "UTC"
        wf.cron_is_active = False
        wf.cron_next_run_at = None

    # Remove from APScheduler
    scheduler_service.remove_schedule(published_workflow_id)

    logger.info("%s Schedule removed for workflow %s", LOG_PREFIX, workflow_id)
    return {"success": True, "message": "Schedule removed"}


@schedule_router.post("/workflow/{workflow_id}/pause", dependencies=[Depends(require_scope("workflow:*:write"))])
async def pause_workflow_schedule(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ScheduleResponse:
    """Pause a workflow schedule."""
    user_id = _get_user_identifier(current_user)

    with get_db() as db:
        wf = (
            db.query(PublishedWorkflow)
            .filter(
                PublishedWorkflow.workflow_id == workflow_id,
                PublishedWorkflow.user_id == user_id,
                PublishedWorkflow.is_published == True,  # noqa: E712
            )
            .first()
        )
        if not wf:
            raise HTTPException(
                status_code=404,
                detail="Published workflow not found or you don't have access",
            )

        wf.cron_is_active = False
        published_workflow_id = str(wf.id)
        db.flush()
        db.refresh(wf)
        response = _build_schedule_response(wf)

    scheduler_service.remove_schedule(published_workflow_id)
    logger.info("%s Schedule paused for workflow %s", LOG_PREFIX, workflow_id)
    return response


@schedule_router.post("/workflow/{workflow_id}/resume", dependencies=[Depends(require_scope("workflow:*:write"))])
async def resume_workflow_schedule(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ScheduleResponse:
    """Resume a paused workflow schedule."""
    user_id = _get_user_identifier(current_user)

    with get_db() as db:
        wf = (
            db.query(PublishedWorkflow)
            .filter(
                PublishedWorkflow.workflow_id == workflow_id,
                PublishedWorkflow.user_id == user_id,
                PublishedWorkflow.is_published == True,  # noqa: E712
            )
            .first()
        )
        if not wf:
            raise HTTPException(
                status_code=404,
                detail="Published workflow not found or you don't have access",
            )

        if not wf.cron_expression:
            raise HTTPException(
                status_code=400,
                detail="No cron expression set. Use PUT to create a schedule first.",
            )

        wf.cron_is_active = True
        next_run = scheduler_service.get_next_run_time(
            wf.cron_expression, wf.cron_timezone or "UTC"
        )
        wf.cron_next_run_at = next_run

        published_workflow_id = str(wf.id)
        cron_expr = wf.cron_expression
        timezone = wf.cron_timezone or "UTC"
        db.flush()
        db.refresh(wf)
        response = _build_schedule_response(wf)

    scheduler_service.add_or_update_schedule(published_workflow_id, cron_expr, timezone)
    logger.info("%s Schedule resumed for workflow %s", LOG_PREFIX, workflow_id)
    return response


@schedule_router.post("/workflow/{workflow_id}/trigger", dependencies=[Depends(require_scope("workflow:*:execute"))])
async def trigger_workflow_schedule(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Manually trigger an immediate execution of a scheduled workflow."""
    user_id = _get_user_identifier(current_user)

    from ...api.graph.services.execution_manager import execution_manager
    from ...services.dependency_injection import get_graph_manager

    with get_db() as db:
        wf = (
            db.query(PublishedWorkflow)
            .filter(
                PublishedWorkflow.workflow_id == workflow_id,
                PublishedWorkflow.user_id == user_id,
                PublishedWorkflow.is_published == True,  # noqa: E712
            )
            .first()
        )
        if not wf:
            raise HTTPException(
                status_code=404,
                detail="Published workflow not found or you don't have access",
            )

        graph = get_graph_manager().load_graph_by_workflow_id(
            workflow_id=wf.workflow_id,
            username=wf.user_id,
        )
        if not graph:
            raise HTTPException(
                status_code=500,
                detail="Failed to load workflow graph",
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        execution_id = f"exec_{timestamp}_{sanitize_graph_name(wf.graph_name)}_{uuid.uuid4().hex[:6]}"

        execution_manager.submit_execution(
            graph=graph,
            initial_input={
                "messages": [
                    {
                        "role": "user",
                        "content": "Manually triggered scheduled execution",
                    }
                ]
            },
            execution_id=execution_id,
            user_id=wf.user_id,
            workflow_id=wf.workflow_id,
            graph_definition_id=None,
            trigger_type="scheduler",
        )

        # Update counters
        wf.cron_last_run_at = datetime.now(ZoneInfo(wf.cron_timezone or "UTC"))
        wf.cron_run_count = (wf.cron_run_count or 0) + 1

    logger.info(
        "%s Manual trigger for workflow %s, execution_id=%s",
        LOG_PREFIX,
        workflow_id,
        execution_id,
    )
    return {"success": True, "execution_id": execution_id}