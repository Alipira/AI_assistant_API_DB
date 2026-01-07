"""Chat API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.chat import ChatRequest, ChatResponse
from app.db.session import get_db
from app.core.llm import LLMClient
import uuid

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Chat endpoint - send a message and get a response

    The assistant can query your database to answer questions about your data.
    """
    try:
        # Initialize LLM client
        llm = LLMClient()

        # Process message
        response_message, tool_calls = llm.chat(
            user_message=request.message,
            db=db
        )

        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())

        return ChatResponse(
            message=response_message,
            conversation_id=conversation_id,
            tool_calls=tool_calls
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )
