"""Tests for template engine reverse_render."""
import pytest
from backend.app.services.template_engine import reverse_render


class TestReverseRender:
    def test_no_variables_returns_new_content(self):
        """Template with no variables — return new content as-is."""
        result = reverse_render("plain text", {}, "edited text")
        assert result == "edited text"

    def test_unchanged_variable_restored(self):
        """Variable value unchanged → restore !{VAR} placeholder."""
        old_template = "Hello !{NAME}, welcome!"
        variables = {"NAME": "Alice"}
        new_content = "Hello Alice, welcome!"
        result = reverse_render(old_template, variables, new_content)
        assert result == "Hello !{NAME}, welcome!"

    def test_changed_variable_kept_literal(self):
        """Variable value changed → keep literal text."""
        old_template = "Hello !{NAME}, welcome!"
        variables = {"NAME": "Alice"}
        new_content = "Hello Bob, welcome!"
        result = reverse_render(old_template, variables, new_content)
        assert result == "Hello Bob, welcome!"

    def test_multiple_variables_mixed(self):
        """Some variables changed, some not."""
        old_template = "Name: !{NAME}, Role: !{ROLE}."
        variables = {"NAME": "Alice", "ROLE": "Admin"}
        new_content = "Name: Alice, Role: SuperAdmin."
        result = reverse_render(old_template, variables, new_content)
        assert result == "Name: !{NAME}, Role: SuperAdmin."

    def test_appended_content_preserved(self):
        """Content added after last anchor is preserved."""
        old_template = "Hello !{NAME}."
        variables = {"NAME": "Alice"}
        new_content = "Hello Alice. See you later!"
        result = reverse_render(old_template, variables, new_content)
        assert result == "Hello !{NAME}. See you later!"

    def test_anchor_not_found_fallback(self):
        """When anchor text cannot be found, return new content as-is."""
        old_template = "Hello !{NAME}, welcome!"
        variables = {"NAME": "Alice"}
        new_content = "Completely different content"
        result = reverse_render(old_template, variables, new_content)
        assert result == "Completely different content"

    def test_repeated_variable(self):
        """Same variable used twice — both restored if unchanged."""
        old_template = "!{NAME} says hi to !{NAME}."
        variables = {"NAME": "Alice"}
        new_content = "Alice says hi to Alice."
        result = reverse_render(old_template, variables, new_content)
        assert result == "!{NAME} says hi to !{NAME}."

    def test_empty_variable_value(self):
        """Variable resolves to empty string."""
        old_template = "prefix!{SEP}suffix"
        variables = {"SEP": ""}
        new_content = "prefixsuffix"
        result = reverse_render(old_template, variables, new_content)
        assert result == "prefix!{SEP}suffix"

    def test_variable_at_start(self):
        """Variable at the very start of template."""
        old_template = "!{GREETING} world"
        variables = {"GREETING": "Hello"}
        new_content = "Hello world"
        result = reverse_render(old_template, variables, new_content)
        assert result == "!{GREETING} world"

    def test_variable_at_end(self):
        """Variable at the very end of template."""
        old_template = "Hello !{NAME}"
        variables = {"NAME": "Alice"}
        new_content = "Hello Alice"
        result = reverse_render(old_template, variables, new_content)
        assert result == "Hello !{NAME}"

    def test_unresolved_variable_in_old_template(self):
        """Variable in old template not in variables dict — treated as literal anchor."""
        old_template = "Hello !{NAME}, !{UNKNOWN} end"
        variables = {"NAME": "Alice"}
        new_content = "Hello Alice, !{UNKNOWN} end"
        result = reverse_render(old_template, variables, new_content)
        assert result == "Hello !{NAME}, !{UNKNOWN} end"
