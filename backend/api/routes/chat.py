"""Chat API — Conversational interface with agents."""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import ChatMessageModel, get_db
from models.schemas import ChatMessage, ChatSendRequest
from agents.factory import get_agent_factory
from config import settings

router = APIRouter()


@router.post("/send")
async def send_message(
    body: ChatSendRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Send a chat message and get an AI response."""
    session_id = body.session_id or str(uuid.uuid4())

    # Store user message
    user_msg = ChatMessageModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=body.message,
        created_at=datetime.utcnow(),
    )
    db.add(user_msg)

    # Get AI response via agent factory
    factory = get_agent_factory()
    response = await factory.chat(
        message=body.message,
        session_id=session_id,
        model=body.model,
    )

    # Store assistant message
    assistant_msg = ChatMessageModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=response,
        model=body.model or settings.default_heavy_model,
        created_at=datetime.utcnow(),
    )
    db.add(assistant_msg)
    await db.commit()

    return {
        "session_id": session_id,
        "response": response,
        "model": body.model or settings.default_heavy_model,
    }


@router.get("/history/{session_id}", response_model=List[ChatMessage])
async def get_chat_history(
    session_id: str, db: AsyncSession = Depends(get_db)
) -> List[ChatMessage]:
    """Get chat history for a session."""
    result = await db.execute(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == session_id)
        .order_by(ChatMessageModel.created_at.asc())
    )
    rows = result.scalars().all()

    return [
        ChatMessage(
            id=row.id,
            session_id=row.session_id,
            role=row.role,
            content=row.content,
            model=row.model,
            tokens_used=row.tokens_used or 0,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)) -> dict:
    """List all chat sessions."""
    result = await db.execute(
        select(
            ChatMessageModel.session_id,
            ChatMessageModel.created_at,
        )
        .distinct(ChatMessageModel.session_id)
        .order_by(ChatMessageModel.created_at.desc())
    )
    rows = result.all()

    sessions = [
        {"session_id": row[0], "created_at": row[1].isoformat() if row[1] else None}
        for row in rows
    ]

    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete all messages in a chat session."""
    await db.execute(
        delete(ChatMessageModel).where(ChatMessageModel.session_id == session_id)
    )
    await db.commit()

    return {"message": "Session deleted", "session_id": session_id}


@router.get("/capabilities")
async def get_capabilities() -> dict:
    """Get available chat capabilities and configuration."""
    return {
        "models": {
            "light": settings.default_light_model,
            "heavy": settings.default_heavy_model,
            "premium": settings.premium_model,
        },
        "features": {
            "tool_use": True,
            "file_context": True,
            "multi_model": True,
            "streaming": True,
        },
        "limits": {
            "max_message_length": 32000,
            "context_window": settings.context_summarize_threshold,
        },
    }
