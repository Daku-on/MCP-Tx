"""Test RMCP types and data structures."""

from datetime import datetime

import pytest

from rmcp.types import (
    MessageStatus,
    RequestTracker,
    RetryPolicy,
    RMCPConfig,
    RMCPMeta,
    RMCPResponse,
    RMCPResult,
    TransactionStatus,
)


def test_rmcp_meta_creation():
    """Test RMCPMeta creation and serialization."""
    meta = RMCPMeta(idempotency_key="test-key", timeout_ms=5000)

    assert meta.version == "0.1.0"
    assert meta.idempotency_key == "test-key"
    assert meta.timeout_ms == 5000
    assert meta.expect_ack is True
    assert meta.retry_count == 0
    assert meta.request_id  # Should be generated

    # Test serialization
    data = meta.to_dict()
    assert "version" in data
    assert "request_id" in data
    assert "idempotency_key" in data
    assert "timeout_ms" in data


def test_rmcp_response():
    """Test RMCPResponse creation."""
    response = RMCPResponse(
        ack=True,
        processed=True,
        attempts=2,
        final_status="completed"
    )

    assert response.ack is True
    assert response.processed is True
    assert response.duplicate is False
    assert response.attempts == 2
    assert response.final_status == "completed"

    # Test serialization
    data = response.to_dict()
    assert data["ack"] is True
    assert data["processed"] is True
    assert data["attempts"] == 2


def test_rmcp_result():
    """Test RMCPResult wrapper."""
    response_meta = RMCPResponse(
        ack=True,
        processed=True,
        attempts=1,
        final_status="completed"
    )

    result = RMCPResult(
        result={"data": "test"},
        rmcp_meta=response_meta
    )

    # Test convenience properties
    assert result.ack is True
    assert result.processed is True
    assert result.final_status == "completed"
    assert result.attempts == 1
    assert result.result == {"data": "test"}


def test_retry_policy_defaults():
    """Test RetryPolicy default values."""
    policy = RetryPolicy()

    assert policy.max_attempts == 3
    assert policy.base_delay_ms == 1000
    assert policy.max_delay_ms == 30000
    assert policy.backoff_multiplier == 2.0
    assert policy.jitter is True
    assert "CONNECTION_ERROR" in policy.retryable_errors
    assert "TIMEOUT" in policy.retryable_errors


def test_retry_policy_validation():
    """Test RetryPolicy validation."""
    # Valid policy
    policy = RetryPolicy(
        max_attempts=5,
        base_delay_ms=500,
        max_delay_ms=60000,
        backoff_multiplier=1.5
    )
    assert policy.max_attempts == 5
    assert policy.base_delay_ms == 500

    # Test validation (should raise on invalid values)
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)  # Too low

    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=20)  # Too high


def test_rmcp_config_defaults():
    """Test RMCPConfig default values."""
    config = RMCPConfig()

    assert config.enabled is True
    assert config.default_timeout_ms == 30000
    assert config.max_concurrent_requests == 10
    assert config.deduplication_window_ms == 300000
    assert config.enable_transactions is True
    assert config.enable_monitoring is True
    assert isinstance(config.retry_policy, RetryPolicy)


def test_request_tracker():
    """Test RequestTracker functionality."""
    tracker = RequestTracker(
        request_id="test-123",
        transaction_id="tx-456",
        status=MessageStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    assert tracker.request_id == "test-123"
    assert tracker.transaction_id == "tx-456"
    assert tracker.status == MessageStatus.PENDING
    assert tracker.attempts == 0
    assert tracker.last_error is None

    # Test status update
    tracker.update_status(MessageStatus.FAILED, "Network error")
    assert tracker.status == MessageStatus.FAILED
    assert tracker.last_error == "Network error"
    assert tracker.updated_at > tracker.created_at


def test_message_status_enum():
    """Test MessageStatus enum values."""
    assert MessageStatus.PENDING == "pending"
    assert MessageStatus.SENT == "sent"
    assert MessageStatus.ACKNOWLEDGED == "acknowledged"
    assert MessageStatus.FAILED == "failed"
    assert MessageStatus.TIMEOUT == "timeout"


def test_transaction_status_enum():
    """Test TransactionStatus enum values."""
    assert TransactionStatus.INITIATED == "initiated"
    assert TransactionStatus.IN_PROGRESS == "in_progress"
    assert TransactionStatus.WAITING_ACK == "waiting_ack"
    assert TransactionStatus.COMPLETED == "completed"
    assert TransactionStatus.FAILED == "failed"
    assert TransactionStatus.TIMEOUT == "timeout"
    assert TransactionStatus.ROLLED_BACK == "rolled_back"
