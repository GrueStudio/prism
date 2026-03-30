"""
Tests for temporal functionality (timezone awareness).
"""

from datetime import datetime, timezone, timedelta
import pytest
from prism.utils import to_local_time, parse_date, validate_date_range
from prism.models.base import BaseItem
from prism.models.bug import BugItem, BugType, BugLog
from prism.managers.config_manager import get_config_manager


@pytest.fixture(autouse=True)
def setup_config():
    """Ensure ConfigManager is initialized so utils has reflected config."""
    get_config_manager()


class TestTimezoneAwareness:
    """Test that datetimes are timezone-aware and handled correctly."""

    def test_to_local_time_converts_utc_to_local(self):
        """to_local_time should convert UTC to local time."""
        utc_now = datetime.now(timezone.utc)
        local_now = to_local_time(utc_now)
        
        # They should represent the same point in time
        assert utc_now == local_now
        # Local time should not be UTC (unless the system is in UTC)
        # But we can at least check it has a tzinfo
        assert local_now.tzinfo is not None

    def test_to_local_time_handles_naive_datetime(self):
        """to_local_time should treat naive datetime as UTC."""
        naive_now = datetime.now()
        local_now = to_local_time(naive_now)
        
        assert local_now.tzinfo is not None
        # Should have been treated as UTC and then converted
        assert local_now.utcoffset() is not None

    def test_base_item_uses_utc_by_default(self):
        """BaseItem should use UTC for created_at and updated_at by default."""
        item = BaseItem(name="Test Item", slug="test-item")
        
        assert item.created_at.tzinfo == timezone.utc
        assert item.updated_at.tzinfo == timezone.utc
        
        # Check they are very close to now UTC
        now_utc = datetime.now(timezone.utc)
        assert abs((now_utc - item.created_at).total_seconds()) < 1.0

    def test_bug_item_uses_utc_by_default(self):
        """BugItem should use UTC for created_at and updated_at by default."""
        bug_type = BugType(name="Test", prefix="TST")
        bug = BugItem(bug_type=bug_type, bug_id="TST100326_01", description="Test")
        
        assert bug.created_at.tzinfo == timezone.utc
        assert bug.updated_at.tzinfo == timezone.utc

    def test_bug_log_uses_utc_by_default(self):
        """BugLog should use UTC for created_at by default."""
        log = BugLog(title="Test Log")
        assert log.created_at.tzinfo == timezone.utc

    def test_parse_date_returns_utc_aware(self):
        """parse_date should return a UTC-aware datetime."""
        dt = parse_date("2026-03-30")
        assert dt is not None
        assert dt.tzinfo == timezone.utc
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 30

    def test_validate_date_range_handles_utc(self):
        """validate_date_range should handle UTC-aware datetimes."""
        future_date = datetime.now(timezone.utc) + timedelta(days=365)
        is_valid, error = validate_date_range(future_date)
        assert is_valid
        assert error is None
        
        past_date = datetime.now(timezone.utc) - timedelta(days=365)
        is_valid, error = validate_date_range(past_date)
        assert is_valid
        assert error is None
