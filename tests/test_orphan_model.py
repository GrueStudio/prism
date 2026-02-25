"""
Tests for Orphan model.

Tests cover:
- Valid orphan creation
- Required description field
- Priority default and custom values
- Priority bounds validation (when validation is added in Action 3)
- Name regex validation (when validation is added in Action 3)
"""

import pytest
from pydantic import ValidationError

from prism.models.orphan import Orphan


class TestOrphanCreation:
    """Test basic Orphan model creation."""

    def test_create_orphan_minimal(self):
        """Create orphan with required fields only."""
        orphan = Orphan(name="Test Idea", description="A test orphan idea")

        assert orphan.name == "Test Idea"
        assert orphan.description == "A test orphan idea"
        assert orphan.priority == 0  # Default
        assert orphan.uuid is not None

    def test_create_orphan_with_priority(self):
        """Create orphan with custom priority."""
        orphan = Orphan(name="High Priority", description="Important", priority=10)

        assert orphan.priority == 10

    def test_create_orphan_negative_priority(self):
        """Create orphan with negative priority."""
        orphan = Orphan(name="Low Priority", description="Not urgent", priority=-5)

        assert orphan.priority == -5

    def test_create_orphan_uuid_is_unique(self):
        """Each orphan gets a unique UUID."""
        orphan1 = Orphan(name="Idea 1", description="First")
        orphan2 = Orphan(name="Idea 2", description="Second")

        assert orphan1.uuid != orphan2.uuid


class TestOrphanDescriptionRequired:
    """Test that description is required."""

    def test_description_required(self):
        """Creating orphan without description raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Orphan(name="No Description")

        # Check that description field is mentioned in error
        assert "description" in str(exc_info.value).lower()

    def test_description_cannot_be_none(self):
        """Description cannot be None."""
        with pytest.raises(ValidationError):
            Orphan(name="Test", description=None)

    def test_description_empty_string_raises(self):
        """Empty string description raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Orphan(name="Test", description="")

        assert "description" in str(exc_info.value).lower()


class TestOrphanPriority:
    """Test priority field behavior."""

    def test_priority_defaults_to_zero(self):
        """Priority defaults to 0 when not specified."""
        orphan = Orphan(name="Test", description="Default priority")

        assert orphan.priority == 0

    def test_priority_accepts_positive_int(self):
        """Priority accepts positive integers."""
        orphan = Orphan(name="High", description="Important", priority=100)

        assert orphan.priority == 100

    def test_priority_accepts_negative_int(self):
        """Priority accepts negative integers."""
        orphan = Orphan(name="Low", description="Not important", priority=-50)

        assert orphan.priority == -50

    def test_priority_accepts_zero(self):
        """Priority accepts zero explicitly."""
        orphan = Orphan(name="Neutral", description="Medium", priority=0)

        assert orphan.priority == 0

    def test_priority_must_be_int(self):
        """Priority must be an integer."""
        with pytest.raises(ValidationError):
            Orphan(name="Test", description="Float priority", priority=5.5)

    def test_priority_string_converts_via_labels(self):
        """String priority converts to int via labels."""
        orphan_low = Orphan(name="Low", description="Test", priority="low")
        orphan_high = Orphan(name="High", description="Test", priority="high")

        assert orphan_low.priority == -10
        assert orphan_high.priority == 10

    def test_priority_string_unknown_uses_default(self):
        """Unknown string priority uses default value."""
        orphan = Orphan(name="Test", description="Unknown label", priority="unknown")

        assert orphan.priority == 0  # Default

    def test_priority_exceeds_max_raises(self):
        """Priority above max raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Orphan(name="Test", description="Too high", priority=101)

        assert "priority" in str(exc_info.value).lower()

    def test_priority_below_min_raises(self):
        """Priority below min raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Orphan(name="Test", description="Too low", priority=-101)

        assert "priority" in str(exc_info.value).lower()


class TestOrphanName:
    """Test name field behavior."""

    def test_name_required(self):
        """Name is required."""
        with pytest.raises(ValidationError) as exc_info:
            Orphan(description="No name")

        assert "name" in str(exc_info.value).lower()

    def test_name_cannot_be_none(self):
        """Name cannot be None."""
        with pytest.raises(ValidationError):
            Orphan(name=None, description="Test")

    def test_name_empty_string_raises(self):
        """Empty string name raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Orphan(name="", description="Test")

        assert "name" in str(exc_info.value).lower()

    def test_name_with_allowed_special_chars(self):
        """Name accepts allowed special characters (space, hyphen, underscore, quotes)."""
        orphan = Orphan(
            name="Test-Name_With 'Quotes' and \"double\"",
            description="Special chars"
        )

        assert orphan.name == "Test-Name_With 'Quotes' and \"double\""

    def test_name_with_disallowed_special_chars_raises(self):
        """Name rejects disallowed special characters."""
        with pytest.raises(ValidationError) as exc_info:
            Orphan(name="Test! @#$%^&*() Name", description="Special")

        assert "pattern" in str(exc_info.value).lower()

    def test_name_with_unicode_raises(self):
        """Name rejects unicode characters outside ASCII range."""
        with pytest.raises(ValidationError) as exc_info:
            Orphan(name="Idée de test 日本語", description="Unicode")

        assert "pattern" in str(exc_info.value).lower()


class TestOrphanModelFields:
    """Test that Orphan model has correct fields."""

    def test_orphan_has_uuid_field(self):
        """Orphan has uuid field."""
        orphan = Orphan(name="Test", description="Test desc")

        assert hasattr(orphan, "uuid")
        assert isinstance(orphan.uuid, str)

    def test_orphan_has_name_field(self):
        """Orphan has name field."""
        assert "name" in Orphan.model_fields

    def test_orphan_has_description_field(self):
        """Orphan has description field."""
        assert "description" in Orphan.model_fields

    def test_orphan_has_priority_field(self):
        """Orphan has priority field."""
        assert "priority" in Orphan.model_fields

    def test_orphan_no_extra_fields(self):
        """Orphan has only expected fields."""
        # Check only expected fields exist
        expected_fields = {"uuid", "name", "description", "priority"}
        actual_fields = set(Orphan.model_fields.keys())

        assert actual_fields == expected_fields
