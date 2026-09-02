"""Graph execution manager service.

This module provides the GraphExecutionManager class for managing
graph execution using a thread pool executor.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from backend.models.workflow import GraphData
from backend.services.config import get_logger
from backend.services.dependency_injection import get_execution_engine
from backend.services.websocket import connection_manager


from ..constants import LOG_PREFIX, THREAD_POOL_MAX_WORKERS, THREAD_POOL_NAME_PREFIX


logger = get_logger(__name__)

# Captured once at first execution submission so that worker threads can
# schedule WebSocket coroutines on the correct (main) event loop.
_main_event_loop: Optional[asyncio.AbstractEventLoop] = None


def get_main_event_loop() -> Optional[asyncio.AbstractEventLoop]:
    """Return the main FastAPI event loop, or None if not yet captured."""
    return _main_event_loop


class GraphExecutionManager:
    """Manager for graph execution with thread pool.

    This class provides a service layer for executing graphs asynchronously
    using a thread pool executor. It encapsulates the threading logic and
    provides a clean interface for graph execution.

    Attributes:
        _executor: ThreadPoolExecutor for async execution
    """

    def __init__(self, max_workers: int = THREAD_POOL_MAX_WORKERS):
        """Initialize GraphExecutionManager.

        Args:
            max_workers: Maximum number of worker threads
        """
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix=THREAD_POOL_NAME_PREFIX
        )
        logger.info(
            f"{LOG_PREFIX} GraphExecutionManager initialized with {max_workers} workers"
        )

    def execute_graph_in_thread(
        self,
        graph: GraphData,
        initial_input: dict[str, Any],
        execution_id: str,
        user_id: str | None = None,
        workflow_id: str | None = None,
        graph_definition_id: str | None = None,
        user_access_token: str | None = None,
        trigger_type: str | None = None,
        chat_session_id: str | None = None,
    ):
        """Execute graph in a separate thread to avoid blocking the API.

        This method runs the async graph execution in a new event loop
        within a thread pool worker.

        Args:
            graph: GraphData object to execute
            initial_input: Initial input data for the graph
            execution_id: Unique execution identifier
            user_id: Optional user ID for tracking
            workflow_id: Optional workflow ID for tracking
            graph_definition_id: Optional graph definition ID for tracking
            user_access_token: Optional user's JWT access token for MCP servers
            trigger_type: Execution trigger type (editor, api, evaluation, scheduler, chat)
            chat_session_id: Optional chat session ID for chat-triggered executions
        """
        try:
            logger.info(
                f"{LOG_PREFIX} Starting graph execution in thread: {execution_id}"
            )
            # Run the async function in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    get_execution_engine().execute_graph(
                        graph=graph,
                        initial_input=initial_input,
                        execution_id=execution_id,
                        user_id=user_id,
                        workflow_id=workflow_id,
                        graph_definition_id=graph_definition_id,
                        user_access_token=user_access_token,
                        trigger_type=trigger_type,
                        chat_session_id=chat_session_id,
                    )
                )
                logger.info(f"{LOG_PREFIX} Graph execution completed: {execution_id}")
            finally:
                # Clean up thread-local checkpointer before closing loop
                # This ensures connection pools are properly closed
                from backend.services.execution.checkpointer_manager import (
                    get_checkpointer_manager,
                )

                get_checkpointer_manager().cleanup_thread()
                loop.close()
        except Exception as e:
            # Error is already logged in the execution context
            logger.error(
                f"{LOG_PREFIX} Error in thread execution {execution_id}: {e}",
                exc_info=True,
            )

    def submit_execution(
        self,
        graph: GraphData,
        initial_input: dict[str, Any],
        execution_id: str,
        user_id: str | None = None,
        workflow_id: str | None = None,
        graph_definition_id: str | None = None,
        user_access_token: str | None = None,
        trigger_type: str | None = None,
        chat_session_id: str | None = None,
    ):
        """Submit a graph execution to the thread pool.

        Args:
            graph: GraphData object to execute
            initial_input: Initial input data for the graph
            execution_id: Unique execution identifier
            user_id: Optional user ID for tracking
            workflow_id: Optional workflow ID for tracking
            graph_definition_id: Optional graph definition ID for tracking
            user_access_token: Optional user's JWT access token for MCP servers
            trigger_type: Execution trigger type (editor, api, evaluation, scheduler, chat)
            chat_session_id: Optional chat session ID for chat-triggered executions

        Returns:
            Future object representing the execution
        """
        global _main_event_loop
        if _main_event_loop is None:
            _main_event_loop = asyncio.get_running_loop()
            # Register the loop with ConnectionManager so it can route
            # cross-thread WebSocket sends without an upward import.

            connection_manager.set_main_loop(_main_event_loop)

        logger.info(f"{LOG_PREFIX} Submitting execution to thread pool: {execution_id}")
        return self._executor.submit(
            self.execute_graph_in_thread,
            graph,
            initial_input,
            execution_id,
            user_id,
            workflow_id,
            graph_definition_id,
            user_access_token,
            trigger_type,
            chat_session_id,
        )

    def shutdown(self, wait: bool = True):
        """Shutdown the thread pool executor.

        Args:
            wait: If True, wait for all pending futures to complete
        """
        logger.info(f"{LOG_PREFIX} Shutting down GraphExecutionManager")
        self._executor.shutdown(wait=wait)


# Global singleton instance
execution_manager = GraphExecutionManager()


def get_execution_status_with_nodes(execution_id: str) -> dict[str, Any] | None:
    """Get execution status with node execution details.

    This function retrieves the execution status from the execution engine
    and enriches it with detailed node execution information from the database.

    Args:
        execution_id: Unique execution identifier

    Returns:
        Dictionary containing execution status and node details, or None if not found
    """
    safe_keys = {
        "execution_id",
        "status",
        "start_time",
        "end_time",
        "graph_name",
        "current_node",
        "current_node_name",
        "error",
        "db_execution_id",
        "thread_id",
        "workflow_id",
        "graph_definition_id",
        "paused",
        "control",
    }

    # Check if execution exists in active executions
    if execution_id not in get_execution_engine().active_executions:
        # Check history
        for record in get_execution_engine().execution_history:
            if record.get("execution_id") == execution_id:
                # Filter to safe keys only Î“Ã‡Ã¶ raw records contain
                # non-serializable objects (event_loop, stream_generator)
                return {key: record[key] for key in safe_keys if key in record}
        return None

    # Get basic status from engine
    status = get_execution_engine().active_executions.get(execution_id)
    if not status:
        return None

    sanitized_status: dict[str, Any] = {
        key: status[key] for key in safe_keys if key in status
    }

    # Get node executions from database if available
    db_execution_id = status.get("db_execution_id")
    if db_execution_id:
        try:
            from backend.services.execution.history import ExecutionHistoryService

            node_executions = ExecutionHistoryService.get_node_executions(
                db_execution_id
            )

            # Format node executions for frontend with complete data
            formatted_nodes = {}
            for node_exec in node_executions:
                node_id = node_exec.get("node_id")
                formatted_nodes[node_id] = {
                    "id": node_exec.get("id"),
                    "node_id": node_id,
                    "node_name": node_exec.get("node_name"),
                    "node_type": node_exec.get("node_type"),
                    "status": node_exec.get("status"),
                    "start_time": str(node_exec.get("start_time"))
                    if node_exec.get("start_time")
                    else None,
                    "end_time": str(node_exec.get("end_time"))
                    if node_exec.get("end_time")
                    else None,
                    "duration_seconds": node_exec.get("duration_seconds"),
                    "input_data": node_exec.get("input_data"),
                    "output_data": node_exec.get("output_data"),
                    "error_message": node_exec.get("error_message"),
                    "input_tokens": node_exec.get("input_tokens"),
                    "output_tokens": node_exec.get("output_tokens"),
                    "total_tokens": node_exec.get("total_tokens"),
                }

            sanitized_status["node_executions"] = formatted_nodes
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to get node executions: {e}")

    return sanitized_status