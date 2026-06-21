from __future__ import annotations

from pathlib import Path

PROMPT_VERSION = "v1.0"
PROMPTS_DIR = Path(__file__).parent / "prompts" / PROMPT_VERSION


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_synthesis_user_prompt(
    *,
    question: str,
    briefing_context: str,
    tool_context: str,
    conversation_history: str = "",
) -> str:
    parts = [
        "## Research question",
        question,
        "",
        "## RQ briefing (pre-analyzed evidence)",
        briefing_context,
    ]
    if tool_context.strip():
        parts.extend(["", "## Additional tool results", tool_context])
    if conversation_history.strip():
        parts.extend(["", "## Conversation history", conversation_history])
    parts.extend(
        [
            "",
            "## Instructions",
            "- Answer using only the evidence above.",
            "- Cite review_id for every factual claim using backticks, e.g. `uuid`.",
            "- Flag low-confidence evidence when confidence < 0.5.",
            "- If evidence is insufficient, say so explicitly.",
        ]
    )
    return "\n".join(parts)
