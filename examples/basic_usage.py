#!/usr/bin/env python3
"""Minimal example: CrewAI agent sending a message via AIPost."""

import os
from crewai import Agent, Task, Crew
from aipost_crewai import AipostSendMessageTool, AipostCheckInboxTool

# Set your API key (or export AIPOST_API_KEY in your shell)
os.environ["AIPOST_API_KEY"] = "mfo_your_key_here"

# ---- Agents ---------------------------------------------------------

sender = Agent(
    role="Task Delegator",
    goal="Delegate tasks to other AI agents via AIPost.email",
    backstory="You manage a distributed team of AI agents and coordinate work.",
    tools=[AipostSendMessageTool(), AipostCheckInboxTool()],
    verbose=True,
)

# ---- Tasks ----------------------------------------------------------

send_task = Task(
    description=(
        "Send a TASK_DELEGATION message to agent 'worker.myteam.mail.aipost.email'. "
        "The payload should include: task description, deadline, and priority. "
        "Use subject='Weekly report delegation'."
    ),
    expected_output="Confirmation that the message was sent successfully, including the message ID.",
    agent=sender,
)

check_task = Task(
    description="Check the inbox for any new messages and summarize what you find.",
    expected_output="A summary of inbox contents.",
    agent=sender,
)

# ---- Crew -----------------------------------------------------------

crew = Crew(agents=[sender], tasks=[send_task, check_task])
result = crew.kickoff()
print(result)
