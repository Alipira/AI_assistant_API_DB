"""Pydantic models for chat API"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's question")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    conversation_history: Optional[List[ChatMessage]] = Field(None, description="Prior messages")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "volvo FH12 91-ع-587-15",
            "conversation_id": "conv_123",
            "conversation_history": [
                {"role": "user", "content": "ماشین 587 کجاست؟"},
                {"role": "assistant", "content": "چندین خودرو یافت شد، کدام را می‌خواهید؟"}
            ]
        }
    })


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict
    result: Any


class ChatResponse(BaseModel):
    message: str = Field(..., description="Assistant's response")
    conversation_id: str = Field(..., description="Conversation ID")
    tool_calls: List[ToolCall] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "ماشین ۲۱۱ در مسیر تهران-قم است با سرعت ۸۰ کیلومتر بر ساعت.",
                "conversation_id": "conv_123",
                "tool_calls": [
                    {
                        "tool_name": "call_backend_api",
                        "arguments": {
                            "action": "vehicle_tracking_current",
                            "params": {"UnitId": "211"},
                            "explanation": "Get current location of vehicle 211"
                        },
                        "result": {"success": True, "data": {"lat": 35.6892, "lon": 51.389, "speed": 80}}
                    }
                ]
            }
        }
    )


class HealthResponse(BaseModel):
    status: str
    openai: str
