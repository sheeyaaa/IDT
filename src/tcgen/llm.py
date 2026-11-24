"""Ollama model construction and bounded structured-output validation."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol, TypeVar

from langchain_ollama import ChatOllama
from ollama import Client
from pydantic import BaseModel, ValidationError

from tcgen.config import AppConfig

T = TypeVar("T", bound=BaseModel)


class Invokable(Protocol):
    """Minimal injectable interface implemented by Ollama and test doubles."""

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        """Return a model response for a single prompt."""


class _ModelSwitcher:
    """Unload the previous role model before another role is invoked."""

    def __init__(self, base_url: str) -> None:
        self.client = Client(host=base_url)
        self.active_model: str | None = None
        self.unload_on_switch = True

    def activate(self, model: str) -> None:
        """Switch the single active Ollama model, unloading its predecessor."""
        if self.unload_on_switch and self.active_model and self.active_model != model:
            self.client.generate(model=self.active_model, prompt="", keep_alive=0)
        self.active_model = model


def unload_model(model: str, base_url: str) -> None:
    """Unload a local model after a completed embedding phase."""
    Client(host=base_url).generate(model=model, prompt="", keep_alive=0)


class _SequentialChatClient:
    """Wrap a chat model so role transitions release the previous model."""

    def __init__(self, model: str, chat: ChatOllama, switcher: _ModelSwitcher) -> None:
        self.model = model
        self.chat = chat
        self.switcher = switcher

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        """Activate this configured model, then delegate the request."""
        self.switcher.activate(self.model)
        return self.chat.invoke(input, **kwargs)

    def invoke_structured(self, prompt: str, schema: type[BaseModel]) -> Any:
        """Ask Ollama for schema-constrained JSON instead of showing it the schema."""
        self.switcher.activate(self.model)
        structured = self.chat.with_structured_output(
            schema,
            method="json_schema",
            include_raw=True,
        )
        return structured.invoke(prompt)


def create_model_clients(config: AppConfig) -> dict[str, Invokable]:
    """Create one local chat client for each configured agent role."""
    switcher = _ModelSwitcher(config.ollama_base_url)
    switcher.unload_on_switch = config.keep_alive != 0
    clients: dict[str, Invokable] = {}
    for role in ("extractor", "generator", "critic"):
        settings = config.models[role]
        chat = ChatOllama(
            model=settings.name,
            base_url=config.ollama_base_url,
            temperature=settings.temperature,
            keep_alive=config.keep_alive,
        )
        clients[role] = _SequentialChatClient(
            model=settings.name,
            chat=chat,
            switcher=switcher,
        )
    return clients


def _response_text(response: Any) -> str:
    """Extract textual content from the common LangChain response shapes."""
    if isinstance(response, str):
        return response
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item) for item in content
        )
    return str(content)


def _repair_json(text: str) -> str:
    """Apply small deterministic repairs without inventing missing content."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    first_object = cleaned.find("{")
    first_array = cleaned.find("[")
    starts = [position for position in (first_object, first_array) if position >= 0]
    if starts:
        start = min(starts)
        end = max(cleaned.rfind("}"), cleaned.rfind("]")) + 1
        if end > start:
            cleaned = cleaned[start:end]
    return re.sub(r",\s*([}\]])", r"\1", cleaned)


def invoke_structured(
    client: Invokable,
    prompt: str,
    schema: type[T],
    retries: int = 2,
) -> tuple[T, int, int]:
    """Invoke a local model, repair JSON, and validate with bounded retries.

    The two integer results are approximate input and output token counts.
    """
    failures: list[str] = []
    input_tokens = 0
    output_tokens = 0
    for attempt in range(retries + 1):
        try:
            structured_invoke = getattr(client, "invoke_structured", None)
            response = (
                structured_invoke(prompt, schema)
                if callable(structured_invoke)
                else client.invoke(prompt)
            )
            if isinstance(response, dict) and "parsing_error" in response:
                parsing_error = response["parsing_error"]
                if parsing_error is not None:
                    raise ValueError(f"Structured response parsing failed: {parsing_error}")
                response = response.get("parsed")
            if isinstance(response, schema):
                parsed = response
                raw = response.model_dump_json()
            elif isinstance(response, dict):
                parsed = schema.model_validate(response)
                raw = json.dumps(response)
            else:
                raw = _response_text(response)
                parsed = schema.model_validate_json(_repair_json(raw))
            input_tokens += max(1, len(prompt) // 4)
            output_tokens += max(1, len(raw) // 4)
            return parsed, input_tokens, output_tokens
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"attempt {attempt + 1}: {exc}")
    raise ValueError(
        f"Model output did not match {schema.__name__} after {retries + 1} attempts: "
        + "; ".join(failures)
    )
