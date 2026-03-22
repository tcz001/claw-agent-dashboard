"""Tests for version restore — agent file restore and blueprint file restore."""
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

# Patch config before importing services
_test_dir = tempfile.mkdtemp(prefix="restore-test-")
os.environ["AGENTS_DIR"] = os.path.join(_test_dir, "agents")
os.environ["DATA_DIR"] = os.path.join(_test_dir, "data")
os.environ["AGENTS_HOST_DIR"] = ""

import backend.app.config as cfg

cfg.AGENTS_DIR = os.path.join(_test_dir, "agents")
cfg.DATA_DIR = os.path.join(_test_dir, "data")
cfg.AGENTS_HOST_DIR = ""
cfg.BLUEPRINTS_DIR = os.path.join(cfg.AGENTS_DIR, "blueprints")

from backend.app.services import version_db, file_service, version_service, blueprint_service


@pytest_asyncio.fixture(autouse=True)
async def fresh_db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "versions.db"
    version_db.DB_PATH = db_path
    if version_db._db is not None:
        await version_db._db.close()
        version_db._db = None
    await version_db.init_db()

    # Point AGENTS_DIR at tmp_path so file_service can write
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    cfg.AGENTS_DIR = str(agents_dir)
    cfg.BLUEPRINTS_DIR = str(agents_dir / "blueprints")
    file_service.AGENTS_DIR = str(agents_dir)

    yield

    if version_db._db is not None:
        await version_db._db.close()
        version_db._db = None


# ---------------------------------------------------------------------------
# Agent file restore
# ---------------------------------------------------------------------------

class TestAgentFileRestore:

    @pytest.mark.asyncio
    async def test_restore_to_previous_version(self, tmp_path):
        """Create agent + file + multiple versions → restore to old → verify file content + new version."""
        agent_name = "workspace-test-restore"
        agents_dir = tmp_path / "agents"

        # Create the workspace and file on disk
        ws_dir = agents_dir / agent_name
        ws_dir.mkdir(parents=True)
        file_path = ws_dir / "CLAUDE.md"
        file_path.write_text("version 1 content", encoding="utf-8")

        # Save v1 via version_service
        v1 = await version_service.save_file_with_version(
            agent_name, "CLAUDE.md", "version 1 content", commit_msg="v1"
        )

        # Update file and save v2
        file_path.write_text("version 2 content", encoding="utf-8")
        v2 = await version_service.save_file_with_version(
            agent_name, "CLAUDE.md", "version 2 content", commit_msg="v2"
        )

        # Verify current file is v2
        assert file_path.read_text() == "version 2 content"

        # Restore to v1
        restored = await version_service.restore_version(v1["id"])

        # File on disk should now be v1 content
        assert file_path.read_text() == "version 1 content"

        # A new version record should be created with source=restore
        assert restored["source"] == "restore"
        assert restored["version_num"] == v2["version_num"] + 1
        assert "Restored from version" in restored["commit_msg"]

    @pytest.mark.asyncio
    async def test_restore_creates_new_version_record(self, tmp_path):
        """Restore should create a new version entry, not overwrite the old one."""
        agent_name = "workspace-test-new-ver"
        ws_dir = tmp_path / "agents" / agent_name
        ws_dir.mkdir(parents=True)
        (ws_dir / "README.md").write_text("original", encoding="utf-8")

        v1 = await version_service.save_file_with_version(
            agent_name, "README.md", "original", commit_msg="initial"
        )
        (ws_dir / "README.md").write_text("modified", encoding="utf-8")
        v2 = await version_service.save_file_with_version(
            agent_name, "README.md", "modified", commit_msg="edit"
        )

        # Restore to v1
        restored = await version_service.restore_version(v1["id"])

        # Should now have 3 versions total
        agent_id = await version_db.get_or_create_agent(agent_name)
        versions, total = await version_db.get_versions(agent_id, "README.md")
        assert total == 3
        # Latest version should be the restore
        assert versions[0]["source"] == "restore"
        assert versions[0]["version_num"] == 3

    @pytest.mark.asyncio
    async def test_restore_invalid_version_id(self):
        """Restore with nonexistent version_id should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await version_service.restore_version(99999)

    @pytest.mark.asyncio
    async def test_restore_updates_tracked_file_hash(self, tmp_path):
        """Restore should update the tracked file hash to prevent scanner re-detection."""
        agent_name = "workspace-test-hash"
        ws_dir = tmp_path / "agents" / agent_name
        ws_dir.mkdir(parents=True)
        (ws_dir / "FILE.md").write_text("v1", encoding="utf-8")

        v1 = await version_service.save_file_with_version(
            agent_name, "FILE.md", "v1", commit_msg="v1"
        )
        (ws_dir / "FILE.md").write_text("v2", encoding="utf-8")
        v2 = await version_service.save_file_with_version(
            agent_name, "FILE.md", "v2", commit_msg="v2"
        )

        await version_service.restore_version(v1["id"])

        # Tracked file hash should match v1 content
        agent_id = await version_db.get_or_create_agent(agent_name)
        tracked = await version_db.get_tracked_file(agent_id, "FILE.md")
        assert tracked is not None
        assert tracked["current_hash"] == version_db.compute_hash("v1")


# ---------------------------------------------------------------------------
# Blueprint file restore
# ---------------------------------------------------------------------------

class TestBlueprintFileRestore:

    async def _create_blueprint_with_file(self, tmp_path, content="# Original"):
        """Helper: create blueprint + template + version + disk file."""
        bp = await blueprint_service.create_blueprint("test-bp", "test")
        await blueprint_service.add_blueprint_file(bp["id"], "SOUL.md", content)

        # Create disk file in blueprints dir
        bp_dir = Path(cfg.BLUEPRINTS_DIR) / "test-bp"
        bp_dir.mkdir(parents=True, exist_ok=True)
        (bp_dir / "SOUL.md").write_text(content, encoding="utf-8")

        return bp

    @pytest.mark.asyncio
    async def test_blueprint_restore_updates_template_and_disk(self, tmp_path):
        """Restore blueprint file → template content and disk file should be updated."""
        bp = await self._create_blueprint_with_file(tmp_path, "# Version 1")

        bp_data = await version_db.get_blueprint(bp["id"])
        agent_id = bp_data["agent_id"]

        # Create a v1 version record
        v1_hash = version_db.compute_hash("# Version 1")
        await version_db.create_version(
            agent_id=agent_id, file_path="SOUL.md",
            content="# Version 1", content_hash=v1_hash,
            source="dashboard", commit_msg="v1",
        )

        # Update template to v2
        template = await version_db.get_template_by_path(agent_id, "SOUL.md")
        await version_db.update_template(template["id"], "# Version 2")
        v2_hash = version_db.compute_hash("# Version 2")
        await version_db.create_version(
            agent_id=agent_id, file_path="SOUL.md",
            content="# Version 2", content_hash=v2_hash,
            source="dashboard", commit_msg="v2",
        )

        # Update disk file to v2
        disk_file = Path(cfg.BLUEPRINTS_DIR) / "test-bp" / "SOUL.md"
        disk_file.write_text("# Version 2", encoding="utf-8")

        # Import the router function to test directly
        from backend.app.routers.blueprints import restore_blueprint_file_version

        result = await restore_blueprint_file_version(bp["id"], "SOUL.md", 1)

        assert result["restored"] is True
        assert result["version_num"] == 1

        # Template should be updated
        template = await version_db.get_template_by_path(agent_id, "SOUL.md")
        assert template["content"] == "# Version 1"

        # Disk file should be updated
        assert disk_file.read_text() == "# Version 1"

    @pytest.mark.asyncio
    async def test_blueprint_restore_creates_new_version(self, tmp_path):
        """Blueprint restore should create a new version record."""
        bp = await self._create_blueprint_with_file(tmp_path, "# Content A")

        bp_data = await version_db.get_blueprint(bp["id"])
        agent_id = bp_data["agent_id"]

        # Create version records
        await version_db.create_version(
            agent_id=agent_id, file_path="SOUL.md",
            content="# Content A", content_hash=version_db.compute_hash("# Content A"),
            source="dashboard", commit_msg="v1",
        )
        await version_db.create_version(
            agent_id=agent_id, file_path="SOUL.md",
            content="# Content B", content_hash=version_db.compute_hash("# Content B"),
            source="dashboard", commit_msg="v2",
        )

        from backend.app.routers.blueprints import restore_blueprint_file_version

        await restore_blueprint_file_version(bp["id"], "SOUL.md", 1)

        # Should now have 3 versions (v1, v2, and the restore)
        versions, total = await version_db.get_versions(agent_id, "SOUL.md")
        assert total == 3
        # Latest version should have the restore commit message
        assert "Restored to version 1" in versions[0]["commit_msg"]

    @pytest.mark.asyncio
    async def test_blueprint_restore_nonexistent_blueprint(self):
        """Restore on nonexistent blueprint should raise HTTPException 404."""
        from backend.app.routers.blueprints import restore_blueprint_file_version
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await restore_blueprint_file_version(99999, "SOUL.md", 1)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_blueprint_restore_nonexistent_version(self, tmp_path):
        """Restore to a nonexistent version_num should raise HTTPException 404."""
        bp = await self._create_blueprint_with_file(tmp_path, "# Content")

        from backend.app.routers.blueprints import restore_blueprint_file_version
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await restore_blueprint_file_version(bp["id"], "SOUL.md", 999)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_blueprint_restore_clears_pending_changes(self, tmp_path):
        """Restore should clear any pending changes for the file."""
        bp = await self._create_blueprint_with_file(tmp_path, "# Original")

        bp_data = await version_db.get_blueprint(bp["id"])
        agent_id = bp_data["agent_id"]

        # Create a version
        await version_db.create_version(
            agent_id=agent_id, file_path="SOUL.md",
            content="# Original", content_hash=version_db.compute_hash("# Original"),
            source="dashboard", commit_msg="v1",
        )

        # Create a pending change
        await version_db.upsert_pending_change(
            blueprint_id=bp["id"], file_path="SOUL.md",
            change_type="modified",
            old_content="# Original", new_content="# Modified",
            old_hash=version_db.compute_hash("# Original"),
            new_hash=version_db.compute_hash("# Modified"),
        )

        # Verify pending change exists
        changes = await version_db.list_pending_changes(bp["id"])
        assert len(changes) == 1

        from backend.app.routers.blueprints import restore_blueprint_file_version
        await restore_blueprint_file_version(bp["id"], "SOUL.md", 1)

        # Pending changes should be cleared
        changes = await version_db.list_pending_changes(bp["id"])
        assert len(changes) == 0
