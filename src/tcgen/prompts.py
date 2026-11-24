"""Loading of checked-in runtime prompt templates."""

from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"


def render_prompt(name: str, **values: str) -> str:
    """Load a Markdown prompt template and replace its named placeholders."""
    template_path = PROMPT_DIR / f"{name}.md"
    template = template_path.read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template
