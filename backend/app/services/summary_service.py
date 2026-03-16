"""Summary service — async LLM-generated version change summaries."""
import httpx

from . import version_db
from .config import get_llm_config


async def generate_summary(
    version_id: int,
    agent_id: int,
    file_path: str,
    version_num: int,
):
    """Generate an AI summary for a version by comparing with previous version."""
    try:
        config = get_llm_config("version_summary")
        if not config.get("openai_base_url") or not config.get("api_key"):
            return  # LLM not configured, skip silently

        # Get current and previous version content
        current = await version_db.get_version(version_id)
        if not current:
            return

        previous = await version_db.get_previous_version(agent_id, file_path, version_num)

        if previous:
            prompt = (
                f"文件 `{file_path}` 发生了变更。请用一句简短的中文描述变更内容。\n\n"
                f"--- 旧版本 ---\n{previous['content'][:2000]}\n\n"
                f"--- 新版本 ---\n{current['content'][:2000]}"
            )
        else:
            prompt = (
                f"文件 `{file_path}` 是新创建的初始版本。请用一句简短的中文描述文件内容。\n\n"
                f"--- 内容 ---\n{current['content'][:2000]}"
            )

        base_url = config["openai_base_url"].rstrip("/")
        api_key = config["api_key"]
        model = config.get("model_name", "gpt-4o-mini")

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是文件版本变更摘要生成器。只输出一句简短的中文摘要，不要解释。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 100,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        summary = data["choices"][0]["message"]["content"].strip()
        await version_db.update_summary(version_id, summary)

    except Exception as e:
        # Silently fail — summary is non-critical
        print(f"[summary_service] Failed to generate summary for version {version_id}: {e}")
