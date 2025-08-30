"""
Tests for email service functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.email_service import send_magic_link_email


class TestEmailService:
    """Test cases for email service."""

    def test_send_magic_link_email_success(self, mock_email_service):
        """Test successful email sending."""
        result = send_magic_link_email("test@example.com", "http://test.com/link")

        assert result is True
        # The mock_email_service fixture patches the function to return True

    def test_send_magic_link_email_missing_sender(self, monkeypatch):
        """Test email sending with missing sender configuration."""
        # Mock missing EMAIL_SENDER
        monkeypatch.setattr("app.services.email_service.EMAIL_SENDER", None)

        result = send_magic_link_email("test@example.com", "http://test.com/link")

        assert result is False

    def test_send_magic_link_email_missing_password(self, monkeypatch):
        """Test email sending with missing password configuration."""
        # Mock missing EMAIL_PASSWORD
        monkeypatch.setattr("app.services.email_service.EMAIL_PASSWORD", None)

        result = send_magic_link_email("test@example.com", "http://test.com/link")

        assert result is False

    @patch('smtplib.SMTP')
    def test_send_magic_link_email_smtp_error(self, mock_smtp, monkeypatch):
        """Test email sending with SMTP error."""
        # Set up valid configuration
        monkeypatch.setattr("app.services.email_service.EMAIL_SENDER", "test@example.com")
        monkeypatch.setattr("app.services.email_service.EMAIL_PASSWORD", "password")

        # Mock SMTP to raise exception
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.starttls.side_effect = Exception("SMTP Error")
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        result = send_magic_link_email("test@example.com", "http://test.com/link")

        assert result is False

    @patch('smtplib.SMTP')
    def test_send_magic_link_email_successful_flow(self, mock_smtp, monkeypatch):
        """Test complete successful email flow."""
        # Set up valid configuration
        monkeypatch.setattr("app.services.email_service.EMAIL_SENDER", "sender@example.com")
        monkeypatch.setattr("app.services.email_service.EMAIL_PASSWORD", "password")

        # Mock successful SMTP flow
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        result = send_magic_link_email("recipient@example.com", "http://test.com/link")

        assert result is True

        # Verify SMTP calls
        mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("sender@example.com", "password")
        mock_smtp_instance.sendmail.assert_called_once()

        # Verify email content
        call_args = mock_smtp_instance.sendmail.call_args
        sender, recipients, msg = call_args[0]

        assert sender == "sender@example.com"
        assert recipients == ["recipient@example.com"]
        assert "http://test.com/link" in msg
        assert "Your FinVault Magic Login Link" in msg
