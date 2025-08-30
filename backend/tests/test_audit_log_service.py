"""
Tests for audit log service functionality.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock
from app.services.audit_log_service import (
    log_audit_event,
    log_login_attempt,
    log_transaction,
    log_admin_action
)


class TestAuditLogService:
    """Test cases for audit log service."""

    @pytest.mark.asyncio
    async def test_log_audit_event_success(self, test_db_session):
        """Test successful audit event logging."""
        result = await log_audit_event(
            db=test_db_session,
            user_id=1,
            action="user_login",
            details="User logged in successfully"
        )

        assert result is not None
        assert result.id is not None
        assert result.user_id == 1  # type: ignore
        assert result.action == "user_login"  # type: ignore
        assert result.details == "User logged in successfully"  # type: ignore

    @pytest.mark.asyncio
    async def test_log_audit_event_without_details(self, test_db_session):
        """Test audit event logging without details."""
        result = await log_audit_event(
            db=test_db_session,
            user_id=2,
            action="password_change"
        )

        assert result is not None
        assert result.id is not None
        assert result.user_id == 2  # type: ignore
        assert result.action == "password_change"  # type: ignore
        assert result.details is None  # type: ignore

    @pytest.mark.asyncio
    async def test_log_login_attempt_success(self, test_db_session):
        """Test successful login attempt logging."""
        result = await log_login_attempt(
            db=test_db_session,
            user_id=1,
            location="New York, US",
            status="success",
            details="Login from Chrome"
        )

        assert result is not None
        assert result.user_id == 1  # type: ignore
        assert result.action == "login_success"  # type: ignore
        assert "New York, US" in result.details  # type: ignore

    @pytest.mark.asyncio
    async def test_log_login_attempt_failure(self, test_db_session):
        """Test failed login attempt logging."""
        result = await log_login_attempt(
            db=test_db_session,
            user_id=None,  # Anonymous login attempt
            location="Unknown",
            status="failure",
            details="Invalid credentials"
        )

        assert result is not None
        assert result.user_id is None  # type: ignore
        assert result.action == "login_failure"  # type: ignore
        assert "Invalid credentials" in result.details  # type: ignore

    @pytest.mark.asyncio
    async def test_log_transaction_success(self, test_db_session):
        """Test successful transaction logging."""
        result = await log_transaction(
            db=test_db_session,
            user_id=1,
            transaction_id=123,
            action="allowed",
            details="Payment processed successfully"
        )

        assert result is not None
        assert result.user_id == 1  # type: ignore
        assert result.action == "transaction_allowed"  # type: ignore
        assert "Transaction ID: 123" in result.details  # type: ignore
        assert "Payment processed successfully" in result.details  # type: ignore

    @pytest.mark.asyncio
    async def test_log_transaction_blocked(self, test_db_session):
        """Test blocked transaction logging."""
        result = await log_transaction(
            db=test_db_session,
            user_id=2,
            transaction_id=456,
            action="blocked",
            details="High risk transaction blocked"
        )

        assert result is not None
        assert result.action == "transaction_blocked"  # type: ignore
        assert "Transaction ID: 456" in result.details  # type: ignore

    @pytest.mark.asyncio
    async def test_log_admin_action_success(self, test_db_session):
        """Test successful admin action logging."""
        result = await log_admin_action(
            db=test_db_session,
            user_id=1,
            action="user_suspend",
            details="Suspended user ID: 123"
        )

        assert result is not None
        assert result.user_id == 1  # type: ignore
        assert result.action == "admin_user_suspend"  # type: ignore
        assert result.details == "Suspended user ID: 123"  # type: ignore

    @pytest.mark.asyncio
    async def test_log_admin_action_without_details(self, test_db_session):
        """Test admin action logging without details."""
        result = await log_admin_action(
            db=test_db_session,
            user_id=1,
            action="system_backup"
        )

        assert result is not None
        assert result.action == "admin_system_backup"  # type: ignore
        assert result.details is None  # type: ignore

    @pytest.mark.asyncio
    async def test_multiple_log_entries(self, test_db_session):
        """Test creating multiple log entries."""
        # Create multiple log entries
        await log_audit_event(test_db_session, 1, "action1", "details1")
        await log_audit_event(test_db_session, 1, "action2", "details2")
        await log_audit_event(test_db_session, 2, "action3", "details3")

        # All should succeed without conflicts
        assert True  # If we get here, all operations succeeded

    def test_log_functions_are_callable(self):
        """Test that all log functions are properly defined and callable."""
        assert callable(log_audit_event)
        assert callable(log_login_attempt)
        assert callable(log_transaction)
        assert callable(log_admin_action)
