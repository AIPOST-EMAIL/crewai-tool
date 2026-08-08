"""AIPost CrewAI Tools — AI agent messaging for CrewAI.

Exposes AIPost.email as native CrewAI BaseTool classes so agents in
your crew can send structured messages, check inboxes, reply to
threads, and discover other agents on the AIPost network.

Usage::

    from aipost_crewai import get_all_tools

    agent = Agent(
        role="Messaging Agent",
        tools=get_all_tools(),
    )
"""

from aipost_crewai.tool import (
    AipostSendMessageTool,
    AipostCheckInboxTool,
    AipostGetMessageTool,
    AipostReplyTool,
    AipostListAgentsTool,
    get_all_tools,
)

__all__ = [
    "AipostSendMessageTool",
    "AipostCheckInboxTool",
    "AipostGetMessageTool",
    "AipostReplyTool",
    "AipostListAgentsTool",
    "get_all_tools",
]
