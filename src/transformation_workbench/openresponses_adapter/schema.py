"""Pinned-schema loading and validation for the local adapter prototype."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

SCHEMA_DIR = Path(__file__).with_name("schemas")
RESPONSE_RESOURCE_SCHEMA = "response_resource.schema.json"
COMPACT_RESOURCE_SCHEMA = "compact_resource.schema.json"


class SchemaValidationError(ValueError):
    """Raised when a normalized payload does not satisfy the pinned schema."""


@lru_cache(maxsize=None)
def _load_validator(filename: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _format_error(error: ValidationError) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    location = path or "(root)"
    return f"{location}: {error.message}"


def _validate(filename: str, payload: Any) -> None:
    validator = _load_validator(filename)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    if errors:
        raise SchemaValidationError("; ".join(_format_error(error) for error in errors))


def validate_response_resource(payload: Any) -> None:
    _validate(RESPONSE_RESOURCE_SCHEMA, payload)


def validate_compact_resource(payload: Any) -> None:
    _validate(COMPACT_RESOURCE_SCHEMA, payload)
