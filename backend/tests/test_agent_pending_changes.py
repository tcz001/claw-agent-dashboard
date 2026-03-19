"""Tests for agent_pending_changes DB operations."""
import os
import pytest
import pytest_asyncio

os.environ["AGENTS_DIR"] = "/tmp/test-agents"
os.environ["DATA_DIR"] = "/tmp/test-data"

from backend.app.services import version_db


@pytest_asyncio.fixture(autouse=True)
async def fresh_db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "versions.db"
    version_db.DB_PATH = db_path
    version_db._db = None
    await version_db.init_db()
    yield
    await version_db.close_db()


class TestAgentPendingChanges:
    @pytest.mark.asyncio
    async def test_upsert_creates_new(self):
        agent_id = await version_db.get_or_create_agent("workspace-test")
        result = await version_db.upsert_agent_pending_change(
            agent_id, "test.md", "modified",
            "old", "new", "hash_old", "hash_new",
        )
        assert result is not None
        assert result["file_path"] == "test.md"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self):
        agent_id = await version_db.get_or_create_agent("workspace-test")
        await version_db.upsert_agent_pending_change(
            agent_id, "test.md", "modified", "old", "new1", "h1", "h2",
        )
        result = await version_db.upsert_agent_pending_change(
            agent_id, "test.md", "modified", "old", "new2", "h1", "h3",
        )
        assert result["new_content"] == "new2"
        changes = await version_db.list_agent_pending_changes(agent_id)
        assert len(changes) == 1

    @pytest.mark.asyncio
    async def test_upsert_skips_rejected_same_hash(self):
        agent_id = await version_db.get_or_create_agent("workspace-test")
        result = await version_db.upsert_agent_pending_change(
            agent_id, "test.md", "modified", "old", "new", "h1", "h2",
        )
        await version_db.resolve_agent_pending_change(result["id"], "rejected")
        result2 = await version_db.upsert_agent_pending_change(
            agent_id, "test.md", "modified", "old", "new", "h1", "h2",
        )
        assert result2 is None

    @pytest.mark.asyncio
    async def test_list_returns_only_pending(self):
        agent_id = await version_db.get_or_create_agent("workspace-test")
        r = await version_db.upsert_agent_pending_change(
            agent_id, "a.md", "modified", "old", "new", "h1", "h2",
        )
        await version_db.resolve_agent_pending_change(r["id"], "accepted")
        await version_db.upsert_agent_pending_change(
            agent_id, "b.md", "added", None, "new", None, "h3",
        )
        changes = await version_db.list_agent_pending_changes(agent_id)
        assert len(changes) == 1
        assert changes[0]["file_path"] == "b.md"

    @pytest.mark.asyncio
    async def test_delete_by_file(self):
        agent_id = await version_db.get_or_create_agent("workspace-test")
        await version_db.upsert_agent_pending_change(
            agent_id, "test.md", "modified", "old", "new", "h1", "h2",
        )
        deleted = await version_db.delete_agent_pending_change_by_file(agent_id, "test.md")
        assert deleted is True
        changes = await version_db.list_agent_pending_changes(agent_id)
        assert len(changes) == 0

    @pytest.mark.asyncio
    async def test_resolve_sets_status(self):
        agent_id = await version_db.get_or_create_agent("workspace-test")
        r = await version_db.upsert_agent_pending_change(
            agent_id, "test.md", "modified", "old", "new", "h1", "h2",
        )
        await version_db.resolve_agent_pending_change(r["id"], "accepted")
        change = await version_db.get_agent_pending_change(r["id"])
        assert change["status"] == "accepted"
        assert change["resolved_at"] is not None
