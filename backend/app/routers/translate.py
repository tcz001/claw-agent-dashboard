"""Translation API routes."""
import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..services.translate import translate_file, get_translation, translation_exists

router = APIRouter(tags=["translate"])


class TranslateRequest(BaseModel):
    agent: str
    path: str


class BatchTranslateRequest(BaseModel):
    items: list[TranslateRequest]


@router.post("/translate")
async def translate(req: TranslateRequest):
    """Translate a file to Chinese."""
    try:
        result = await translate_file(req.agent, req.path)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.get("/translate/{agent_name}")
async def get_translated_file(agent_name: str, path: str = Query(...)):
    """Get a previously translated file."""
    result = get_translation(agent_name, path)
    if result is None:
        raise HTTPException(status_code=404, detail="Translation not found")
    return result


@router.get("/translate/{agent_name}/exists")
async def check_translation(agent_name: str, path: str = Query(...)):
    """Check if a translation exists."""
    return {"exists": translation_exists(agent_name, path)}


@router.post("/translate/batch")
async def batch_translate(req: BatchTranslateRequest):
    """Batch translate multiple files with streaming progress."""

    async def event_generator():
        total = len(req.items)
        for i, item in enumerate(req.items):
            progress = {
                "type": "progress",
                "current": i + 1,
                "total": total,
                "agent": item.agent,
                "path": item.path,
            }
            yield f"data: {json.dumps(progress)}\n\n"
            try:
                await translate_file(item.agent, item.path)
                result = {
                    "type": "translated",
                    "current": i + 1,
                    "total": total,
                    "agent": item.agent,
                    "path": item.path,
                    "success": True,
                }
                yield f"data: {json.dumps(result)}\n\n"
            except Exception as e:
                error = {
                    "type": "error",
                    "current": i + 1,
                    "total": total,
                    "agent": item.agent,
                    "path": item.path,
                    "success": False,
                    "error": str(e),
                }
                yield f"data: {json.dumps(error)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'total': total})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
