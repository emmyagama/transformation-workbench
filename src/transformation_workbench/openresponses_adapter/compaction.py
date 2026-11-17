"""Authenticated adapter-owned compact state for the local Open Responses adapter."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PROTOCOL = "transformation-workbench/openresponses-compaction"
VERSION = 1
TOKEN_PREFIX = "twb1."
AAD = b"transformation-workbench/openresponses-compaction:v1"
COMPACTION_KEY_ENV = "OPENRESPONSES_COMPACTION_KEY"
MAX_PLAINTEXT_BYTES = 64 * 1024
MAX_TOKEN_BYTES = 96 * 1024
MAX_SUMMARY_CHARS = 24 * 1024
MAX_COMPACTION_ITEMS = 4
MAX_CONTEXT_CHARS = 48 * 1024
DEFAULT_TTL_SECONDS = 24 * 60 * 60
COMPACTED_SYSTEM_PREFIX = "Compacted conversation state:\n"


class CompactionError(ValueError):
    """Safe compaction failure that never contains plaintext or key material."""

    def __init__(
        self,
        code: str = "invalid_compaction",
        message: str = "Compaction state is invalid or unavailable.",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CompactionState:
    summary: str
    model: str
    source_item_count: int
    created_at: int
    expires_at: int
    key_id: str


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.b64decode(value + padding, altchars=b"-_", validate=True)


def _key_id(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:16]


class CompactionCipher:
    """AES-GCM wrapper for adapter-owned continuation state."""

    def __init__(
        self,
        key: bytes,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        now: Callable[[], float] | None = None,
    ) -> None:
        if not isinstance(key, bytes) or len(key) != 32:
            raise CompactionError(
                "invalid_compaction_key",
                "Compaction key must be 32 bytes.",
            )
        if ttl_seconds <= 0:
            raise CompactionError(
                "invalid_compaction_key",
                "Compaction state lifetime must be positive.",
            )
        self._key = key
        self._key_id = _key_id(key)
        self._ttl_seconds = ttl_seconds
        self._now = now or time.time
        self._aead = AESGCM(key)

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        now: Callable[[], float] | None = None,
    ) -> CompactionCipher:
        source = os.environ if environ is None else environ
        raw = source.get(COMPACTION_KEY_ENV)
        if not raw:
            raise CompactionError(
                "missing_compaction_key",
                "The compaction key is not configured.",
            )
        try:
            key = _b64url_decode(raw)
        except Exception as exc:
            raise CompactionError(
                "invalid_compaction_key",
                "The compaction key is not valid base64url.",
            ) from exc
        return cls(key, ttl_seconds=ttl_seconds, now=now)

    @property
    def key_id(self) -> str:
        return self._key_id

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def now(self) -> int:
        return int(self._now())

    def encrypt(
        self,
        summary: str,
        *,
        model: str,
        source_item_count: int,
    ) -> str:
        if not isinstance(summary, str) or not summary.strip():
            raise CompactionError("empty_summary", "Compaction summary is empty.")
        if len(summary) > MAX_SUMMARY_CHARS:
            raise CompactionError("oversized_summary", "Compaction summary is too large.")
        if not isinstance(source_item_count, int) or source_item_count < 0:
            raise CompactionError("invalid_compaction", "Compaction item count is invalid.")
        created_at = self.now()
        payload = {
            "version": VERSION,
            "adapter": PROTOCOL,
            "key_id": self._key_id,
            "created_at": created_at,
            "expires_at": created_at + self._ttl_seconds,
            "model": model,
            "source_item_count": source_item_count,
            "summary": summary,
        }
        plaintext = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
        if len(plaintext) > MAX_PLAINTEXT_BYTES:
            raise CompactionError("oversized_compaction", "Compaction state is too large.")
        nonce = secrets.token_bytes(12)
        ciphertext = self._aead.encrypt(nonce, plaintext, AAD)
        token = TOKEN_PREFIX + _b64url_encode(nonce + ciphertext)
        if len(token.encode("ascii")) > MAX_TOKEN_BYTES:
            raise CompactionError("oversized_compaction", "Compaction token is too large.")
        return token

    def decrypt(self, token: str) -> CompactionState:
        if not isinstance(token, str) or not token.startswith(TOKEN_PREFIX):
            raise CompactionError("unsupported_compaction", "Unsupported compaction state.")
        encoded = token[len(TOKEN_PREFIX) :]
        if len(encoded) > MAX_TOKEN_BYTES:
            raise CompactionError("oversized_compaction", "Compaction token is too large.")
        try:
            raw = _b64url_decode(encoded)
        except Exception as exc:
            raise CompactionError("invalid_compaction", "Compaction state is malformed.") from exc
        if len(raw) < 12 + 16:
            raise CompactionError("invalid_compaction", "Compaction state is malformed.")
        nonce, ciphertext = raw[:12], raw[12:]
        try:
            plaintext = self._aead.decrypt(nonce, ciphertext, AAD)
        except InvalidTag as exc:
            raise CompactionError(
                "invalid_compaction",
                "Compaction state could not be authenticated.",
            ) from exc
        if len(plaintext) > MAX_PLAINTEXT_BYTES:
            raise CompactionError("oversized_compaction", "Compaction state is too large.")
        try:
            payload = json.loads(plaintext)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CompactionError("invalid_compaction", "Compaction state is malformed.") from exc
        if not isinstance(payload, dict):
            raise CompactionError("invalid_compaction", "Compaction state is malformed.")
        if payload.get("version") != VERSION:
            raise CompactionError("unsupported_compaction", "Unsupported compaction version.")
        if payload.get("adapter") != PROTOCOL:
            raise CompactionError("unsupported_compaction", "Unsupported compaction adapter.")
        if payload.get("key_id") != self._key_id:
            raise CompactionError("invalid_compaction", "Compaction key does not match.")
        created_at = payload.get("created_at")
        expires_at = payload.get("expires_at")
        model = payload.get("model")
        source_item_count = payload.get("source_item_count")
        summary = payload.get("summary")
        if (
            not isinstance(created_at, int)
            or isinstance(created_at, bool)
            or not isinstance(expires_at, int)
            or isinstance(expires_at, bool)
            or not isinstance(model, str)
            or not model
            or expires_at <= created_at
            or not isinstance(source_item_count, int)
            or isinstance(source_item_count, bool)
            or source_item_count < 0
            or not isinstance(summary, str)
            or not summary.strip()
            or len(summary) > MAX_SUMMARY_CHARS
        ):
            raise CompactionError("invalid_compaction", "Compaction state is malformed.")
        if expires_at <= self.now():
            raise CompactionError("expired_compaction", "Compaction state has expired.")
        return CompactionState(
            summary=summary,
            model=model,
            source_item_count=source_item_count,
            created_at=created_at,
            expires_at=expires_at,
            key_id=self._key_id,
        )


def replace_compaction_items(
    request: Mapping[str, Any],
    cipher: CompactionCipher,
) -> tuple[dict[str, Any], int]:
    """Replace adapter compaction items with validated system context."""

    result = copy.deepcopy(dict(request))
    input_value = result.get("input")
    if not isinstance(input_value, list):
        return result, 0
    replaced: list[Any] = []
    count = 0
    context_chars = 0
    requested_model = result.get("model")
    for item in input_value:
        if isinstance(item, Mapping) and item.get("type") == "compaction":
            if count >= MAX_COMPACTION_ITEMS:
                raise CompactionError(
                    "oversized_compaction",
                    "Too many compaction items.",
                )
            token = item.get("encrypted_content")
            if not isinstance(token, str):
                raise CompactionError("invalid_compaction", "Compaction item is malformed.")
            state = cipher.decrypt(token)
            if isinstance(requested_model, str) and requested_model != state.model:
                raise CompactionError(
                    "invalid_compaction",
                    "Compaction state does not match the requested model.",
                )
            context = COMPACTED_SYSTEM_PREFIX + state.summary
            context_chars += len(context)
            if context_chars > MAX_CONTEXT_CHARS:
                raise CompactionError(
                    "oversized_compaction",
                    "Compacted context is too large.",
                )
            replaced.append(
                {
                    "type": "message",
                    "role": "system",
                    "content": context,
                }
            )
            count += 1
            continue
        replaced.append(copy.deepcopy(item))
    result["input"] = replaced
    return result, count
