"""
Tests for utility functions in prism.utils module.
"""

import pytest
from datetime import datetime, timedelta

from prism.utils import parse_date, format_date, validate_date_range
from prism.constants import DATE_MAX_YEARS_FUTURE, DATE_MAX_YEARS_PAST


class TestParseDate:
    """Tests for the parse_date function."""

    def test_parse_iso_format(self):
        """Test parsing ISO 8601 format (YYYY-MM-DD)."""
        result = parse_date("2024-12-31")
        assert result == datetime(2024, 12, 31)

    def test_parse_slash_format_yyyy_mm_dd(self):
        """Test parsing YYYY/MM/DD format."""
        result = parse_date("2024/12/31")
        assert result == datetime(2024, 12, 31)

    def test_parse_dd_mm_yyyy_dash(self):
        """Test parsing DD-MM-YYYY format."""
        result = parse_date("31-12-2024")
        assert result == datetime(2024, 12, 31)

    def test_parse_dd_mm_yyyy_slash(self):
        """Test parsing DD/MM/YYYY format."""
        result = parse_date("31/12/2024")
        assert result == datetime(2024, 12, 31)

    def test_parse_mm_dd_yyyy_dash(self):
        """Test parsing MM-DD-YYYY format."""
        result = parse_date("12-31-2024")
        assert result == datetime(2024, 12, 31)

    def test_parse_mm_dd_yyyy_slash(self):
        """Test parsing MM/DD/YYYY format."""
        result = parse_date("12/31/2024")
        assert result == datetime(2024, 12, 31)

    def test_parse_compact_format(self):
        """Test parsing YYYYMMDD format."""
        result = parse_date("20241231")
        assert result == datetime(2024, 12, 31)

    def test_parse_dd_month_yyyy(self):
        """Test parsing 'DD Month YYYY' format."""
        result = parse_date("31 December 2024")
        assert result == datetime(2024, 12, 31)

    def test_parse_dd_mon_yyyy(self):
        """Test parsing 'DD Mon YYYY' format."""
        result = parse_date("31 Dec 2024")
        assert result == datetime(2024, 12, 31)

    def test_parse_month_dd_yyyy(self):
        """Test parsing 'Month DD, YYYY' format."""
        result = parse_date("December 31, 2024")
        assert result == datetime(2024, 12, 31)

    def test_parse_mon_dd_yyyy(self):
        """Test parsing 'Mon DD, YYYY' format."""
        result = parse_date("Dec 31, 2024")
        assert result == datetime(2024, 12, 31)

    def test_parse_invalid_format(self):
        """Test parsing invalid date format returns None."""
        result = parse_date("invalid-date")
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_date("")
        assert result is None

    def test_parse_partial_date(self):
        """Test parsing partial date returns None."""
        result = parse_date("2024-12")
        assert result is None

    def test_parse_with_extra_text(self):
        """Test parsing date with extra text returns None."""
        result = parse_date("2024-12-31 extra")
        assert result is None


class TestFormatDate:
    """Tests for the format_date function."""

    def test_format_date(self):
        """Test formatting a datetime to ISO 8601 format."""
        date = datetime(2024, 12, 31)
        result = format_date(date)
        assert result == "2024-12-31"

    def test_format_date_with_time(self):
        """Test that formatting ignores time component."""
        date = datetime(2024, 12, 31, 23, 59, 59)
        result = format_date(date)
        assert result == "2024-12-31"


class TestValidateDateRange:
    """Tests for the validate_date_range function."""

    def test_valid_date_today(self):
        """Test that today's date is valid."""
        is_valid, error_msg = validate_date_range(datetime.now())
        assert is_valid is True
        assert error_msg is None

    def test_valid_date_future(self):
        """Test that a date in the near future is valid."""
        future_date = datetime.now() + timedelta(days=30)
        is_valid, error_msg = validate_date_range(future_date)
        assert is_valid is True
        assert error_msg is None

    def test_valid_date_recent_past(self):
        """Test that a recent past date is valid."""
        past_date = datetime.now() - timedelta(days=30)
        is_valid, error_msg = validate_date_range(past_date)
        assert is_valid is True
        assert error_msg is None

    def test_invalid_date_too_far_past(self):
        """Test that a date too far in the past is invalid."""
        past_date = datetime.now() - timedelta(days=(DATE_MAX_YEARS_PAST + 1) * 365)
        is_valid, error_msg = validate_date_range(past_date)
        assert is_valid is False
        assert error_msg is not None
        assert "too far in the past" in error_msg

    def test_invalid_date_too_far_future(self):
        """Test that a date too far in the future is invalid."""
        future_date = datetime.now() + timedelta(days=(DATE_MAX_YEARS_FUTURE + 1) * 365)
        is_valid, error_msg = validate_date_range(future_date)
        assert is_valid is False
        assert error_msg is not None
        assert "too far in the future" in error_msg

    def test_valid_date_max_past(self):
        """Test that a date at the maximum past limit is valid."""
        past_date = datetime(datetime.now().year - DATE_MAX_YEARS_PAST, datetime.now().month, datetime.now().day)
        is_valid, error_msg = validate_date_range(past_date)
        assert is_valid is True

    def test_valid_date_max_future(self):
        """Test that a date at the maximum future limit is valid."""
        future_date = datetime(datetime.now().year + DATE_MAX_YEARS_FUTURE, datetime.now().month, datetime.now().day)
        is_valid, error_msg = validate_date_range(future_date)
        assert is_valid is True
