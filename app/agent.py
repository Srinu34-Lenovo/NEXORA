import re

from app.llm import llm
from app.rag import rag
from app.memory import memory_manager
from app.tools import get_current_time, create_task


class NexoraAgent:

    ROLE_INSTRUCTIONS = {
        "developer agent": (
            "Developer Agent",
            "You are the Developer Agent. Help build, analyze, and debug software. "
            "Focus on code quality, debugging, architecture, implementation steps, and practical fixes."
        ),
        "data agent": (
            "Data Agent",
            "You are the Data Agent. Analyze datasets and generate insights. "
            "Focus on summarizing patterns, trends, anomalies, and actionable recommendations from data."
        ),
        "automation agent": (
            "Automation Agent",
            "You are the Automation Agent. Automate repetitive workflows and save time. "
            "Focus on step-by-step automation ideas, scripts, integrations, and efficiency improvements."
        ),
    }

    def __init__(self):

        self.max_steps = 5

    def detect_role(self, message):
        text = message.strip()
        match = re.search(
            r"act as(?:\s+the)?\s+([A-Za-z][A-Za-z\s-]+?)(?:[.!?]|$)",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return "General Assistant", "You are a helpful assistant."

        role_name = match.group(1).strip().lower()
        for key, (label, instructions) in self.ROLE_INSTRUCTIONS.items():
            if role_name == key or role_name in key:
                return label, instructions

        normalized = role_name.replace("-", " ")
        return (
            normalized.title(),
            f"You are the {normalized.title()} assistant. Provide a focused, helpful, and professional response."
        )

    def build_prompt(self, message):

        context = rag.build_context(message)
        role_label, role_instructions = self.detect_role(message)

        return f"""
You are NEXORA, a personal AI intelligence system.

Active persona: {role_label}
Persona instructions:
{role_instructions}

Relevant user memory:
{context}

User request:
{message}

Instructions:

1. Use the memory when relevant.
2. Do not invent personal information.
3. Be concise and useful.
4. If information is missing, say so.
5. Protect private information.
6. Stay in the active persona when answering.

Answer the user:
"""

    def chat(self, message):

        prompt = self.build_prompt(message)

        if llm.available():

            answer = llm.generate(prompt)

        else:

            answer = (
                "NEXORA local LLM is not running.\n\n"
                "Your message was received:\n"
                f"{message}\n\n"
                "Start Ollama to enable AI responses."
            )

        self._save_conversation(
            "user",
            message
        )

        self._save_conversation(
            "assistant",
            answer
        )

        return answer

    def remember(self, content):

        return memory_manager.add(
            content,
            "conversation"
        )

    def _save_conversation(
        self,
        role,
        content
    ):

        from app.database import get_db

        with get_db() as db:

            db.execute(
                """
                INSERT INTO conversations(
                    role,
                    content
                )
                VALUES (?, ?)
                """,
                (role, content)
            )

            db.commit()


agent = NexoraAgent()