"""Version management API routes."""
import difflib

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services import version_db, version_service

router = APIRouter(tags=["versions"])


@router.get("/versions/{agent_name}/{file_path:path}")
async def get_file_versions(
    agent_name: str,
    file_path: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get version list for a file (paginated, without content)."""
    agent_id = await version_db.get_or_create_agent(agent_name)
    versions, total = await version_db.get_versions(agent_id, file_path, limit, offset)
    return {"versions": versions, "total": total}


@router.get("/versions/detail/{version_id}")
async def get_version_detail(version_id: int):
    """Get a single version with full content."""
    version = await version_db.get_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


class RestoreRequest(BaseModel):
    version_id: int


@router.post("/versions/{agent_name}/{file_path:path}/restore")
async def restore_file_version(agent_name: str, file_path: str, body: RestoreRequest):
    """Restore a file to a previous version."""
    try:
        version = await version_service.restore_version(body.version_id)
        return {"new_version_id": version["id"], "version_num": version["version_num"]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.get("/versions/{agent_name}/{file_path:path}/diff")
async def get_version_diff(
    agent_name: str,
    file_path: str,
    from_version_id: int = Query(...),
    to_version_id: int = Query(...),
):
    """Get unified diff between two versions."""
    from_ver = await version_db.get_version(from_version_id)
    to_ver = await version_db.get_version(to_version_id)

    if not from_ver or not to_ver:
        raise HTTPException(status_code=404, detail="Version not found")

    from_lines = from_ver["content"].splitlines(keepends=True)
    to_lines = to_ver["content"].splitlines(keepends=True)

    diff = difflib.unified_diff(
        from_lines,
        to_lines,
        fromfile=f"v{from_ver['version_num']}",
        tofile=f"v{to_ver['version_num']}",
    )
    return {"diff": "".join(diff)}
