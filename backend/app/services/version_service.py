"""Version service — core business logic for file versioning."""
import asyncio

from . import version_db, file_service, summary_service
from .config import read_config


async def save_file_with_version(
    agent_name: str,
    rel_path: str,
    content: str,
    commit_msg: str | None = None,
) -> dict:
    """Save file via agent-preview and create a version (source=app)."""
    # Write file to disk
    file_service.write_file(agent_name, rel_path, content)

    # Create version
    content_hash = version_db.compute_hash(content)
    agent_id = await version_db.get_or_create_agent(agent_name)
    version = await version_db.create_version(
        agent_id=agent_id,
        file_path=rel_path,
        content=content,
        content_hash=content_hash,
        source="app",
        commit_msg=commit_msg,
    )

    # Update tracked file hash to prevent scanner from re-detecting
    await version_db.upsert_tracked_file(agent_id, rel_path, content_hash)

    # Trigger async summary if enabled and no commit msg
    _maybe_trigger_summary(version, agent_id, rel_path)

    return version


async def restore_version(version_id: int) -> dict:
    """Restore a file to a previous version. Creates a new version with source=restore."""
    target = await version_db.get_version(version_id)
    if not target:
        raise ValueError(f"Version {version_id} not found")

    # Need to find agent workspace_name from agent_id
    db = await version_db.get_db()
    cursor = await db.execute("SELECT workspace_name FROM agents WHERE id = ?", (target["agent_id"],))
    agent_row = await cursor.fetchone()
    if not agent_row:
        raise ValueError("Agent not found")

    agent_name = agent_row["workspace_name"]
    rel_path = target["file_path"]

    # Write content back to file
    file_service.write_file(agent_name, rel_path, target["content"])

    # Create restore version
    content_hash = version_db.compute_hash(target["content"])
    restore_msg = f"Restored from version {target['version_num']}"
    version = await version_db.create_version(
        agent_id=target["agent_id"],
        file_path=rel_path,
        content=target["content"],
        content_hash=content_hash,
        source="restore",
        commit_msg=restore_msg,
    )

    # Update tracked file hash
    await version_db.upsert_tracked_file(target["agent_id"], rel_path, content_hash)

    return version


async def record_external_change(
    agent_id: int,
    file_path: str,
    content: str,
    content_hash: str,
    likely_openclaw: bool = False,
) -> dict:
    """Record an externally detected file change."""
    version = await version_db.create_version(
        agent_id=agent_id,
        file_path=file_path,
        content=content,
        content_hash=content_hash,
        source="external",
        likely_openclaw=likely_openclaw,
    )

    await version_db.upsert_tracked_file(agent_id, file_path, content_hash)

    _maybe_trigger_summary(version, agent_id, file_path)

    return version


def _maybe_trigger_summary(version: dict, agent_id: int, file_path: str):
    """Trigger async LLM summary if conditions are met."""
    # Skip if user provided a commit message
    if version.get("commit_msg"):
        return

    config = read_config()
    features = config.get("features", {})
    if not features.get("auto_summary", True):
        return

    asyncio.create_task(
        summary_service.generate_summary(
            version_id=version["id"],
            agent_id=agent_id,
            file_path=file_path,
            version_num=version["version_num"],
        )
    )
