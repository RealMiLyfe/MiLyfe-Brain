"""Hybrid Chat routes — tools + conversation."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from config import settings
from models.schemas import ChatResponse, ChatSendRequest, ChatSession

router = APIRouter()


@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatSendRequest):
    """Send a chat message with optional tool execution."""
    import httpx
    from memory.database import db

    session_id = request.session_id or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    model = request.model or settings.default_heavy_model

    # Store user message
    msg_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO chat_messages (id, session_id, role, content, model, tokens_used, tool_calls, attachments, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (msg_id, session_id, "user", request.message, model, 0, "[]", "[]", now),
    )

    # Build messages from history
    history = await db.fetch_all(
        "SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY created_at",
        (session_id,),
    )
    messages = [{"role": "system", "content": _get_chat_system_prompt()}]
    messages.extend([{"role": row["role"], "content": row["content"]} for row in history])

    # Call Ollama
    tool_calls = []
    tokens_used = 0
    try:
        async with httpx.AsyncClient(timeout=settings.agent_timeout) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("message", {}).get("content", "")
            tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

            # Parse for tool calls if enabled
            if request.tools_enabled:
                from agents.tool_parser import ToolParser
                parsed_tools = ToolParser.parse(response_text)
                if parsed_tools:
                    from tools.registry import tool_registry
                    for tc in parsed_tools:
                        try:
                            result = await tool_registry.execute(tc["name"], tc["params"])
                            tc["result"] = str(result)
                            tool_calls.append(tc)
                        except Exception as e:
                            tc["result"] = f"Error: {str(e)}"
                            tool_calls.append(tc)
    except Exception as e:
        response_text = f"I encountered an error communicating with the language model: {str(e)}"

    # Store assistant response
    resp_id = str(uuid.uuid4())
    resp_now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO chat_messages (id, session_id, role, content, model, tokens_used, tool_calls, attachments, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (resp_id, session_id, "assistant", response_text, model, tokens_used, str(tool_calls), "[]", resp_now),
    )

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        tool_calls=tool_calls,
        model=model,
        tokens_used=tokens_used,
    )


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session."""
    from memory.database import db

    rows = await db.fetch_all(
        "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at", (session_id,)
    )
    return [dict(row) for row in rows]


@router.get("/sessions", response_model=list[ChatSession])
async def list_sessions():
    """List all chat sessions."""
    from memory.database import db

    rows = await db.fetch_all(
        """SELECT session_id, COUNT(*) as msg_count,
                  MIN(created_at) as first_msg, MAX(created_at) as last_msg
           FROM chat_messages GROUP BY session_id ORDER BY last_msg DESC"""
    )
    return [
        ChatSession(
            id=row["session_id"],
            title=f"Session {row['session_id'][:8]}",
            message_count=row["msg_count"],
            created_at=row["first_msg"],
            updated_at=row["last_msg"],
        )
        for row in rows
    ]


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    from memory.database import db

    await db.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    return {"message": "Session deleted", "session_id": session_id}


@router.post("/intervene/{playbook_id}")
async def intervene_playbook(playbook_id: str, request: ChatSendRequest):
    """Intervene in a running playbook with a message."""
    from agents.factory import agent_factory
    from agents.message_bus import message_bus

    await message_bus.send(
        topic="intervention",
        sender_id="user",
        sender_role="user",
        content={"playbook_id": playbook_id, "message": request.message},
    )
    return {"message": "Intervention sent", "playbook_id": playbook_id}


@router.get("/capabilities")
async def get_capabilities():
    """List chat agent capabilities."""
    return {
        "tools_enabled": True,
        "available_models": [settings.default_light_model, settings.default_heavy_model],
        "features": ["tool_execution", "file_context", "code_execution", "web_search"],
    }


def _get_chat_system_prompt() -> str:
    return """You are MiLyfe Brain's chat assistant. You can help with:
- Answering questions about the workspace and projects
- Executing tools (file operations, code, search)
- Providing explanations and suggestions
- Helping plan and debug tasks

When you need to use a tool, output a JSON tool call:
{"tool": "tool_name", "params": {"param1": "value"}}

Be helpful, concise, and accurate."""
