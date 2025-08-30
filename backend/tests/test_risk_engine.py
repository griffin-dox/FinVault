"""
Tests for the risk engine service.
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from app.services.risk_engine import (
    score_transaction,
    device_penalty,
    geo_penalty,
    typing_penalty,
    score_login,
    _haversine
)


class TestRiskEngine:
    """Test cases for risk engine functionality."""

    def test_score_transaction_low_risk(self, sample_transaction_data, sample_behavior_profile):
        """Test scoring a low-risk transaction."""
        from unittest.mock import patch
        from datetime import datetime
        
        # Mock the current time to be within normal hours (10 AM UTC)
        mock_time = datetime(2024, 1, 1, 10, 0, 0)
        
        with patch('app.services.risk_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            result = score_transaction(sample_transaction_data, sample_behavior_profile)

        assert isinstance(result, dict)
        assert "risk_score" in result
        assert "level" in result
        assert "reasons" in result
        assert "anomalies" in result
        assert result["level"] == "low"
        assert result["risk_score"] == 0

    def test_score_transaction_device_mismatch(self, sample_transaction_data, sample_behavior_profile):
        """Test scoring transaction with device mismatch."""
        # Modify transaction to have different device
        transaction = sample_transaction_data.copy()
        transaction["device_info"] = "Different Browser"

        with patch('app.services.risk_engine.user_tx_history', {}):
            result = score_transaction(transaction, sample_behavior_profile)

        assert result["risk_score"] > 0
        assert "Device mismatch" in result["reasons"]
        assert "New device detected" in result["anomalies"]

    def test_score_transaction_location_mismatch(self, sample_transaction_data, sample_behavior_profile):
        """Test scoring transaction with location mismatch."""
        transaction = sample_transaction_data.copy()
        transaction["location"] = "Different City"

        with patch('app.services.risk_engine.user_tx_history', {}):
            result = score_transaction(transaction, sample_behavior_profile)

        assert result["risk_score"] > 0
        assert "Location mismatch" in result["reasons"]

    def test_score_transaction_large_amount(self, sample_transaction_data, sample_behavior_profile):
        """Test scoring transaction with large amount."""
        transaction = sample_transaction_data.copy()
        transaction["amount"] = 1000.0  # Large amount

        with patch('app.services.risk_engine.user_tx_history', {}):
            result = score_transaction(transaction, sample_behavior_profile)

        assert result["risk_score"] > 0
        assert "Large transaction amount" in result["reasons"]

    def test_score_transaction_unusual_time(self, sample_transaction_data, sample_behavior_profile, monkeypatch):
        """Test scoring transaction at unusual time."""
        # Mock datetime to return 2 AM
        mock_datetime = MagicMock()
        mock_datetime.now.return_value = datetime(2023, 1, 1, 2, 0, 0)  # 2 AM
        mock_datetime.hour = 2

        with patch('app.services.risk_engine.datetime', mock_datetime):
            result = score_transaction(sample_transaction_data, sample_behavior_profile)

        assert result["risk_score"] > 0
        assert "Unusual transaction time" in result["reasons"]

    def test_score_transaction_missing_user_id(self):
        """Test scoring transaction with missing user_id."""
        transaction = {"amount": 100.0}
        result = score_transaction(transaction, {})

        assert result["risk_score"] == 0
        assert result["level"] == "low"
        assert "Invalid transaction - no user_id" in result["reasons"]

    def test_score_transaction_custom_rules(self, sample_transaction_data, sample_behavior_profile):
        """Test scoring with custom rules."""
        from unittest.mock import patch
        from datetime import datetime
        
        custom_rules = {
            "device_mismatch": 100,  # Higher penalty
            "high_threshold": 50,
            "medium_threshold": 25
        }

        transaction = sample_transaction_data.copy()
        transaction["device_info"] = "Different Device"

        # Mock the current time to be within normal hours and clear transaction history
        mock_time = datetime(2024, 1, 1, 10, 0, 0)
        
        with patch('app.services.risk_engine.datetime') as mock_datetime, \
             patch('app.services.risk_engine.user_tx_history', {}):
            mock_datetime.now.return_value = mock_time
            result = score_transaction(transaction, sample_behavior_profile, custom_rules)

        assert result["risk_score"] == 100  # Should use custom rule
        assert result["level"] == "high"

    def test_device_penalty_matching_devices(self):
        """Test device penalty with matching devices."""
        current = {"browser": "Chrome", "os": "Windows", "screen": "1920x1080"}
        profile = {"browser": "Chrome", "os": "Windows", "screen": "1920x1080"}

        penalty, reasons = device_penalty(current, profile)

        assert penalty == 0
        assert len(reasons) == 0

    def test_device_penalty_different_browser(self):
        """Test device penalty with different browser."""
        current = {"browser": "Firefox", "os": "Windows"}
        profile = {"browser": "Chrome", "os": "Windows"}

        penalty, reasons = device_penalty(current, profile)

        assert penalty > 0
        assert any("Device browser brand mismatch" in reason for reason in reasons)

    def test_geo_penalty_same_location(self):
        """Test geo penalty with same location."""
        current = {"latitude": 40.7128, "longitude": -74.0060, "accuracy": 10}
        profile = {"latitude": 40.7128, "longitude": -74.0060}

        penalty, reasons = geo_penalty(current, profile)

        assert penalty == 0

    def test_geo_penalty_different_location(self):
        """Test geo penalty with different location."""
        current = {"latitude": 40.7128, "longitude": -74.0060, "accuracy": 10}
        profile = {"latitude": 34.0522, "longitude": -118.2437}  # Los Angeles

        penalty, reasons = geo_penalty(current, profile)

        assert penalty > 0

    def test_haversine_distance_calculation(self):
        """Test haversine distance calculation."""
        # New York to Los Angeles
        nyc_lat, nyc_lon = 40.7128, -74.0060
        la_lat, la_lon = 34.0522, -118.2437

        distance = _haversine(nyc_lat, nyc_lon, la_lat, la_lon)

        # Approximate distance should be around 3935 km
        assert 3900 < distance < 4000

    def test_haversine_with_none_coordinates(self):
        """Test haversine with None coordinates."""
        distance = _haversine(None, None, 40.7128, -74.0060)
        assert distance == float('inf')

    def test_typing_penalty_normal_behavior(self):
        """Test typing penalty with normal behavior."""
        current = {"wpm": 60, "errorRate": 0.02, "keystrokeTimings": [100, 105, 98]}
        profile = {
            "baselines": {
                "typing": {
                    "wpm_mean": 60,
                    "wpm_std": 5,
                    "err_mean": 0.02,
                    "err_std": 0.01
                }
            }
        }

        penalty, reasons = typing_penalty(current, profile)

        assert penalty == 0
        assert len(reasons) == 0

    def test_typing_penalty_outlier_behavior(self):
        """Test typing penalty with outlier behavior."""
        current = {"wpm": 120, "errorRate": 0.10, "keystrokeTimings": [50, 45, 55]}  # Very fast, high errors
        profile = {
            "baselines": {
                "typing": {
                    "wpm_mean": 60,
                    "wpm_std": 5,
                    "err_mean": 0.02,
                    "err_std": 0.01
                }
            }
        }

        penalty, reasons = typing_penalty(current, profile)

        assert penalty > 0
        assert len(reasons) > 0

    def test_score_login_successful(self):
        """Test successful login scoring."""
        behavioral_challenge = {"wpm": 60, "errorRate": 0.02}
        metrics = {"device_match": True, "location_match": True}
        profile = {"trusted": True}

        result = score_login(behavioral_challenge, metrics, profile)

        assert isinstance(result, dict)
        assert "risk_score" in result
        assert "level" in result

    def test_score_login_high_risk(self):
        """Test high-risk login scoring."""
        behavioral_challenge = {"wpm": 200, "errorRate": 0.50}  # Suspicious behavior
        metrics = {"device_match": False, "location_match": False}
        profile = {"trusted": False}

        result = score_login(behavioral_challenge, metrics, profile)

        assert result["risk_score"] >= 40  # Should be at least medium risk
        assert result["level"] in ["medium", "high"]
