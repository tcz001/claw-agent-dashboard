"""Change detector — abstract interface + hash-based scanning implementation."""
import asyncio
import os
from abc import ABC, abstractmethod
from pathlib import Path

from ..config import AGENTS_DIR, SESSION_DATA_DIR
from ..services import version_db, version_service
from ..services.file_service import CORE_FILES
from ..services.scanner import list_agents


class ChangeDetector(ABC):
    @abstractmethod
    async def start(self):
        ...

    @abstractmethod
    async def stop(self):
        ...


class HashScanDetector(ChangeDetector):
    """Periodic hash-based file change detection."""

    def __init__(self, interval: int = 30):
        self._interval = interval
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _scan_loop(self):
        while self._running:
            try:
                await self._scan_all()
            except Exception as e:
                print(f"[change_detector] Scan error: {e}")
            await asyncio.sleep(self._interval)

    async def _scan_all(self):
        agents = list_agents()
        for agent in agents:
            agent_name = agent["name"]
            agent_dir = Path(AGENTS_DIR) / agent_name
            if not agent_dir.exists():
                continue

            agent_id = await version_db.get_or_create_agent(agent_name)
            tracked = await version_db.get_all_tracked_files(agent_id)
            tracked_map = {t["file_path"]: t["current_hash"] for t in tracked}

            # Collect managed files: core files + skills
            managed_files = []
            # Core files
            for fname in CORE_FILES:
                fpath = agent_dir / fname
                if fpath.exists() and fpath.is_file():
                    managed_files.append((fname, fpath))
            # Other .md files in root
            for fpath in agent_dir.iterdir():
                if fpath.is_file() and fpath.suffix.lower() == ".md" and fpath.name not in CORE_FILES:
                    managed_files.append((fpath.name, fpath))

            # Skills files (recursive)
            skills_dir = agent_dir / "skills"
            if skills_dir.exists():
                for root, _dirs, files in os.walk(skills_dir):
                    for fname in files:
                        full_path = Path(root) / fname
                        rel_path = str(full_path.relative_to(agent_dir))
                        managed_files.append((rel_path, full_path))

            # Check each file
            seen_paths = set()
            for rel_path, full_path in managed_files:
                seen_paths.add(rel_path)
                try:
                    content = full_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                content_hash = version_db.compute_hash(content)

                if rel_path in tracked_map:
                    # Known file — check if changed
                    if content_hash != tracked_map[rel_path]:
                        likely_openclaw = self._check_likely_openclaw(agent_name)
                        await version_service.record_external_change(
                            agent_id=agent_id,
                            file_path=rel_path,
                            content=content,
                            content_hash=content_hash,
                            likely_openclaw=likely_openclaw,
                        )
                else:
                    # New file — create initial version
                    await version_db.create_version(
                        agent_id=agent_id,
                        file_path=rel_path,
                        content=content,
                        content_hash=content_hash,
                        source="external",
                    )
                    await version_db.upsert_tracked_file(agent_id, rel_path, content_hash)

    def _check_likely_openclaw(self, agent_name: str) -> bool:
        """Heuristic: check if any .jsonl.lock files exist for this agent."""
        # OpenClaw session data path
        short_name = agent_name.replace("workspace-", "")
        session_dir = Path(SESSION_DATA_DIR) / f"agents/{short_name}"
        if not session_dir.exists():
            # Try alternate path structure
            session_dir = Path(SESSION_DATA_DIR) / short_name
        if not session_dir.exists():
            return False

        try:
            for entry in session_dir.iterdir():
                if entry.name.endswith(".jsonl.lock"):
                    return True
        except Exception:
            pass
        return False


# Module-level singleton
_detector: ChangeDetector | None = None


async def start_detector(interval: int = 30):
    global _detector
    _detector = HashScanDetector(interval=interval)
    await _detector.start()


async def stop_detector():
    global _detector
    if _detector:
        await _detector.stop()
        _detector = None
