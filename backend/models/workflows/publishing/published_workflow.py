"""Published workflow model."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ....services.database import Base
from ...base import TimestampMixin, UUIDPrimaryKeyMixin


class PublishedWorkflow(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing published workflow metadata and configuration.

    Manages published workflows with access control, rate limiting,
    and usage analytics.

    Attributes:
        id: Unique published workflow identifier (UUID).
        graph_name: Graph name for this published workflow.
        custom_slug: Custom URL slug (optional).
        description: Workflow description.
        require_authentication: Whether authentication is required.
        rate_limit: Rate limiting configuration (JSON).
        allowed_origins: CORS allowed origins (JSON).
        webhook_url: Completion webhook URL.
        input_schema: JSON schema for input validation.
        workflow_id: Associated workflow ID.
        user_id: User who published the workflow.
        is_published: Whether workflow is currently published.
        published_at: Publication timestamp.
        last_accessed: Last access timestamp.
        access_count: Total number of accesses.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "published_workflows"

    graph_name = Column(String, nullable=False, index=True)  # Removed unique constraint

    # Publication configuration
    custom_slug = Column(String, nullable=True, unique=True, index=True)
    description = Column(Text, nullable=True)
    require_authentication = Column(Boolean, default=True, nullable=False)

    # Access control
    rate_limit = Column(JSON, nullable=True)
    allowed_origins = Column(JSON, nullable=True)
    webhook_url = Column(String, nullable=True)
    input_schema = Column(JSON, nullable=True)

    # User and workflow ownership
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id = Column(String(255), nullable=True, index=True)

    # Status and analytics
    is_published = Column(Boolean, default=True, nullable=False)
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    access_count = Column(BigInteger, default=0, nullable=False)

    # Cron scheduling
    cron_expression = Column(String, nullable=True)
    cron_timezone = Column(String, nullable=False, default="UTC")
    cron_is_active = Column(Boolean, default=False, nullable=False)
    cron_last_run_at = Column(DateTime(timezone=True), nullable=True)
    cron_next_run_at = Column(DateTime(timezone=True), nullable=True)
    cron_run_count = Column(BigInteger, default=0, nullable=False)
    cron_failure_count = Column(BigInteger, default=0, nullable=False)

    # Relationships
    workflow = relationship("Workflow")
    auth_tokens = relationship(
        "WorkflowAuthToken",
        back_populates="published_workflow",
        cascade="all, delete-orphan",
    )
    access_logs = relationship(
        "WorkflowAccessLog",
        back_populates="published_workflow",
        cascade="all, delete-orphan",
    )