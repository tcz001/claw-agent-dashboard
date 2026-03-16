"""Global skills service — lists and reads shared and npm global skills."""
from pathlib import Path

from ..config import GLOBAL_SKILLS_DIR, SHARED_SKILLS_DIR
from .file_service import LANG_MAP


def _detect_language(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return LANG_MAP.get(ext, "plaintext")


def _source_path(source: str) -> Path:
    """Return the base directory for a given source."""
    if source == "shared":
        return Path(SHARED_SKILLS_DIR)
    elif source == "global":
        return Path(GLOBAL_SKILLS_DIR)
    else:
        raise ValueError(f"Unknown source: {source}")


def list_sources() -> list[dict]:
    """List available global skill sources."""
    sources = []
    shared_dir = Path(SHARED_SKILLS_DIR)
    if shared_dir.exists():
        sources.append({
            "source": "shared",
            "name": "Shared Skills",
            "path": str(shared_dir),
        })
    global_dir = Path(GLOBAL_SKILLS_DIR)
    if global_dir.exists():
        sources.append({
            "source": "global",
            "name": "NPM Global Skills",
            "path": str(global_dir),
        })
    return sources


def list_skills(source: str) -> list[dict]:
    """List skills in a global source directory."""
    base = _source_path(source)
    if not base.exists():
        return []

    skills = []
    for entry in sorted(base.iterdir()):
        if entry.is_dir():
            # Try to get skill name from SKILL.md
            skill_md = entry / "SKILL.md"
            display_name = entry.name
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8", errors="replace")
                    for line in content.splitlines():
                        if line.startswith("name:"):
                            display_name = line.split(":", 1)[1].strip()
                            break
                except Exception:
                    pass

            skills.append({
                "name": entry.name,
                "display_name": display_name,
                "path": entry.name,
                "source": source,
            })
    return skills


def list_skill_files(source: str, skill_name: str) -> list[dict]:
    """Recursively list all files in a global skill directory."""
    base = _source_path(source)
    skill_dir = base / skill_name
    if not skill_dir.exists():
        return []

    def _walk(directory: Path, rel_prefix: str) -> list[dict]:
        items = []
        for entry in sorted(directory.iterdir()):
            rel_path = f"{rel_prefix}/{entry.name}" if rel_prefix else entry.name
            full_rel = f"{skill_name}/{rel_path}"
            if entry.is_file():
                items.append({
                    "name": entry.name,
                    "path": full_rel,
                    "type": "file",
                })
            elif entry.is_dir() and entry.name not in {
                ".git", "__pycache__", "node_modules",
            }:
                children = _walk(entry, rel_path)
                items.append({
                    "name": entry.name,
                    "path": full_rel,
                    "type": "directory",
                    "children": children,
                })
        return items

    return _walk(skill_dir, "")


def read_file(source: str, rel_path: str) -> dict | None:
    """Read a file from a global skill source."""
    base = _source_path(source)
    file_path = base / rel_path

    # Security: ensure path doesn't escape base directory
    try:
        file_path = file_path.resolve()
        base_resolved = base.resolve()
        if not str(file_path).startswith(str(base_resolved)):
            return None
    except Exception:
        return None

    if not file_path.exists() or not file_path.is_file():
        return None

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    return {
        "path": rel_path,
        "name": file_path.name,
        "content": content,
        "language": _detect_language(file_path.name),
        "source": source,
        "host_path": str(file_path),
    }
