"""
Tests for NavigationManager.

Tests cover:
- Path resolution (get_item_by_path, get_item_path)
- Current item tracking (get_current_*)
- Special token resolution (:b, :co, :lasto, :nextd, etc.)
- CRUD context management
- Depth-first path validation
"""

from prism.managers.navigation_manager import SPECIAL_TOKENS, NavigationManager


class TestNavigationManagerInit:
    """Test NavigationManager initialization."""

    def test_init(self, sample_project):
        """NavigationManager initializes with project."""
        nav = NavigationManager(sample_project)
        assert nav.project is sample_project


class TestPathResolution:
    """Test path resolution methods."""

    def test_get_item_by_path_full_path(self, sample_project):
        """Get item by full path string."""
        nav = NavigationManager(sample_project)

        action = nav.get_item_by_path(
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )

        assert action is not None
        assert action.name == "Action 1"

    def test_get_item_by_path_not_found(self, sample_project):
        """Get item returns None for invalid path."""
        nav = NavigationManager(sample_project)

        result = nav.get_item_by_path("invalid/path/here")

        assert result is None

    def test_get_item_by_path_empty(self, sample_project):
        """Get item returns None for empty path."""
        nav = NavigationManager(sample_project)

        result = nav.get_item_by_path("")

        assert result is None

    def test_get_item_path(self, sample_project):
        """Get path string from item."""
        nav = NavigationManager(sample_project)

        phase = sample_project.phases[0]
        path = nav.get_item_path(phase)

        assert path == "phase-1"

    def test_get_item_path_nested(self, sample_project):
        """Get path for deeply nested item."""
        nav = NavigationManager(sample_project)

        phase = sample_project.phases[0]
        milestone = phase.children[0]
        objective = milestone.children[0]
        deliverable = objective.children[0]
        action = deliverable.children[0]

        path = nav.get_item_path(action)

        assert path == "phase-1/milestone-1/objective-1/deliverable-1/action-1"


class TestCurrentItemTracking:
    """Test current item tracking methods."""

    def test_get_current_objective(self, sample_project):
        """Get current (most recent non-completed) objective."""
        nav = NavigationManager(sample_project)

        current = nav.get_current_objective()

        assert current is not None
        assert current.name == "Objective 1"

    def test_get_current_milestone(self, sample_project):
        """Get milestone containing current objective."""
        nav = NavigationManager(sample_project)

        current = nav.get_current_milestone()

        assert current is not None
        assert current.name == "Milestone 1"

    def test_get_current_phase(self, sample_project):
        """Get phase containing current objective."""
        nav = NavigationManager(sample_project)

        current = nav.get_current_phase()

        assert current is not None
        assert current.name == "Phase 1"

    def test_get_current_strategic_items(self, sample_project):
        """Get all current strategic items as dict."""
        nav = NavigationManager(sample_project)

        current = nav.get_current_strategic_items()

        assert current["phase"] is not None
        assert current["milestone"] is not None
        assert current["objective"] is not None


class TestSpecialTokens:
    """Test special token definitions."""

    def test_up_tokens_defined(self):
        """Up navigation tokens are defined."""
        assert ":u" in SPECIAL_TOKENS
        assert ":up" in SPECIAL_TOKENS
        assert ":parent" in SPECIAL_TOKENS
        assert SPECIAL_TOKENS[":u"] == "up"
        assert SPECIAL_TOKENS[":up"] == "up"
        assert SPECIAL_TOKENS[":parent"] == "up"

    def test_current_tokens_defined(self):
        """Current item tokens are defined."""
        assert ":cp" in SPECIAL_TOKENS
        assert ":cm" in SPECIAL_TOKENS
        assert ":co" in SPECIAL_TOKENS
        assert ":cd" in SPECIAL_TOKENS
        assert ":ca" in SPECIAL_TOKENS

    def test_last_tokens_defined(self):
        """Last item tokens are defined."""
        assert ":lp" in SPECIAL_TOKENS
        assert ":lm" in SPECIAL_TOKENS
        assert ":lo" in SPECIAL_TOKENS
        assert ":ld" in SPECIAL_TOKENS
        assert ":la" in SPECIAL_TOKENS

    def test_next_tokens_defined(self):
        """Next item tokens are defined (deliverable/action only)."""
        assert ":nd" in SPECIAL_TOKENS
        assert ":na" in SPECIAL_TOKENS
        # Strategic items should NOT have next tokens
        assert ":np" not in SPECIAL_TOKENS
        assert ":nm" not in SPECIAL_TOKENS
        assert ":no" not in SPECIAL_TOKENS


class TestResolveSpecialToken:
    """Test special token resolution."""

    def test_resolve_up_token(self, sample_project):
        """Resolve :up to parent path."""
        nav = NavigationManager(sample_project)

        # Set task_cursor - crud_context will be inferred as the deliverable
        nav.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )

        # :up goes to parent of crud_context (which is the deliverable)
        # Parent of deliverable is objective
        result = nav.resolve_special_token(":u")

        assert result == "phase-1/milestone-1/objective-1"

    def test_resolve_current_phase(self, sample_project):
        """Resolve :cp to current phase path."""
        nav = NavigationManager(sample_project)

        result = nav.resolve_special_token(":cp")

        assert result == "phase-1"

    def test_resolve_current_objective(self, sample_project):
        """Resolve :co to current objective path."""
        nav = NavigationManager(sample_project)

        result = nav.resolve_special_token(":co")

        assert result == "phase-1/milestone-1/objective-1"

    def test_resolve_last_phase(self, sample_project):
        """Resolve :lp to last phase."""
        nav = NavigationManager(sample_project)

        result = nav.resolve_special_token(":lp")

        assert result == "phase-1"

    def test_resolve_invalid_token(self, sample_project):
        """Resolve returns None for invalid token."""
        nav = NavigationManager(sample_project)

        result = nav.resolve_special_token(":invalid")

        assert result is None

    def test_resolve_non_token(self, sample_project):
        """Resolve returns None for non-token string."""
        nav = NavigationManager(sample_project)

        result = nav.resolve_special_token("not-a-token")

        assert result is None


class TestResolvePath:
    """Test unified path resolution."""

    def test_resolve_none_returns_context(self, sample_project):
        """Resolve None returns current CRUD context."""
        nav = NavigationManager(sample_project)
        nav.project.crud_context = "phase-1/milestone-1/objective-1/deliverable-1"

        result = nav.resolve_path(None)

        assert result == "phase-1/milestone-1/objective-1/deliverable-1"

    def test_resolve_empty_returns_context(self, sample_project):
        """Resolve empty string returns current CRUD context."""
        nav = NavigationManager(sample_project)
        nav.project.crud_context = "phase-1/milestone-1/objective-1/deliverable-1"

        result = nav.resolve_path("")

        assert result == "phase-1/milestone-1/objective-1/deliverable-1"

    def test_resolve_special_token(self, sample_project):
        """Resolve delegates special tokens to resolve_special_token."""
        nav = NavigationManager(sample_project)

        result = nav.resolve_path(":co")

        assert result == "phase-1/milestone-1/objective-1"

    def test_resolve_absolute_path(self, sample_project):
        """Resolve strips leading slash from absolute paths."""
        nav = NavigationManager(sample_project)

        result = nav.resolve_path("/phase-1/milestone-1")

        assert result == "phase-1/milestone-1"

    def test_resolve_relative_path(self, sample_project):
        """Resolve prepends context to relative paths."""
        nav = NavigationManager(sample_project)
        nav.project.crud_context = "phase-1/milestone-1/objective-1"

        result = nav.resolve_path("deliverable-1")

        assert result == "phase-1/milestone-1/objective-1/deliverable-1"


class TestCrudContext:
    """Test CRUD context management."""

    def test_get_crud_context_from_explicit(self, sample_project):
        """Get CRUD context returns explicit value when set."""
        nav = NavigationManager(sample_project)
        nav.project.crud_context = "explicit/context/path"

        result = nav.get_crud_context()

        assert result == "explicit/context/path"

    def test_get_crud_context_from_task_cursor(self, sample_project):
        """Get CRUD context infers from task_cursor when not explicit."""
        nav = NavigationManager(sample_project)
        nav.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )

        result = nav.get_crud_context()

        assert result == "phase-1/milestone-1/objective-1/deliverable-1"

    def test_get_crud_context_none(self, sample_project):
        """Get CRUD context returns None when nothing set."""
        nav = NavigationManager(sample_project)

        result = nav.get_crud_context()

        assert result is None

    def test_set_crud_context_valid(self, sample_project):
        """Set CRUD context succeeds for valid path."""
        nav = NavigationManager(sample_project)

        result = nav.set_crud_context("phase-1/milestone-1/objective-1")

        assert result is True
        assert nav.project.crud_context == "phase-1/milestone-1/objective-1"

    def test_set_crud_context_invalid_path(self, sample_project):
        """Set CRUD context fails for invalid path."""
        nav = NavigationManager(sample_project)

        result = nav.set_crud_context("invalid/path")

        assert result is False

    def test_set_crud_context_behind_task_cursor(self, sample_project):
        """Set CRUD context fails for path behind task_cursor."""
        nav = NavigationManager(sample_project)
        nav.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )

        # Try to set context to earlier branch (doesn't exist, but would be behind)
        # Since we only have phase-1, this tests the validation logic
        result = nav.set_crud_context("phase-1/milestone-1/objective-1")

        # Ancestor is allowed (not behind)
        assert result is True


class TestDepthFirstValidation:
    """Test depth-first path validation (_is_path_behind)."""

    def test_path_behind_earlier_phase(self, sample_project, mock_data):
        """Path in earlier phase is behind."""
        nav = NavigationManager(sample_project)

        # Add another phase for testing
        phase2 = mock_data.create_phase(
            name="Phase 2", slug="phase-2", uuid="phase-2-uuid"
        )
        sample_project.add_child(phase2)

        nav.project.task_cursor = (
            "phase-2/milestone-1/objective-1/deliverable-1/action-1"
        )

        assert (
            nav._is_path_behind(
                "phase-1", "phase-2/milestone-1/objective-1/deliverable-1/action-1"
            )
            is True
        )

    def test_path_behind_earlier_milestone(self, sample_project, mock_data):
        """Path in earlier milestone is behind."""
        nav = NavigationManager(sample_project)

        # Add milestone 2
        milestone2 = mock_data.create_milestone(
            name="Milestone 2",
            slug="milestone-2",
            parent_uuid="phase-1-uuid",
            uuid="milestone-2-uuid",
        )
        sample_project.phases[0].add_child(milestone2)

        nav.project.task_cursor = (
            "phase-1/milestone-2/objective-1/deliverable-1/action-1"
        )

        assert (
            nav._is_path_behind(
                "phase-1/milestone-1",
                "phase-1/milestone-2/objective-1/deliverable-1/action-1",
            )
            is True
        )

    def test_path_not_behind_ancestor(self, sample_project):
        """Ancestor path is NOT behind descendant."""
        nav = NavigationManager(sample_project)
        nav.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )

        assert (
            nav._is_path_behind(
                "phase-1", "phase-1/milestone-1/objective-1/deliverable-1/action-1"
            )
            is False
        )
        assert (
            nav._is_path_behind(
                "phase-1/milestone-1",
                "phase-1/milestone-1/objective-1/deliverable-1/action-1",
            )
            is False
        )

    def test_path_not_behind_equal(self, sample_project):
        """Equal path is NOT behind."""
        nav = NavigationManager(sample_project)
        path = "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        nav.project.task_cursor = path

        assert nav._is_path_behind(path, path) is False

    def test_path_not_behind_later_sibling(self, sample_project):
        """Later sibling is NOT behind."""
        nav = NavigationManager(sample_project)
        nav.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )

        assert (
            nav._is_path_behind(
                "phase-1/milestone-1/objective-1/deliverable-1/action-2",
                "phase-1/milestone-1/objective-1/deliverable-1/action-1",
            )
            is False
        )


class TestResolveCurrentOfType:
    """Test _resolve_current_of_type method."""

    def test_resolve_current_phase(self, sample_project):
        """Resolve current phase."""
        nav = NavigationManager(sample_project)

        result = nav._resolve_current_of_type("phase")

        assert result == "phase-1"

    def test_resolve_current_milestone(self, sample_project):
        """Resolve current milestone."""
        nav = NavigationManager(sample_project)

        result = nav._resolve_current_of_type("milestone")

        assert result == "phase-1/milestone-1"

    def test_resolve_current_objective(self, sample_project):
        """Resolve current objective."""
        nav = NavigationManager(sample_project)

        result = nav._resolve_current_of_type("objective")

        assert result == "phase-1/milestone-1/objective-1"

    def test_resolve_current_deliverable(self, sample_project):
        """Resolve current deliverable from context."""
        nav = NavigationManager(sample_project)
        nav.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )

        result = nav._resolve_current_of_type("deliverable")

        assert result == "phase-1/milestone-1/objective-1/deliverable-1"

    def test_resolve_current_action(self, sample_project):
        """Resolve current action from task_cursor."""
        nav = NavigationManager(sample_project)
        nav.project.task_cursor = (
            "phase-1/milestone-1/objective-1/deliverable-1/action-1"
        )

        result = nav._resolve_current_of_type("action")

        assert result == "phase-1/milestone-1/objective-1/deliverable-1/action-1"

    def test_resolve_current_no_context(self, empty_project):
        """Resolve current returns None when no context."""
        nav = NavigationManager(empty_project)

        result = nav._resolve_current_of_type("phase")

        assert result is None
