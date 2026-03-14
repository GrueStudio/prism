"""
Tests for Bug models.

Tests cover:
- BugType creation and validation
- BugLog creation
- BugItem creation and validation
- Bug ID format validation
- Bug lifecycle status transitions
- Log management
"""

import pytest
from pydantic import ValidationError

from prism.models.bug import BugItem, BugLog, BugStatus, BugType


class TestBugType:
    """Test BugType model."""

    def test_create_bug_type_minimal(self):
        """Create BugType with required fields only."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")

        assert bug_type.name == "Physics Bug"
        assert bug_type.prefix == "PHYS"
        assert bug_type.description is None

    def test_create_bug_type_with_description(self):
        """Create BugType with description."""
        bug_type = BugType(
            name="Physics Bug",
            prefix="PHYS",
            description="Physics engine related bugs"
        )

        assert bug_type.description == "Physics engine related bugs"

    def test_prefix_min_length_2(self):
        """Prefix must be at least 2 characters."""
        with pytest.raises(ValidationError) as exc_info:
            BugType(name="Test", prefix="P")

        assert "prefix" in str(exc_info.value).lower()

    def test_prefix_max_length_4(self):
        """Prefix must be at most 4 characters."""
        with pytest.raises(ValidationError) as exc_info:
            BugType(name="Test", prefix="PHYSX")

        assert "prefix" in str(exc_info.value).lower()

    def test_prefix_must_be_uppercase(self):
        """Prefix must be uppercase letters."""
        with pytest.raises(ValidationError) as exc_info:
            BugType(name="Test", prefix="phys")

        assert "prefix" in str(exc_info.value).lower()

    def test_prefix_must_be_letters_only(self):
        """Prefix must be letters only, no numbers."""
        with pytest.raises(ValidationError) as exc_info:
            BugType(name="Test", prefix="PH1S")

        assert "prefix" in str(exc_info.value).lower()

    def test_prefix_valid_examples(self):
        """Test valid prefix examples."""
        # 2 letters
        bug_type = BugType(name="UI Bug", prefix="UI")
        assert bug_type.prefix == "UI"

        # 3 letters
        bug_type = BugType(name="API Bug", prefix="API")
        assert bug_type.prefix == "API"

        # 4 letters
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        assert bug_type.prefix == "PHYS"


class TestBugLog:
    """Test BugLog model."""

    def test_create_bug_log_minimal(self):
        """Create BugLog with required fields only."""
        log = BugLog(title="Stack Trace")

        assert log.title == "Stack Trace"
        assert log.log_type == "general"
        assert log.metadata is None
        assert log.id is not None
        assert log.created_at is not None

    def test_create_bug_log_with_type(self):
        """Create BugLog with specific log type."""
        log = BugLog(
            title="Error Message",
            log_type="error_log"
        )

        assert log.log_type == "error_log"

    def test_create_bug_log_with_metadata(self):
        """Create BugLog with metadata."""
        metadata = {"file": "game.py", "line": 42}
        log = BugLog(
            title="Error occurred",
            log_type="stack_trace",
            metadata=metadata
        )

        assert log.metadata == metadata

    def test_bug_log_auto_generates_id(self):
        """BugLog auto-generates unique ID."""
        log1 = BugLog(title="First log")
        log2 = BugLog(title="Second log")

        assert log1.id != log2.id


class TestBugItem:
    """Test BugItem model creation and basic fields."""

    def test_create_bug_minimal(self):
        """Create BugItem with required fields only."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(
            bug_type=bug_type,
            bug_id="PHYS100326_01",
            description="Character falls through floor"
        )

        assert bug.bug_type.name == "Physics Bug"
        assert bug.bug_id == "PHYS100326_01"
        assert bug.description == "Character falls through floor"
        assert bug.status == BugStatus.OPEN
        assert bug.counter == 0
        assert bug.steps_to_reproduce is None
        assert bug.root_cause is None
        assert bug.fix_description is None
        assert len(bug.logs) == 0

    def test_create_bug_with_all_fields(self):
        """Create BugItem with all optional fields populated."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(
            bug_type=bug_type,
            bug_id="PHYS100326_01",
            description="Character falls through floor when jumping near walls",
            steps_to_reproduce="1. Start level\n2. Jump near wall\n3. Fall through",
            root_cause="Collision detection fails at wall boundaries",
            fix_description="Added boundary check in collision handler",
            counter=1
        )

        assert bug.steps_to_reproduce == "1. Start level\n2. Jump near wall\n3. Fall through"
        assert bug.root_cause == "Collision detection fails at wall boundaries"
        assert bug.fix_description == "Added boundary check in collision handler"
        assert bug.counter == 1

    def test_bug_uuid_auto_generated(self):
        """BugItem auto-generates UUID."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug1 = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Bug 1")
        bug2 = BugItem(bug_type=bug_type, bug_id="PHYS100326_02", description="Bug 2")

        assert bug1.uuid != bug2.uuid

    def test_bug_timestamps_auto_generated(self):
        """BugItem auto-generates timestamps."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        assert bug.created_at is not None
        assert bug.updated_at is not None

    def test_description_required(self):
        """BugItem requires description."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")

        with pytest.raises(ValidationError) as exc_info:
            BugItem(bug_type=bug_type, bug_id="PHYS100326_01")

        assert "description" in str(exc_info.value).lower()

    def test_description_empty_string_raises(self):
        """BugItem rejects empty description."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")

        with pytest.raises(ValidationError) as exc_info:
            BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="")

        assert "description" in str(exc_info.value).lower()


class TestBugIdValidation:
    """Test bug ID format validation."""

    def test_valid_bug_id_format(self):
        """Valid bug ID format is accepted."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        assert bug.bug_id == "PHYS100326_01"

    def test_bug_id_2_letter_prefix(self):
        """Bug ID with 2-letter prefix."""
        bug_type = BugType(name="UI Bug", prefix="UI")
        bug = BugItem(bug_type=bug_type, bug_id="UI100326_01", description="Test")

        assert bug.bug_id == "UI100326_01"

    def test_bug_id_3_letter_prefix(self):
        """Bug ID with 3-letter prefix."""
        bug_type = BugType(name="API Bug", prefix="API")
        bug = BugItem(bug_type=bug_type, bug_id="API100326_01", description="Test")

        assert bug.bug_id == "API100326_01"

    def test_bug_id_lowercase_prefix_raises(self):
        """Bug ID with lowercase prefix raises error."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")

        with pytest.raises(ValidationError) as exc_info:
            BugItem(bug_type=bug_type, bug_id="phys100326_01", description="Test")

        assert "bug_id" in str(exc_info.value).lower()

    def test_bug_id_wrong_format_raises(self):
        """Bug ID with wrong format raises error."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")

        with pytest.raises(ValidationError) as exc_info:
            BugItem(bug_type=bug_type, bug_id="PHYS-100326-01", description="Test")

        assert "bug_id" in str(exc_info.value).lower()

    def test_bug_id_missing_counter_raises(self):
        """Bug ID missing counter raises error."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")

        with pytest.raises(ValidationError) as exc_info:
            BugItem(bug_type=bug_type, bug_id="PHYS100326", description="Test")

        assert "bug_id" in str(exc_info.value).lower()

    def test_bug_id_wrong_date_format_raises(self):
        """Bug ID with wrong date format raises error."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")

        with pytest.raises(ValidationError) as exc_info:
            BugItem(bug_type=bug_type, bug_id="PHYS20260310_01", description="Test")

        assert "bug_id" in str(exc_info.value).lower()


class TestBugStatus:
    """Test BugStatus enum and status transitions."""

    def test_bug_default_status_is_open(self):
        """Bug default status is OPEN."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        assert bug.status == BugStatus.OPEN

    def test_set_status_from_enum(self):
        """Set status using BugStatus enum."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        bug.set_status(BugStatus.REPRODUCED)

        assert bug.status == BugStatus.REPRODUCED

    def test_set_status_from_string(self):
        """Set status using string value."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        bug.set_status("found")

        assert bug.status == BugStatus.FOUND

    def test_set_status_invalid_string_raises(self):
        """Set status with invalid string raises error."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        with pytest.raises(ValueError):
            bug.set_status("invalid_status")

    def test_all_bug_status_values(self):
        """Test all BugStatus enum values."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")

        for status in BugStatus:
            bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")
            bug.set_status(status)
            assert bug.status == status

    def test_status_lifecycle_progression(self):
        """Test bug status progressing through lifecycle."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        # Initial state
        assert bug.status == BugStatus.OPEN

        # After reproduction
        bug.set_status(BugStatus.REPRODUCED)
        assert bug.status == BugStatus.REPRODUCED

        # After root cause found
        bug.set_status(BugStatus.FOUND)
        assert bug.status == BugStatus.FOUND

        # After fix implemented
        bug.set_status(BugStatus.FIXED)
        assert bug.status == BugStatus.FIXED

        # After fix deployed
        bug.set_status(BugStatus.IMPLEMENTED)
        assert bug.status == BugStatus.IMPLEMENTED

    def test_status_change_updates_timestamp(self):
        """Status change updates the updated_at timestamp."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        original_updated = bug.updated_at

        bug.set_status(BugStatus.REPRODUCED)

        assert bug.updated_at >= original_updated


class TestBugLogManagement:
    """Test bug log management functionality."""

    def test_add_log_basic(self):
        """Add a log entry to bug."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        log = bug.add_log(title="Stack Trace")

        assert len(bug.logs) == 1
        assert bug.logs[0].title == "Stack Trace"
        assert bug.logs[0].log_type == "general"
        assert log == bug.logs[0]

    def test_add_log_with_type(self):
        """Add a log entry with specific type."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        bug.add_log(
            title="Stack Trace",
            log_type="stack_trace"
        )

        assert bug.logs[0].log_type == "stack_trace"

    def test_add_log_with_metadata(self):
        """Add a log entry with metadata."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        metadata = {"file": "game.py", "line": 42}
        bug.add_log(
            title="Error Log",
            log_type="error_log",
            metadata=metadata
        )

        assert bug.logs[0].metadata == metadata

    def test_add_multiple_logs(self):
        """Add multiple log entries."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        bug.add_log(title="First log", log_type="note")
        bug.add_log(title="Second log", log_type="stack_trace")
        bug.add_log(title="Third log", log_type="error_log")

        assert len(bug.logs) == 3
        assert bug.logs[0].log_type == "note"
        assert bug.logs[1].log_type == "stack_trace"
        assert bug.logs[2].log_type == "error_log"

    def test_add_log_updates_timestamp(self):
        """Adding a log updates the updated_at timestamp."""
        bug_type = BugType(name="Physics Bug", prefix="PHYS")
        bug = BugItem(bug_type=bug_type, bug_id="PHYS100326_01", description="Test")

        original_updated = bug.updated_at

        bug.add_log(title="New log entry")

        assert bug.updated_at >= original_updated

