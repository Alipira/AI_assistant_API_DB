"""Pydantic models for chat API"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request from user"""
    message: str = Field(..., description="User's question")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for history")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "How many users do we have in the database?",
                "conversation_id": "conv_123"
            }
        }


class ToolCall(BaseModel):
    """Information about a tool call"""
    tool_name: str
    arguments: dict
    result: Any


class ChatResponse(BaseModel):
    """Chat response to user"""
    message: str = Field(..., description="Assistant's response")
    conversation_id: str = Field(..., description="Conversation ID")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tools used")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "You have 1,250 users in the database.",
                "conversation_id": "conv_123",
                "tool_calls": [
                    {
                        "tool_name": "query_database",
                        "arguments": {"query": "SELECT COUNT(*) FROM users"},
                        "result": {"count": 1250}
                    }
                ]
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    openai: str
