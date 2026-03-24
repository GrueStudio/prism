"""
Tests for Prism CLI config commands.

Tests cover:
- config show
- config set (simple values)
- config set --add/--remove (lists and dicts)
- Error handling for invalid config operations
"""

import json
import pytest
from click.testing import CliRunner
from prism.cli import cli
from prism.core import PrismCore

@pytest.fixture
def runner(prism_dir, monkeypatch):
    """Create CliRunner with PrismCore patched to use temp directory."""
    original_init = PrismCore.__init__

    def patched_init(self, prism_dir_arg=None, **kwargs):
        # Always use prism_dir from fixture
        original_init(self, prism_dir=prism_dir, **kwargs)

    monkeypatch.setattr(PrismCore, "__init__", patched_init)
    return CliRunner()

class TestConfigShowCommand:
    """Test config show command."""

    def test_show_config(self, runner):
        """Show default configuration."""
        result = runner.invoke(cli, ["config", "show"], catch_exceptions=False)
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "slug_max_length" in data
        assert "slug_filler_words" in data
        assert "bug_types" in data

class TestConfigSetCommand:
    """Test config set command."""

    def test_set_simple_value(self, runner):
        """Set a simple configuration value."""
        result = runner.invoke(
            cli, 
            ["config", "set", "slug_max_length", "100"], 
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "Set 'slug_max_length' to '100'" in result.output
        
        # Verify persistence
        core = PrismCore()
        assert core.config.get_model().slug_max_length == 100

    def test_add_to_list(self, runner):
        """Add a value to a string list."""
        result = runner.invoke(
            cli, 
            ["config", "set", "slug_filler_words", "newword", "--add"], 
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "Added value to 'slug_filler_words'" in result.output
        
        core = PrismCore()
        assert "newword" in core.config.get_model().slug_filler_words

    def test_remove_from_list(self, runner):
        """Remove a value from a string list."""
        # First add it
        runner.invoke(cli, ["config", "set", "slug_filler_words", "testword", "--add"])
        
        result = runner.invoke(
            cli, 
            ["config", "set", "slug_filler_words", "testword", "--remove"], 
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "Removed value from 'slug_filler_words'" in result.output
        
        core = PrismCore()
        assert "testword" not in core.config.get_model().slug_filler_words

    def test_add_bug_type(self, runner):
        """Add a complex bug type object."""
        bug_type_json = '{"name": "Performance", "prefix": "PERF", "description": "Perf issues"}'
        result = runner.invoke(
            cli, 
            ["config", "set", "bug_types", bug_type_json, "--add"], 
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "Added value to 'bug_types'" in result.output
        
        core = PrismCore()
        bug_types = core.config.get_model().bug_types
        assert any(bt.prefix == "PERF" for bt in bug_types)

    def test_remove_bug_type(self, runner):
        """Remove a bug type by prefix."""
        # Default config has 'BUG' prefix
        # First check it exists
        core = PrismCore()
        # Default config might be empty or have BUG. Let's add one if it doesn't.
        if not any(bt.prefix == "BUG" for bt in core.config.get_model().bug_types):
             runner.invoke(cli, ["config", "set", "bug_types", '{"name":"Bug","prefix":"BUG"}', "--add"])

        result = runner.invoke(
            cli, 
            ["config", "set", "bug_types", "BUG", "--remove"], 
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "Removed value from 'bug_types'" in result.output
        
        core = PrismCore()
        bug_types = core.config.get_model().bug_types
        assert not any(bt.prefix == "BUG" for bt in bug_types)

    def test_add_priority_label(self, runner):
        """Add to priority labels dict."""
        label_json = '{"label": "critical", "value": 100}'
        result = runner.invoke(
            cli, 
            ["config", "set", "orphan_priority_labels", label_json, "--add"], 
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "Added value to 'orphan_priority_labels'" in result.output
        
        core = PrismCore()
        assert core.config.get_model().orphan_priority_labels["critical"] == 100

    def test_remove_priority_label(self, runner):
        """Remove from priority labels dict."""
        # Add first
        runner.invoke(
            cli, 
            ["config", "set", "orphan_priority_labels", '{"label": "temp", "value": 1}', "--add"]
        )
        
        result = runner.invoke(
            cli, 
            ["config", "set", "orphan_priority_labels", "temp", "--remove"], 
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "Removed value from 'orphan_priority_labels'" in result.output
        
        core = PrismCore()
        assert "temp" not in core.config.get_model().orphan_priority_labels

class TestConfigErrorHandling:
    """Test error cases for config commands."""

    def test_invalid_key(self, runner):
        """Error when setting nonexistent key."""
        result = runner.invoke(cli, ["config", "set", "nonexistent_key", "value"])
        assert result.exit_code != 0
        assert "Configuration key 'nonexistent_key' not found" in result.output

    def test_add_and_remove_flags(self, runner):
        """Error when using both --add and --remove."""
        result = runner.invoke(
            cli, 
            ["config", "set", "slug_filler_words", "value", "--add", "--remove"]
        )
        assert result.exit_code != 0
        assert "Cannot use --add and --remove at the same time" in result.output

    def test_add_to_non_list_dict(self, runner):
        """Error when using --add on simple value."""
        result = runner.invoke(
            cli, 
            ["config", "set", "slug_max_length", "50", "--add"]
        )
        assert result.exit_code != 0
        assert "is not a list" in result.output

    def test_invalid_json_for_complex_type(self, runner):
        """Error with malformed JSON for bug_types."""
        result = runner.invoke(
            cli, 
            ["config", "set", "bug_types", "{invalid-json}", "--add"]
        )
        assert result.exit_code != 0
        assert "Invalid bug type data" in result.output

    def test_duplicate_in_list(self, runner):
        """Error when adding duplicate to list."""
        # 'the' is a default filler word
        result = runner.invoke(
            cli, 
            ["config", "set", "slug_filler_words", "the", "--add"]
        )
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_missing_json_keys(self, runner):
        """Error when JSON is missing required keys for complex types."""
        # Missing 'value'
        label_json = '{"label": "incomplete"}'
        result = runner.invoke(
            cli, 
            ["config", "set", "orphan_priority_labels", label_json, "--add"]
        )
        assert result.exit_code != 0
        assert "must contain 'label' and 'value' keys" in result.output
