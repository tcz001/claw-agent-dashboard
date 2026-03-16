"""Settings API routes."""
from fastapi import APIRouter
from pydantic import BaseModel

from ..services.config import read_config, write_config

router = APIRouter(tags=["settings"])


class SettingsUpdate(BaseModel):
    llm: dict = {}
    features: dict = {}


@router.get("/settings")
async def get_settings():
    """Get current settings with masked API keys."""
    config = read_config()
    # Mask API keys
    default_llm = config.get("llm", {}).get("default", {})
    if default_llm.get("api_key"):
        key = default_llm["api_key"]
        default_llm["api_key_masked"] = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
    overrides = config.get("llm", {}).get("overrides", {})
    for _purpose, cfg in overrides.items():
        if cfg.get("api_key"):
            key = cfg["api_key"]
            cfg["api_key_masked"] = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
    return config


@router.put("/settings")
async def update_settings(settings: SettingsUpdate):
    """Update settings."""
    result = write_config(settings.model_dump())
    return {"status": "ok", "settings": result}
