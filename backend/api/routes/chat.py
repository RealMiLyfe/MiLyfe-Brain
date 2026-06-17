"""MiLyfe Brain — Hybrid Chat Routes (tools + conversation)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

import orjson
import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func

from memory.database import ChatMessageRow, ChatSessionRow, async_session_factory
from models.schemas import ChatMessage, ChatSend, ChatSession

logger = structlog.get_logger()
router = APIRouter()


@router.post("/send")
async def send_message(data: ChatSend):
    """Send a message with optional tool execution."""
    session_id = data.session_id or str(uuid.uuid4())

    async with async_session_factory() as session:
        # Ensure session exists
        chat_session = await session.get(ChatSessionRow, session_id)
        if not chat_session:
            chat_session = ChatSessionRow(
                id=session_id,
                title=data.message[:50] if data.message else "New Chat",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(chat_session)

        # Store user message
        user_msg_id = str(uuid.uuid4())
        user_msg = ChatMessageRow(
            id=user_msg_id,
            session_id=session_id,
            role="user",
            content=data.message,
            created_at=datetime.utcnow(),
        )
        session.add(user_msg)
        await session.commit()

    # Generate AI response
    try:
        from agents.factory import agent_factory

        response_data = await agent_factory.chat(
            message=data.message,
            session_id=session_id,
            model_override=data.model_override,
            output_style=data.output_style,
            attachments=data.attachments,
        )

        # Store assistant message
        async with async_session_factory() as session:
            assistant_msg = ChatMessageRow(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=response_data.get("content", ""),
                model=response_data.get("model", ""),
                tokens_used=response_data.get("tokens_used", 0),
                tool_calls=orjson.dumps(response_data.get("tool_calls", [])).decode(),
                created_at=datetime.utcnow(),
            )
            session.add(assistant_msg)

            # Update session
            chat_session = await session.get(ChatSessionRow, session_id)
            if chat_session:
                chat_session.message_count = (chat_session.message_count or 0) + 2
                chat_session.updated_at = datetime.utcnow()

            await session.commit()

        return {
            "session_id": session_id,
            "message_id": assistant_msg.id,
            "content": response_data.get("content", ""),
            "model": response_data.get("model", ""),
            "tokens_used": response_data.get("tokens_used", 0),
            "tool_calls": response_data.get("tool_calls", []),
        }

    except Exception as e:
        logger.error("chat_send_failed", error=str(e))
        # Store error response
        async with async_session_factory() as session:
            error_msg = ChatMessageRow(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=f"Error: {str(e)}",
                created_at=datetime.utcnow(),
            )
            session.add(error_msg)
            await session.commit()

        return {
            "session_id": session_id,
            "content": f"I encountered an error: {str(e)}",
            "error": True,
        }


@router.get("/history/{session_id}", response_model=List[ChatMessage])
async def get_chat_history(session_id: str, limit: int = 100, offset: int = 0):
    """Get chat history for a session."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChatMessageRow)
            .where(ChatMessageRow.session_id == session_id)
            .order_by(ChatMessageRow.created_at)
            .offset(offset)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            ChatMessage(
                id=r.id,
                session_id=r.session_id,
                role=r.role,
                content=r.content,
                model=r.model,
                tokens_used=r.tokens_used or 0,
                tool_calls=orjson.loads(r.tool_calls) if r.tool_calls else [],
                attachments=orjson.loads(r.attachments) if r.attachments else [],
                created_at=r.created_at,
            )
            for r in rows
        ]


@router.get("/sessions", response_model=List[ChatSession])
async def list_sessions():
    """List all chat sessions."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChatSessionRow).order_by(ChatSessionRow.updated_at.desc()).limit(50)
        )
        rows = result.scalars().all()
        return [
            ChatSession(
                id=r.id,
                title=r.title,
                message_count=r.message_count or 0,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session and its messages."""
    async with async_session_factory() as session:
        # Delete messages
        result = await session.execute(
            select(ChatMessageRow).where(ChatMessageRow.session_id == session_id)
        )
        for msg in result.scalars().all():
            await session.delete(msg)

        # Delete session
        chat_session = await session.get(ChatSessionRow, session_id)
        if chat_session:
            await session.delete(chat_session)

        await session.commit()

    return {"detail": "Session deleted", "id": session_id}


@router.post("/intervene/{playbook_id}")
async def intervene_in_playbook(playbook_id: str, data: ChatSend):
    """Intervene in a running playbook."""
    # This sends a message to the orchestrator agent running the playbook
    try:
        from graphs.orchestrator import intervene
        result = await intervene(playbook_id, data.message)
        return {"playbook_id": playbook_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capabilities")
async def get_capabilities():
    """List chat agent capabilities."""
    return {
        "tools": True,
        "file_context": True,
        "code_execution": True,
        "web_browsing": True,
        "output_styles": ["default", "concise", "verbose", "architect", "pair_programmer", "diff_only", "junior_friendly", "tutorial"],
        "slash_commands": ["/review", "/explain", "/fix", "/test", "/refactor", "/doc", "/plan"],
        "max_message_length": 50000,
        "attachments": True,
    }
