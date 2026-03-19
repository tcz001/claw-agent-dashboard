"""Search API routes — file content search and session search."""
import asyncio

from fastapi import APIRouter, Query, HTTPException

from ..config import AGENTS_DIR, BLUEPRINTS_DIR, ES_URL
from ..services.search_service import search_files

router = APIRouter(tags=["search"])


@router.get("/status")
async def search_status():
    """Return which search capabilities are available."""
    session_search = False
    if ES_URL:
        try:
            from ..services.session_indexer import is_es_available
            session_search = await is_es_available()
        except Exception:
            pass
    return {"file_search": True, "session_search": session_search}


@router.get("/files")
async def search_files_endpoint(
    scope: str = Query(..., pattern="^(agent|blueprint)$"),
    name: str = Query(..., min_length=1),
    query: str = Query(..., min_length=1),
    case_sensitive: bool = Query(False),
    max_results: int = Query(200, ge=1, le=1000),
):
    """Full-text search across files in an agent or blueprint directory."""
    import os

    # Path safety
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Invalid name")

    if scope == "agent":
        search_dir = os.path.join(AGENTS_DIR, name)
    else:
        search_dir = os.path.join(BLUEPRINTS_DIR, name)

    if not os.path.isdir(search_dir):
        raise HTTPException(status_code=404, detail=f"Directory not found: {name}")

    # Run in thread to avoid blocking event loop
    result = await asyncio.to_thread(
        search_files, search_dir, query,
        case_sensitive=case_sensitive, max_results=max_results,
    )
    return result


@router.get("/sessions")
async def search_sessions_endpoint(
    agent_name: str = Query(..., min_length=1),
    query: str = Query(..., min_length=1),
    max_results: int = Query(50, ge=1, le=200),
):
    """Search session messages via Elasticsearch."""
    if not ES_URL:
        raise HTTPException(status_code=503, detail="Elasticsearch not configured")

    try:
        from ..services.session_indexer import search_sessions
        result = await search_sessions(agent_name, query, max_results=max_results)
        return result
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Elasticsearch unavailable")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
