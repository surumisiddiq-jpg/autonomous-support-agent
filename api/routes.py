from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter

from api.dependencies import require_api_token
from api.limiter import limiter
from service.agent_service import start_agent, decide_agent

router = APIRouter(prefix="/api/v1")


class CustomerChatPayload(BaseModel):
    thread_id: str
    user_message: str = Field(min_length=1, max_length=4000)


class AdminOverridePayload(BaseModel):
    thread_id: str
    action: str


@router.post(
    "/agent/chat",
    dependencies=[Depends(require_api_token)],
)
@limiter.limit("10/minute")
def chat(request: Request, payload: CustomerChatPayload):
    try:
        return start_agent(payload.thread_id, payload.user_message)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.post(
    "/admin/override",
    dependencies=[Depends(require_api_token)],
)
@limiter.limit("5/minute")
def override(request: Request, payload: AdminOverridePayload):
    try:
        return decide_agent(payload.thread_id, payload.action)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))