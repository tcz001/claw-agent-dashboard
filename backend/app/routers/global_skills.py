"""Global skills API routes."""
from fastapi import APIRouter, HTTPException, Query

from ..services import global_skills as gs
from ..services.translate import translation_exists

router = APIRouter(tags=["global-skills"])


@router.get("/global-skills")
async def list_global_skill_sources():
    """List available global skill sources."""
    return gs.list_sources()


@router.get("/global-skills/{source}/skills")
async def list_global_skills(source: str):
    """List skills in a global source."""
    try:
        return gs.list_skills(source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/global-skills/{source}/skill-files/{skill_name}")
async def get_global_skill_files(source: str, skill_name: str):
    """List files in a global skill directory."""
    try:
        return gs.list_skill_files(source, skill_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/global-skills/{source}/file")
async def get_global_file_content(
    source: str, path: str = Query(..., description="Relative file path"),
):
    """Read a file from a global skill source."""
    try:
        result = gs.read_file(source, path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="File not found")
    # Check translation using pseudo-agent name
    pseudo_agent = f"__global_{source}__"
    result["has_translation"] = translation_exists(pseudo_agent, path)
    return result
