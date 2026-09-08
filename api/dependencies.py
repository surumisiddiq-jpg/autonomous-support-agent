# filepath: C:\New folder\autonomous-support-agent\api\dependencies.py
from secrets import compare_digest

from fastapi import Header, HTTPException
from config.settings import settings


def require_api_token(
    x_api_token: str = Header(default=""),
) -> None:
    if not settings.API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="API_TOKEN is not configured.",
        )

    if not compare_digest(x_api_token, settings.API_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid API token.")