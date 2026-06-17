"""
MiLyfe Brain - Chat Route

Hybrid chat interface with session management and tool execution.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, func, select, update

from memory.database import (
    ChatMessageRow,
    ChatSessionRow,
    async_session_factory,
)
from models.schemas import ChatMessage, ChatSend, ChatSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/send", response_model=ChatMessage)
async def send_message(body: ChatSend) -> ChatMessage:
    """Send a chat message and get an AI response (with tool execution)."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    session_id = body.session_id or str(uuid4())
    now = datetime.utcnow()

    # Ensure session exists
    async with async_session_factory() as db:
        result = await db.execute(
            select(ChatSessionRow).where(ChatSessionRow.id == session_id)
        )
        session_row = result.scalar_one_or_none()

        if session_row is None:
            session_row = ChatSessionRow(
                id=session_id,
                title=body.content[:80],
                topic="general",
                message_count=0,
                created_at=now,
                updated_at=now,
            )
            db.add(session_row)

        # Save user message
        user_msg_id = str(uuid4())
        user_msg = ChatMessageRow(
            id=user_msg_id,
            session_id=session_id,
            role="user",
            content=body.content,
            metadata_json=json.dumps({"output_style": body.output_style.value}),
            timestamp=now,
        )
        db.add(user_msg)

        # Update session count
        await db.execute(
            update(ChatSessionRow)
            .where(ChatSessionRow.id == session_id)
            .values(message_count=ChatSessionRow.message_count + 1, updated_at=now)
        )

        await db.commit()

    # Generate AI response
    assistant_content = await _generate_response(session_id, body.content, body.model)

    # Save assistant message
    assistant_msg_id = str(uuid4())
    response_time = datetime.utcnow()

    async with async_session_factory() as db:
        assistant_msg = ChatMessageRow(
            id=assistant_msg_id,
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            metadata_json=json.dumps({"model": body.model}),
            timestamp=response_time,
        )
        db.add(assistant_msg)

        await db.execute(
            update(ChatSessionRow)
            .where(ChatSessionRow.id == session_id)
            .values(message_count=ChatSessionRow.message_count + 1, updated_at=response_time)
        )

        await db.commit()

    return ChatMessage(
        id=assistant_msg_id,
        session_id=session_id,
        role="assistant",
        content=assistant_content,
        timestamp=response_time,
    )


@router.get("/history/{session_id}", response_model=List[ChatMessage])
async def get_history(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> List[ChatMessage]:
    """Get chat messages for a session."""
    if async_session_factory is None:
        return []

    async with async_session_factory() as db:
        result = await db.execute(
            select(ChatMessageRow)
            .where(ChatMessageRow.session_id == session_id)
            .order_by(ChatMessageRow.timestamp.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = result.scalars().all()

    return [
        ChatMessage(
            id=row.id,
            session_id=row.session_id,
            role=row.role,
            content=row.content,
            metadata=json.loads(row.metadata_json) if row.metadata_json else {},
            timestamp=row.timestamp,
        )
        for row in rows
    ]


@router.get("/sessions", response_model=List[ChatSession])
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> List[ChatSession]:
    """List chat sessions."""
    if async_session_factory is None:
        return []

    async with async_session_factory() as db:
        result = await db.execute(
            select(ChatSessionRow)
            .order_by(ChatSessionRow.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = result.scalars().all()

    return [
        ChatSession(
            id=row.id,
            title=row.title,
            topic=row.topic,
            created_at=row.created_at,
            updated_at=row.updated_at,
            message_count=row.message_count,
        )
        for row in rows
    ]


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a chat session and all its messages."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with async_session_factory() as db:
        result = await db.execute(
            select(ChatSessionRow).where(ChatSessionRow.id == session_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Session not found")

        await db.execute(
            delete(ChatMessageRow).where(ChatMessageRow.session_id == session_id)
        )
        await db.execute(
            delete(ChatSessionRow).where(ChatSessionRow.id == session_id)
        )
        await db.commit()

    return {"status": "deleted", "session_id": session_id}


async def _generate_response(
    session_id: str,
    user_content: str,
    model_override: Optional[str] = None,
) -> str:
    """Generate an AI response for a chat message using the LLM client."""
    try:
        from tools.llm_client import generate

        # Retrieve recent context
        context_messages: List[Dict[str, str]] = []
        if async_session_factory is not None:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(ChatMessageRow)
                    .where(ChatMessageRow.session_id == session_id)
                    .order_by(ChatMessageRow.timestamp.desc())
                    .limit(10)
                )
                rows = result.scalars().all()
                for row in reversed(rows):
                    context_messages.append({"role": row.role, "content": row.content})

        context_messages.append({"role": "user", "content": user_content})

        response = await generate(
            messages=context_messages,
            model=model_override,
        )
        return response.get("content", "I'm sorry, I couldn't generate a response.")

    except Exception as e:
        logger.error("Chat generation failed: %s", e)
        return f"Error generating response: {str(e)}"
