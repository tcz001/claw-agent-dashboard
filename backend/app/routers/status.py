"""Status API routes — system metrics, gateway health, agent status, events."""
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..services import status as status_service

router = APIRouter(tags=["status"])


@router.get("/status")
async def get_full_status():
    """Get complete system status (gateway + system + all agents)."""
    return status_service.get_full_status()


@router.get("/status/system")
async def get_system_metrics():
    """Get system memory and load metrics."""
    return status_service.get_system_metrics()


@router.get("/status/gateway")
async def get_gateway_status():
    """Get gateway process status."""
    gw = status_service.get_gateway_status()
    gw["uptime_human"] = status_service._format_uptime(gw["uptime_seconds"]) if gw["running"] else "down"
    return gw


@router.get("/status/agent/{agent_name:path}")
async def get_agent_detail(agent_name: str):
    """
    Get detailed status for a specific agent including:
    - Agent status and sessions (with model, token usage, cache rate)
    - Recent events filtered for this agent
    - Compact gateway/system summary
    """
    return status_service.get_agent_detail(agent_name)


@router.get("/status/session/{agent_name:path}/{session_id}/messages")
async def get_session_messages(
    agent_name: str,
    session_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Get paginated message history for a specific session."""
    return status_service.get_session_messages(agent_name, session_id, offset=offset, limit=limit)


@router.get("/status/events")
async def get_recent_events(
    agent: Optional[str] = Query(None, description="Filter events by agent name"),
    limit: int = Query(100, ge=1, le=500),
):
    """Get recent events parsed from gateway logs."""
    return status_service.get_recent_events(agent_filter=agent, limit=limit)


@router.get("/status/models")
async def get_available_models():
    """Get available models from OpenClaw configuration."""
    return status_service.get_available_models()


class NewSessionRequest(BaseModel):
    agent: str
    model: str | None = None
    message: str
    session_key: str | None = None  # Channel session key for binding


@router.post("/status/session/new")
async def create_new_session(req: NewSessionRequest):
    """Create a new session by proxying to the Gateway API."""
    return await status_service.create_new_session(req.agent, req.model, req.message, req.session_key)
