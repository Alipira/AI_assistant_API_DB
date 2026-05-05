"""Chat API endpoints"""
import uuid
import time

from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from app.core.logging_config import get_logger
from app.schema.chat_schema import ChatRequest, ChatResponse
from app.core.llm import LLMClient
from app.schema.Auth import AuthContext

router = APIRouter()


def _build_auth_context(
    authorization: Optional[str],
    x_user_id: Optional[str],
    # x_tenant_id is disabled — backend does not support multi-tenancy
    # x_tenant_id: Optional[str],
) -> AuthContext:
    """
    Build an AuthContext from HTTP headers.

    The Bearer token is forwarded to the backend as-is so the backend's
    own authorization service (remote policy check) can validate scopes
    and roles without duplicating that logic here.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header"
        )

    if authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1].strip()
    else:
        access_token = authorization.strip()

    # user_id is required by the backend (sent as X-User-Id header)
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")

    return AuthContext(
        access_token=access_token,
        user_id=x_user_id,
        # tenant_id is disabled — backend does not support multi-tenancy
        # tenant_id=x_tenant_id or "",
    )


logger = get_logger("chat")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None),
    # x_tenant_id is disabled — backend does not support multi-tenancy
    # x_tenant_id: Optional[str] = Header(default=None),
):
    """
    Chat endpoint – send a message and get an AI response.
    The assistant uses backend APIs to answer questions about live data.

    Required headers:
      Authorization: Bearer <token>
      X-User-Id:    <user id>
    """
    start = time.time()
    logger.info(f"REQUEST  conv={request.conversation_id} user={x_user_id} msg_len={len(request.message)}")
    try:
        auth_context = _build_auth_context(authorization, x_user_id)

        llm = LLMClient()

        response_message, tool_calls = llm.chat(
            user_message=request.message,
            auth_context=auth_context,
            conversation_history=request.conversation_history or [],
        )

        conversation_id = request.conversation_id or str(uuid.uuid4())
        elapsed = time.time() - start
        logger.info(f"RESPONSE conv={conversation_id} tool_calls={len(tool_calls)} elapsed={elapsed:.2f}s")
        return ChatResponse(
            message=response_message,
            conversation_id=conversation_id,
            tool_calls=tool_calls,
        )

    except HTTPException as e:
        logger.warning(f"HTTP {e.status_code} conv={request.conversation_id} detail={e.detail}")
        raise
    except Exception as e:
        logger.error(f"UNHANDLED conv={request.conversation_id} error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")
