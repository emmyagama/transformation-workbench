"""Typed synthetic intake for the end-to-end Transformation Workbench demo."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .security import (
    SafetyError,
    assert_safe_display_text,
    validate_case_ids,
)

DEFAULT_CASE_IDS = ("C-009", "C-006", "C-014")
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}\Z")


class IntakeRequest(BaseModel):
    """One synthetic request and its bounded analysis inputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    request_id: str = Field(min_length=1, max_length=200)
    process_name: str = Field(
        default="Synthetic email service-request intake",
        min_length=1,
        max_length=200,
    )
    desired_outcome: str = Field(min_length=10, max_length=1000)
    case_ids: list[str] = Field(
        default_factory=lambda: list(DEFAULT_CASE_IDS),
        max_length=20,
    )
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("request_id")
    @classmethod
    def _validate_request_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not _REQUEST_ID_PATTERN.fullmatch(cleaned):
            raise ValueError(
                "request_id must be a short identifier without spaces or paths."
            )
        return cleaned

    @field_validator("process_name")
    @classmethod
    def _validate_process_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("process_name must not be blank.")
        assert_safe_display_text(cleaned, "process_name")
        return cleaned

    @field_validator("desired_outcome")
    @classmethod
    def _validate_desired_outcome(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("desired_outcome must contain at least 10 characters.")
        assert_safe_display_text(cleaned, "desired_outcome")
        return cleaned

    @field_validator("case_ids")
    @classmethod
    def _validate_case_ids(cls, values: list[str]) -> list[str]:
        try:
            return validate_case_ids(values)
        except SafetyError as exc:
            raise ValueError(exc.message) from exc

    @field_validator("notes")
    @classmethod
    def _validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        assert_safe_display_text(cleaned, "notes")
        return cleaned
