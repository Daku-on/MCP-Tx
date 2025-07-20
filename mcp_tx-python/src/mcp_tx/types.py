"""
MCP-Tx core types and data structures.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageStatus(str, Enum):
    """Status of an MCP-Tx message."""

    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TransactionStatus(str, Enum):
    """Status of an MCP-Tx transaction."""

    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    WAITING_ACK = "waiting_ack"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ROLLED_BACK = "rolled_back"


@dataclass
class MCPTxMeta:
    """MCP-Tx metadata for message enhancement."""

    version: str = "0.1.0"
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: str | None = None
    idempotency_key: str | None = None
    expect_ack: bool = True
    retry_count: int = 0
    timeout_ms: int = 30000
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class MCPTxResponse:
    """MCP-Tx response metadata."""

    ack: bool
    processed: bool
    duplicate: bool = False
    attempts: int = 1
    final_status: str = "completed"
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class RetryPolicy(BaseModel):
    """Configuration for retry behavior."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay_ms: int = Field(default=1000, ge=100)
    max_delay_ms: int = Field(default=30000, ge=1000)
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)
    jitter: bool = Field(default=True)
    retryable_errors: list[str] = Field(
        default_factory=lambda: ["CONNECTION_ERROR", "TIMEOUT", "NETWORK_ERROR", "TEMPORARY_FAILURE"]
    )


class MCPTxConfig(BaseModel):
    """Configuration for MCP-Tx session."""

    enabled: bool = Field(default=True)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    default_timeout_ms: int = Field(default=30000, ge=1000, le=600000)  # 1s to 10min
    max_concurrent_requests: int = Field(default=10, ge=1, le=100)
    deduplication_window_ms: int = Field(default=300000, ge=10000, le=3600000)  # 10s to 1hr
    enable_transactions: bool = Field(default=True)
    enable_monitoring: bool = Field(default=True)


@dataclass
class MCPTxResult:
    """Result wrapper containing both MCP result and MCP-Tx metadata."""

    result: Any
    mcp_tx_meta: MCPTxResponse

    @property
    def ack(self) -> bool:
        """Whether the request was acknowledged."""
        return self.mcp_tx_meta.ack

    @property
    def processed(self) -> bool:
        """Whether the tool was actually executed."""
        return self.mcp_tx_meta.processed

    @property
    def final_status(self) -> str:
        """Final status of the operation."""
        return self.mcp_tx_meta.final_status

    @property
    def attempts(self) -> int:
        """Number of retry attempts made."""
        return self.mcp_tx_meta.attempts


class MCPTxError(Exception):
    """Base exception for MCP-Tx errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "MCP_TX_ERROR",
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retryable = retryable
        self.details = details or {}


class MCPTxTimeoutError(MCPTxError):
    """Timeout error for MCP-Tx operations."""

    def __init__(self, message: str, timeout_ms: int):
        super().__init__(message, error_code="MCP_TX_TIMEOUT", retryable=True, details={"timeout_ms": timeout_ms})


class MCPTxNetworkError(MCPTxError):
    """Network error for MCP-Tx operations."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(
            message,
            error_code="MCP_TX_NETWORK_ERROR",
            retryable=True,
            details={"original_error": str(original_error) if original_error else None},
        )


class MCPTxSequenceError(MCPTxError):
    """Sequence/ordering error for MCP-Tx operations."""

    def __init__(self, message: str, expected: int, received: int):
        super().__init__(
            message,
            error_code="MCP_TX_SEQUENCE_ERROR",
            retryable=False,
            details={"expected": expected, "received": received},
        )


@dataclass
class RequestTracker:
    """Tracks the lifecycle of an MCP-Tx request."""

    request_id: str
    transaction_id: str | None
    status: MessageStatus
    created_at: datetime
    updated_at: datetime
    attempts: int = 0
    last_error: str | None = None

    def update_status(self, status: MessageStatus, error: str | None = None) -> None:
        """Update request status and timestamp."""
        self.status = status
        self.updated_at = datetime.utcnow()
        if error:
            self.last_error = error
