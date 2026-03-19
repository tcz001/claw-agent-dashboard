# backend/app/services/search_service.py
"""File content search — recursive directory scan with context lines."""
import os
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".cache", ".venv", "venv"}
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
CONTEXT_LINES = 2


def _is_binary(file_path: str) -> bool:
    """Check if file is binary by looking for null bytes in first 1024 bytes."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except (OSError, IOError):
        return True


def search_files(
    root_dir: str,
    query: str,
    case_sensitive: bool = False,
    max_results: int = 200,
) -> dict:
    """Search file contents recursively under root_dir.

    Returns dict with query, total_matches, and results grouped by file.
    """
    root = Path(root_dir)
    if not root.is_dir():
        return {"query": query, "total_matches": 0, "results": []}

    results = []
    total_matches = 0
    search_query = query if case_sensitive else query.lower()

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded directories (in-place modification)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            if total_matches >= max_results:
                break

            file_path = os.path.join(dirpath, filename)

            # Skip large files
            try:
                if os.path.getsize(file_path) > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            # Skip binary files
            if _is_binary(file_path):
                continue

            # Read and search
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except (OSError, IOError):
                continue

            file_matches = []
            for i, line in enumerate(lines):
                if total_matches >= max_results:
                    break

                compare_line = line if case_sensitive else line.lower()
                if search_query in compare_line:
                    before = [lines[j].rstrip("\n") for j in range(max(0, i - CONTEXT_LINES), i)]
                    after = [lines[j].rstrip("\n") for j in range(i + 1, min(len(lines), i + 1 + CONTEXT_LINES))]
                    file_matches.append({
                        "line_number": i + 1,
                        "line_content": line.rstrip("\n"),
                        "context_before": before,
                        "context_after": after,
                    })
                    total_matches += 1

            if file_matches:
                rel_path = os.path.relpath(file_path, root)
                results.append({"file_path": rel_path, "matches": file_matches})

        if total_matches >= max_results:
            break

    return {"query": query, "total_matches": total_matches, "results": results}
