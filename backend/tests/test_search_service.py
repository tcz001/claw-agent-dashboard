# backend/tests/test_search_service.py
"""Tests for file content search service."""
import os
import sys
from pathlib import Path

import pytest

os.environ["AGENTS_DIR"] = "/tmp/test-agents-search"
os.environ["DATA_DIR"] = "/tmp/test-data-search"

from backend.app.services.search_service import search_files


@pytest.fixture
def search_dir(tmp_path):
    """Create a temp directory with test files."""
    (tmp_path / "hello.md").write_text("line one\nline two has hello world\nline three\nline four\nline five")
    skills_dir = tmp_path / "skills" / "greet"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# Greeting Skill\n\ndef hello_world():\n    print('hello')\n    return True")
    (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02\x03")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("should be skipped")
    return tmp_path


class TestSearchFiles:
    def test_basic_search(self, search_dir):
        results = search_files(str(search_dir), "hello", case_sensitive=False, max_results=200)
        assert results["query"] == "hello"
        assert results["total_matches"] > 0
        file_paths = [r["file_path"] for r in results["results"]]
        assert "hello.md" in file_paths

    def test_case_insensitive(self, search_dir):
        results = search_files(str(search_dir), "HELLO", case_sensitive=False, max_results=200)
        assert results["total_matches"] > 0

    def test_case_sensitive(self, search_dir):
        results = search_files(str(search_dir), "HELLO", case_sensitive=True, max_results=200)
        assert results["total_matches"] == 0

    def test_context_lines(self, search_dir):
        results = search_files(str(search_dir), "hello world", case_sensitive=False, max_results=200)
        match = results["results"][0]["matches"][0]
        assert match["line_number"] == 2
        assert "hello world" in match["line_content"]
        assert len(match["context_before"]) <= 2
        assert len(match["context_after"]) <= 2

    def test_skips_binary(self, search_dir):
        results = search_files(str(search_dir), "\x00", case_sensitive=False, max_results=200)
        file_paths = [r["file_path"] for r in results["results"]]
        assert "binary.bin" not in file_paths

    def test_skips_git_dir(self, search_dir):
        results = search_files(str(search_dir), "skipped", case_sensitive=False, max_results=200)
        file_paths = [r["file_path"] for r in results["results"]]
        assert not any(".git" in p for p in file_paths)

    def test_max_results_limit(self, search_dir):
        results = search_files(str(search_dir), "line", case_sensitive=False, max_results=2)
        assert results["total_matches"] <= 2

    def test_nested_file_relative_path(self, search_dir):
        results = search_files(str(search_dir), "hello_world", case_sensitive=False, max_results=200)
        file_paths = [r["file_path"] for r in results["results"]]
        assert "skills/greet/SKILL.md" in file_paths

    def test_no_results(self, search_dir):
        results = search_files(str(search_dir), "nonexistent_xyz_999", case_sensitive=False, max_results=200)
        assert results["total_matches"] == 0
        assert results["results"] == []
