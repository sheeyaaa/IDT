"""Configuration loading for local model roles and pipeline limits."""

from __future__ import annotations

import ipaddress
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ModelSettings(BaseModel):
    """Ollama model and sampling settings for one agent role."""

    model_config = ConfigDict(extra="forbid")

    name: str
    temperature: float = Field(ge=0, le=2)


class AppConfig(BaseModel):
    """Application settings, including the mandatory local Ollama endpoint."""

    model_config = ConfigDict(extra="forbid")

    ollama_base_url: str = "http://localhost:11434"
    models: dict[str, ModelSettings]
    max_iterations: int = Field(default=3, ge=1, le=3)
    quality_threshold: float = Field(default=8.0, ge=0, le=10)
    coverage_target: float = Field(default=95.0, ge=0, le=100)
    chunk_size_tokens: int = Field(default=800, ge=100)
    chunk_overlap_tokens: int = Field(default=100, ge=0)
    generation_batch_size: int = Field(default=8, ge=1)
    request_retries: int = Field(default=2, ge=0, le=2)
    keep_alive: int = Field(default=300, ge=0)
    chroma_path: Path = Path(".tcgen/chroma")

    @field_validator("ollama_base_url")
    @classmethod
    def require_local_ollama(cls, value: str) -> str:
        """Reject remote Ollama endpoints to keep document content on-device."""
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("ollama_base_url must be a valid local HTTP(S) URL")
        hostname = parsed.hostname.casefold()
        is_loopback = hostname == "localhost"
        if not is_loopback:
            try:
                is_loopback = ipaddress.ip_address(hostname).is_loopback
            except ValueError:
                is_loopback = False
        if not is_loopback:
            raise ValueError("ollama_base_url must use localhost or a loopback IP address")
        return value

    @model_validator(mode="after")
    def validate_roles_and_limits(self) -> AppConfig:
        """Require all model roles, distinct critic family, and a meaningful overlap."""
        required_roles = {"extractor", "generator", "critic", "embeddings"}
        missing_roles = required_roles - self.models.keys()
        if missing_roles:
            raise ValueError(f"Missing model roles: {', '.join(sorted(missing_roles))}")
        generator_name = self.models["generator"].name.rsplit("/", 1)[-1].casefold()
        critic_name = self.models["critic"].name.rsplit("/", 1)[-1].casefold()
        generator_match = re.match(r"[a-z]+", generator_name)
        critic_match = re.match(r"[a-z]+", critic_name)
        generator_family = generator_match.group() if generator_match else generator_name
        critic_family = critic_match.group() if critic_match else critic_name
        if generator_family == critic_family:
            raise ValueError("critic model must be from a different family than generator")
        if self.chunk_overlap_tokens >= self.chunk_size_tokens:
            raise ValueError("chunk_overlap_tokens must be less than chunk_size_tokens")
        return self


def load_config(path: Path | None = None) -> AppConfig:
    """Load YAML settings and apply supported environment overrides."""
    config_path = path or Path("config.yaml")
    data: dict[str, Any] = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Configuration must be a YAML mapping: {config_path}")
        data = loaded

    data["ollama_base_url"] = os.getenv(
        "TCGEN_OLLAMA_BASE_URL", data.get("ollama_base_url", "http://localhost:11434")
    )
    role_models = data.setdefault("models", {})
    if not isinstance(role_models, dict):
        raise ValueError("Configuration 'models' must be a YAML mapping")
    for role in ("extractor", "generator", "critic", "embeddings"):
        env_name = f"TCGEN_{role.upper()}_MODEL"
        if env_name in os.environ:
            role_settings = role_models.setdefault(role, {})
            if isinstance(role_settings, str):
                role_settings = {"name": role_settings}
                role_models[role] = role_settings
            if not isinstance(role_settings, dict):
                raise ValueError(f"Configuration for model role {role!r} must be a mapping")
            role_settings["name"] = os.environ[env_name]
    return AppConfig.model_validate(data)
