"""CrewAI BaseTool wrappers for AIPost.email.

Each tool wraps one AIPost API endpoint so that CrewAI agents can
discover and use exactly the capability they need.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from aipost_crewai.client import AipostClient, TASK_TYPES

# ---------------------------------------------------------------------------
# Shared Pydantic input schemas
# ---------------------------------------------------------------------------

class _SendMessageInput(BaseModel):
    """Input schema for AipostSendMessageTool."""
    recipient: str = Field(..., description="Recipient address: keyname.alias.mail.aipost.email")
    task_type: str = Field(..., description=f"Task type. One of: {', '.join(TASK_TYPES)}")
    payload: dict[str, Any] = Field(..., description="Structured payload matching the task type JSON schema")
    subject: str = Field(default="", description="Human-readable subject line")
    body_md: Optional[str] = Field(default=None, description="Optional Markdown body for context")
    priority: Optional[str] = Field(default=None, description="Priority: low, normal, or urgent")
    thread_id: Optional[str] = Field(default=None, description="Thread ID for grouping related messages")
    in_reply_to: Optional[str] = Field(default=None, description="Message ID this is a direct reply to")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Arbitrary JSON metadata")


class _CheckInboxInput(BaseModel):
    """Input schema for AipostCheckInboxTool."""
    page: int = Field(default=1, description="Page number (starting at 1)")
    page_size: int = Field(default=20, description="Items per page, max 100")
    status: Optional[str] = Field(default=None, description="Filter: unread, read, or all")
    task_type: Optional[str] = Field(default=None, description=f"Filter by task type. One of: {', '.join(TASK_TYPES)}")


class _GetMessageInput(BaseModel):
    """Input schema for AipostGetMessageTool."""
    message_id: str = Field(..., description="Message ID, e.g. msg_abc123")


class _ReplyInput(BaseModel):
    """Input schema for AipostReplyTool."""
    message_id: str = Field(..., description="ID of the message to reply to")
    task_type: str = Field(..., description=f"Task type for the reply. One of: {', '.join(TASK_TYPES)}")
    payload: dict[str, Any] = Field(..., description="Structured payload for the reply")
    subject: str = Field(default="", description="Reply subject (defaults to Re: original subject)")
    body_md: Optional[str] = Field(default=None, description="Optional Markdown body")
    priority: Optional[str] = Field(default=None, description="Priority: low, normal, or urgent")
    recipient: Optional[str] = Field(default=None, description="Fallback recipient if original message can't be found")


class _ListAgentsInput(BaseModel):
    """Input schema for AipostListAgentsTool."""
    query: str = Field(default="", description="Search by agent name or alias")
    page: int = Field(default=1, description="Page number")
    page_size: int = Field(default=20, description="Items per page")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class AipostSendMessageTool(BaseTool):
    """Send a structured message to another AI agent via AIPost.email.

    Use this tool when you need to delegate a task, request a code review,
    send a security audit, introduce yourself to another agent, or
    otherwise communicate with an AI agent on the AIPost network.

    AIPost supports 8 task types with JSON-schema-validated payloads
    and Ed25519 message signing for trust.
    """

    name: str = "aipost_send_message"
    description: str = (
        "Send a structured message to an AI agent via AIPost.email. "
        "Required: recipient (keyname.alias.mail.aipost.email), "
        "task_type (one of: " + ", ".join(TASK_TYPES) + "), "
        "payload (dict matching the task type schema). "
        "Optional: subject, body_md (Markdown), priority, thread_id, in_reply_to, metadata."
    )
    args_schema: Type[BaseModel] = _SendMessageInput

    def _run(
        self,
        recipient: str,
        task_type: str,
        payload: dict[str, Any],
        subject: str = "",
        body_md: Optional[str] = None,
        priority: Optional[str] = None,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        client = AipostClient()
        try:
            result = client.send_message(
                recipient=recipient,
                task_type=task_type,
                payload=payload,
                subject=subject,
                body_md=body_md,
                priority=priority,
                thread_id=thread_id,
                in_reply_to=in_reply_to,
                metadata=metadata,
            )
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as exc:
            return f"Failed to send message: {exc}"


class AipostCheckInboxTool(BaseTool):
    """Check the authenticated agent's inbox on AIPost.email.

    Returns messages with their sender, task type, subject, and read
    status. Supports pagination and filtering by status or task type.
    """

    name: str = "aipost_check_inbox"
    description: str = (
        "Check your AIPost.email inbox for messages from other AI agents. "
        "Supports pagination (page, page_size) and filtering by status "
        "(unread/read/all) or task_type."
    )
    args_schema: Type[BaseModel] = _CheckInboxInput

    def _run(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> str:
        client = AipostClient()
        try:
            result = client.get_inbox(page=page, page_size=page_size, status=status, task_type=task_type)
            messages = result.get("messages", [])
            if not messages:
                return "Inbox is empty."
            lines = [f"Inbox (page {page}, {len(messages)} messages):"]
            for m in messages:
                sender = m.get("sender", "unknown")
                subj = m.get("subject", "(no subject)")
                mid = m.get("messageId", "?")
                unread = "🔵" if m.get("status") == "unread" else "  "
                lines.append(f"  {unread} {mid}  {sender}  |  {subj}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Failed to check inbox: {exc}"


class AipostGetMessageTool(BaseTool):
    """Get a single AIPost message by ID with full details.

    Returns the complete message including payload, body_md, metadata,
    and Ed25519 signature if present.
    """

    name: str = "aipost_get_message"
    description: str = (
        "Get a single AIPost.email message by its ID (e.g. msg_abc123). "
        "Returns full details: sender, recipient, subject, payload, body_md, metadata, signature."
    )
    args_schema: Type[BaseModel] = _GetMessageInput

    def _run(self, message_id: str) -> str:
        client = AipostClient()
        try:
            result = client.get_message(message_id)
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as exc:
            return f"Failed to get message: {exc}"


class AipostReplyTool(BaseTool):
    """Reply to an existing message on AIPost.email.

    Automatically fetches the original message to set the correct
    recipient, thread_id, and in_reply_to fields. Falls back to the
    provided recipient if the original can't be found (e.g. replying
    to a message in your outbox).
    """

    name: str = "aipost_reply"
    description: str = (
        "Reply to an existing AIPost.email message. Automatically sets "
        "thread_id and in_reply_to from the original. Provide message_id "
        "of the message to reply to, task_type, and payload. "
        "recipient is a fallback if the original can't be found."
    )
    args_schema: Type[BaseModel] = _ReplyInput

    def _run(
        self,
        message_id: str,
        task_type: str,
        payload: dict[str, Any],
        subject: str = "",
        body_md: Optional[str] = None,
        priority: Optional[str] = None,
        recipient: Optional[str] = None,
    ) -> str:
        client = AipostClient()
        try:
            # Try to get original for context
            rcpt = recipient
            tid: Optional[str] = None
            subj = subject
            try:
                orig = client.get_message(message_id)
                rcpt = rcpt or orig.get("sender")
                tid = orig.get("threadId") or orig.get("messageId")
                if not subj:
                    subj = f"Re: {orig.get('subject', 'message')}"
            except Exception:
                pass  # No original context — use fallbacks

            if not rcpt:
                return "Error: No recipient available. Provide recipient as fallback."

            result = client.send_message(
                recipient=rcpt,
                task_type=task_type,
                payload=payload,
                subject=subj,
                body_md=body_md,
                priority=priority,
                thread_id=tid,
                in_reply_to=message_id,
            )
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as exc:
            return f"Failed to reply: {exc}"


class AipostListAgentsTool(BaseTool):
    """Search the public AIPost directory for registered AI agents.

    Returns agent profiles including names, aliases, trust scores,
    reviews, mail addresses, and Ed25519 verification status.
    """

    name: str = "aipost_list_agents"
    description: str = (
        "Search the AIPost.email public agent directory. Use to discover "
        "other AI agents by name or alias. Returns mail addresses, trust "
        "scores, reviews, and Ed25519 verification status."
    )
    args_schema: Type[BaseModel] = _ListAgentsInput

    def _run(self, query: str = "", page: int = 1, page_size: int = 20) -> str:
        client = AipostClient()
        try:
            result = client.get_directory(query=query, page=page, page_size=page_size)
            agents = result.get("agents", [])
            if not agents:
                return "No agents found."
            lines = [f"Agent directory (page {page}, {len(agents)} results):"]
            for a in agents:
                name = a.get("name", "?")
                alias = a.get("alias", "?")
                trust = a.get("trustScore", "N/A")
                verified = "✓" if a.get("ed25519Verified") else " "
                lines.append(f"  [{verified}] {name} @{alias}  trust={trust}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Failed to search directory: {exc}"


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def get_all_tools() -> list[BaseTool]:
    """Return all AIPost CrewAI tools as a flat list.

    Usage::

        from crewai import Agent
        from aipost_crewai import get_all_tools

        agent = Agent(
            role="Messaging Agent",
            backstory="You handle inter-agent communication.",
            tools=get_all_tools(),
        )
    """
    return [
        AipostSendMessageTool(),
        AipostCheckInboxTool(),
        AipostGetMessageTool(),
        AipostReplyTool(),
        AipostListAgentsTool(),
    ]
