"""Gate 1 tests for the optional local Open Responses adapter."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from starlette.testclient import TestClient

from transformation_workbench.openresponses_adapter.compaction import (
    AAD,
    COMPACTION_KEY_ENV,
    MAX_COMPACTION_ITEMS,
    MAX_SUMMARY_CHARS,
    TOKEN_PREFIX,
    CompactionCipher,
    CompactionError,
)
from transformation_workbench.openresponses_adapter.fake_upstream import (
    FakeStats,
    build_fake_app,
)
from transformation_workbench.openresponses_adapter.gateway import (
    BoundedResponseCache,
    ConfigurationError,
    assert_loopback_url,
    assert_upstream_url,
    build_gateway_app,
)
from transformation_workbench.openresponses_adapter.responses import (
    build_compaction_summary_request,
    build_fake_response,
    build_fake_summary,
)
from transformation_workbench.openresponses_adapter.runtime import (
    assert_hosted_credentials,
    assert_no_hosted_credentials,
)

UPSTREAM = "http://127.0.0.1:9999"
TEST_KEY = bytes(range(32))


def make_test_cipher(now: Any = None) -> CompactionCipher:
    return CompactionCipher(TEST_KEY, now=now)


def tamper_token(token: str) -> str:
    encoded = token[len(TOKEN_PREFIX) :]
    padding = "=" * (-len(encoded) % 4)
    raw = bytearray(base64.urlsafe_b64decode(encoded + padding))
    raw[-1] ^= 1
    return TOKEN_PREFIX + base64.urlsafe_b64encode(bytes(raw)).rstrip(b"=").decode(
        "ascii"
    )


def seal_payload(payload: dict[str, Any], *, key: bytes = TEST_KEY) -> str:
    nonce = b"\x00" * 12
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, AAD)
    return TOKEN_PREFIX + base64.urlsafe_b64encode(nonce + ciphertext).rstrip(b"=").decode(
        "ascii"
    )



class MockUpstream:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.mode = "ok"

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.calls.append(
            {
                "path": request.url.path,
                "body": body,
                "authorization": request.headers.get("authorization"),
                "compaction": request.headers.get("x-workbench-compaction") == "1",
            }
        )
        if self.mode == "http_error":
            return httpx.Response(
                503,
                json={"error": {"code": "fake_down", "message": "down"}},
            )
        if self.mode == "invalid_response":
            return httpx.Response(200, json=[])
        if request.headers.get("x-workbench-compaction") == "1":
            return httpx.Response(200, json=build_fake_summary(body))
        input_value = body.get("input")
        if isinstance(input_value, list) and any(
            isinstance(item, dict)
            and item.get("type") == "function_call_output"
            and item.get("call_id") == "call_openresponses_missing"
            for item in input_value
        ):
            return httpx.Response(
                400,
                json={
                    "error": {
                        "code": "invalid_function_call_output",
                        "message": "missing tool call",
                    }
                },
            )
        if body.get("stream") is True:
            if self.mode == "partial_sse":
                return httpx.Response(
                    200,
                    text='event: response.completed\ndata: {"type":"response.complet',
                    headers={"content-type": "text/event-stream"},
                )
            if self.mode == "malformed_sse":
                return httpx.Response(
                    200,
                    text="event: response.completed\ndata: {bad-json}\n\ndata: [DONE]\n\n",
                    headers={"content-type": "text/event-stream"},
                )
            response = build_fake_response(body)
            event = json.dumps({"type": "response.completed", "response": response})
            return httpx.Response(
                200,
                text=f"event: response.completed\ndata: {event}\n\ndata: [DONE]\n\n",
                headers={"content-type": "text/event-stream"},
            )
        return httpx.Response(200, json=build_fake_response(body))


def make_client(
    mock: MockUpstream,
    *,
    max_cache_entries: int = 32,
    cipher: CompactionCipher | None = None,
    upstream_headers: dict[str, str] | None = None,
) -> TestClient:
    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.MockTransport(mock.handler),
            trust_env=False,
        )

    app = build_gateway_app(
        UPSTREAM,
        client_factory=factory,
        max_cache_entries=max_cache_entries,
        compaction_cipher=cipher or make_test_cipher(),
        upstream_headers=upstream_headers,
    )
    return TestClient(app)


def test_http_translation_preserves_request_values_and_validates_schema() -> None:
    mock = MockUpstream()
    with make_client(mock) as client:
        response = client.post(
            "/responses",
            headers={"Authorization": "Bearer local-dummy"},
            json={
                "model": "local-fake-model",
                "input": "Say hello in exactly 3 words.",
                "temperature": 0.2,
                "top_p": 0.3,
                "parallel_tool_calls": False,
                "max_output_tokens": 42,
                "store": False,
                "metadata": {"test": "gate-1"},
                "service_tier": "default",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["temperature"] == pytest.approx(0.2)
    assert payload["top_p"] == pytest.approx(0.3)
    assert payload["parallel_tool_calls"] is False
    assert payload["max_output_tokens"] == 42
    assert payload["store"] is False
    assert payload["metadata"] == {"test": "gate-1"}
    assert payload["output"][0]["content"][0]["type"] == "output_text"
    assert mock.calls[0]["authorization"] is None
    assert mock.calls[0]["path"] == "/responses"


def test_tool_request_normalizes_response_tool_defaults_and_function_call() -> None:
    with make_client(MockUpstream()) as client:
        response = client.post(
            "/responses",
            json={
                "model": "local-fake-model",
                "input": "What's the weather in San Francisco?",
                "tools": [
                    {
                        "type": "function",
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {
                            "type": "object",
                            "properties": {"location": {"type": "string"}},
                        },
                    }
                ],
            },
        )

    payload = response.json()
    assert payload["tools"][0]["strict"] is None
    assert payload["tools"][0]["name"] == "get_weather"
    assert payload["output"][0]["type"] == "function_call"
    assert payload["output"][0]["name"] == "get_weather"


def test_streaming_translation_emits_events_and_terminal_response() -> None:
    mock = MockUpstream()
    with make_client(mock) as client:
        response = client.post(
            "/responses",
            json={"model": "local-fake-model", "input": "Count from 1 to 5.", "stream": True},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: response.created" in response.text
    assert "event: response.output_text.delta" in response.text
    assert "event: response.completed" in response.text
    assert "data: [DONE]" in response.text


def test_streaming_malformed_upstream_reports_safe_error_event() -> None:
    mock = MockUpstream()
    mock.mode = "malformed_sse"
    with make_client(mock) as client:
        response = client.post(
            "/responses",
            json={"model": "local-fake-model", "input": "hello", "stream": True},
        )

    assert response.status_code == 200
    assert "upstream_protocol_error" in response.text
    assert "response.completed" not in response.text


def test_streaming_partial_upstream_reports_safe_error_event() -> None:
    mock = MockUpstream()
    mock.mode = "partial_sse"
    with make_client(mock) as client:
        response = client.post(
            "/responses",
            json={"model": "local-fake-model", "input": "hello", "stream": True},
        )

    assert response.status_code == 200
    assert "upstream_protocol_error" in response.text
    assert "response.completed" not in response.text


def test_invalid_upstream_response_is_bounded() -> None:
    mock = MockUpstream()
    mock.mode = "invalid_response"
    with make_client(mock) as client:
        response = client.post(
            "/responses",
            json={"model": "local-fake-model", "input": "hello"},
        )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_protocol_error"


def test_http_upstream_error_is_mapped_without_leaking_request_body() -> None:
    mock = MockUpstream()
    mock.mode = "http_error"
    with make_client(mock) as client:
        response = client.post(
            "/responses",
            json={"model": "local-fake-model", "input": "sensitive local text"},
        )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "fake_down"
    assert "sensitive local text" not in response.text


def test_websocket_supports_multiple_turns_and_continuation() -> None:
    mock = MockUpstream()
    with make_client(mock) as client:
        with client.websocket_connect("/responses") as websocket:
            websocket.send_json(
                {
                    "type": "response.create",
                    "model": "local-fake-model",
                    "store": False,
                    "input": "Remember the code word: cobalt. Reply with OK.",
                }
            )
            first_events = receive_until_terminal(websocket)
            first = first_events[-1]["response"]
            assert first["id"].startswith("resp_")

            websocket.send_json(
                {
                    "type": "response.create",
                    "model": "local-fake-model",
                    "store": False,
                    "previous_response_id": first["id"],
                    "input": "What is the code word? Reply with only the code word.",
                }
            )
            second_events = receive_until_terminal(websocket)
            second = second_events[-1]["response"]

    assert second["previous_response_id"] == first["id"]
    assert second["output"][0]["content"][0]["text"] == "cobalt"
    second_upstream = mock.calls[1]["body"]
    assert "previous_response_id" not in second_upstream
    assert "cobalt" in json.dumps(second_upstream["input"])


def test_websocket_missing_predecessor_is_connection_scoped() -> None:
    mock = MockUpstream()
    with make_client(mock) as client:
        with client.websocket_connect("/responses") as websocket:
            websocket.send_json(
                {
                    "type": "response.create",
                    "model": "local-fake-model",
                    "store": False,
                    "input": "Remember the code word: cobalt. Reply with OK.",
                }
            )
            first = receive_until_terminal(websocket)[-1]["response"]
        with client.websocket_connect("/responses") as websocket:
            websocket.send_json(
                {
                    "type": "response.create",
                    "model": "local-fake-model",
                    "store": False,
                    "previous_response_id": first["id"],
                    "input": "Continue.",
                }
            )
            error = websocket.receive_json()

    assert error["type"] == "error"
    assert error["error"]["code"] == "previous_response_not_found"


def test_failed_continuation_evicts_cached_predecessor() -> None:
    mock = MockUpstream()
    with make_client(mock) as client:
        with client.websocket_connect("/responses") as websocket:
            websocket.send_json(
                {
                    "type": "response.create",
                    "model": "local-fake-model",
                    "store": False,
                    "input": "Remember the code word: ember. Reply with OK.",
                }
            )
            first = receive_until_terminal(websocket)[-1]["response"]
            websocket.send_json(
                {
                    "type": "response.create",
                    "model": "local-fake-model",
                    "store": False,
                    "previous_response_id": first["id"],
                    "input": [
                        {
                            "type": "function_call_output",
                            "call_id": "call_openresponses_missing",
                            "output": "missing",
                        }
                    ],
                }
            )
            failed = websocket.receive_json()
            websocket.send_json(
                {
                    "type": "response.create",
                    "model": "local-fake-model",
                    "store": False,
                    "previous_response_id": first["id"],
                    "input": "Try again.",
                }
            )
            retry = websocket.receive_json()

    assert failed["type"] == "error"
    assert retry["error"]["code"] == "previous_response_not_found"


def test_compacted_output_can_start_a_new_websocket_chain() -> None:
    mock = MockUpstream()
    with make_client(mock) as client:
        compact = client.post(
            "/responses/compact",
            json={"model": "local-fake-model", "input": "compact this"},
        )
        compacted_output = compact.json()["output"]
        with client.websocket_connect("/responses") as websocket:
            websocket.send_json(
                {
                    "type": "response.create",
                    "model": "local-fake-model",
                    "store": False,
                    "input": [
                        *compacted_output,
                        {
                            "type": "message",
                            "role": "user",
                            "content": "Continue from here. Reply with exactly: compacted",
                        },
                    ],
                    "tools": [],
                }
            )
            events = receive_until_terminal(websocket)

    final = events[-1]["response"]
    assert final["status"] == "completed"
    assert final["previous_response_id"] is None
    assert final["output"][0]["content"][0]["text"] == "compacted"


def test_websocket_rejects_http_only_fields() -> None:
    with make_client(MockUpstream()) as client:
        with client.websocket_connect("/responses") as websocket:
            websocket.send_json(
                {
                    "type": "response.create",
                    "model": "local-fake-model",
                    "stream": True,
                    "input": "hello",
                }
            )
            error = websocket.receive_json()
    assert error["error"]["code"] == "invalid_request"


def test_bounded_cache_evicts_oldest_entry() -> None:
    cache = BoundedResponseCache(max_entries=2)
    cache.put("one", {"id": "one"}, {})
    cache.put("two", {"id": "two"}, {})
    cache.put("three", {"id": "three"}, {})
    assert cache.get("one") is None
    assert cache.get("two") is not None
    assert cache.get("three") is not None
    assert len(cache) == 2


def test_compaction_contract_and_missing_model_preflight() -> None:
    mock = MockUpstream()
    cipher = make_test_cipher(now=lambda: 1_000)
    with make_client(mock, cipher=cipher) as client:
        missing = client.post("/responses/compact", json={"input": "compact"})
        compact = client.post(
            "/responses/compact",
            json={"model": "local-fake-model", "input": "compact this"},
        )

    assert missing.status_code == 400
    assert len(mock.calls) == 1
    assert mock.calls[0]["path"] == "/responses"
    assert mock.calls[0]["compaction"] is True
    assert compact.status_code == 200
    payload = compact.json()
    assert payload["object"] == "response.compaction"
    assert payload["output"][0]["type"] == "compaction"
    token = payload["output"][0]["encrypted_content"]
    assert token.startswith(TOKEN_PREFIX)
    assert "test-only" not in token
    state = cipher.decrypt(token)
    assert "compact this" in state.summary
    assert "compact this" not in token


def test_compaction_summary_request_preserves_original_instructions() -> None:
    request = build_compaction_summary_request(
        {"model": "m", "instructions": "Keep the customer tone."},
        "user: hello",
    )
    serialized = json.dumps(request["input"])
    assert "Keep the customer tone." in serialized
    assert request["store"] is False
    assert request["stream"] is False


def test_compaction_round_trip_is_randomized_and_hides_plaintext() -> None:
    summary = "The launch is Tuesday. Support must be notified first."
    cipher = make_test_cipher(now=lambda: 1_000)
    first = cipher.encrypt(summary, model="local-fake-model", source_item_count=2)
    second = cipher.encrypt(summary, model="local-fake-model", source_item_count=2)

    assert first != second
    assert first.startswith(TOKEN_PREFIX)
    assert summary not in first
    state = cipher.decrypt(first)
    assert state.summary == summary
    assert state.model == "local-fake-model"
    assert state.source_item_count == 2
    assert state.created_at == 1_000
    assert state.key_id == cipher.key_id


def test_compaction_rejects_tamper_wrong_key_version_and_expiry() -> None:
    cipher = make_test_cipher(now=lambda: 1_000)
    token = cipher.encrypt("secret summary", model="m", source_item_count=1)
    tampered = tamper_token(token)

    with pytest.raises(CompactionError) as tamper_error:
        cipher.decrypt(tampered)
    assert tamper_error.value.code == "invalid_compaction"

    wrong_key = CompactionCipher(bytes(range(1, 33)), now=lambda: 1_000)
    with pytest.raises(CompactionError) as key_error:
        wrong_key.decrypt(token)
    assert key_error.value.code == "invalid_compaction"

    version_payload = {
        "version": 2,
        "adapter": "transformation-workbench/openresponses-compaction",
        "key_id": cipher.key_id,
        "created_at": 1_000,
        "expires_at": 2_000,
        "model": "m",
        "source_item_count": 1,
        "summary": "secret summary",
    }
    with pytest.raises(CompactionError) as version_error:
        cipher.decrypt(seal_payload(version_payload))
    assert version_error.value.code == "unsupported_compaction"

    clock = [1_000]
    expiring = CompactionCipher(TEST_KEY, ttl_seconds=10, now=lambda: clock[0])
    expiring_token = expiring.encrypt("secret summary", model="m", source_item_count=1)
    clock[0] = 2_000
    with pytest.raises(CompactionError) as expiry_error:
        expiring.decrypt(expiring_token)
    assert expiry_error.value.code == "expired_compaction"


def test_compaction_requires_a_valid_key() -> None:
    with pytest.raises(CompactionError) as missing:
        CompactionCipher.from_env({})
    assert missing.value.code == "missing_compaction_key"
    with pytest.raises(CompactionError) as invalid:
        CompactionCipher.from_env({COMPACTION_KEY_ENV: "not-a-valid-key"})
    assert invalid.value.code == "invalid_compaction_key"


def test_gateway_requires_a_compaction_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(COMPACTION_KEY_ENV, raising=False)
    with pytest.raises(CompactionError) as error:
        build_gateway_app(UPSTREAM)
    assert error.value.code == "missing_compaction_key"


def test_compaction_rejects_malformed_and_oversized_tokens() -> None:
    cipher = make_test_cipher()
    with pytest.raises(CompactionError) as malformed:
        cipher.decrypt("not-a-token")
    assert malformed.value.code == "unsupported_compaction"
    with pytest.raises(CompactionError) as oversized:
        cipher.decrypt(TOKEN_PREFIX + "A" * (96 * 1024 + 1))
    assert oversized.value.code == "oversized_compaction"


def test_compaction_rejects_oversized_summary_payload() -> None:
    cipher = make_test_cipher(now=lambda: 1_000)
    payload = {
        "version": 1,
        "adapter": "transformation-workbench/openresponses-compaction",
        "key_id": cipher.key_id,
        "created_at": 1_000,
        "expires_at": 2_000,
        "model": "m",
        "source_item_count": 1,
        "summary": "x" * (MAX_SUMMARY_CHARS + 1),
    }
    with pytest.raises(CompactionError) as error:
        cipher.decrypt(seal_payload(payload))
    assert error.value.code == "invalid_compaction"


def test_compaction_item_round_trip_reconstructs_context() -> None:
    mock = MockUpstream()
    cipher = make_test_cipher()
    with make_client(mock, cipher=cipher) as client:
        compact = client.post(
            "/responses/compact",
            json={
                "model": "local-fake-model",
                "input": "We agreed to launch on Tuesday and notify support first.",
            },
        )
        token = compact.json()["output"][0]["encrypted_content"]
        continued = client.post(
            "/responses",
            json={
                "model": "local-fake-model",
                "input": [
                    {"type": "compaction", "encrypted_content": token},
                    {
                        "type": "message",
                        "role": "user",
                        "content": "Reply with exactly: compacted",
                    },
                ],
            },
        )

    assert continued.status_code == 200
    upstream_input = mock.calls[-1]["body"]["input"]
    assert upstream_input[0]["role"] == "system"
    assert "We agreed to launch on Tuesday" in upstream_input[0]["content"]
    assert all(item.get("type") != "compaction" for item in upstream_input)
    assert continued.json()["output"][0]["content"][0]["text"] == "compacted"


def test_tampered_compaction_item_is_rejected_before_upstream() -> None:
    mock = MockUpstream()
    cipher = make_test_cipher()
    with make_client(mock, cipher=cipher) as client:
        compact = client.post(
            "/responses/compact",
            json={"model": "local-fake-model", "input": "sensitive summary"},
        )
        token = compact.json()["output"][0]["encrypted_content"]
        tampered = tamper_token(token)
        response = client.post(
            "/responses",
            json={
                "model": "local-fake-model",
                "input": [{"type": "compaction", "encrypted_content": tampered}],
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_compaction"
    assert len(mock.calls) == 1


def test_compaction_item_with_wrong_key_is_rejected_before_upstream() -> None:
    first = MockUpstream()
    with make_client(first, cipher=make_test_cipher()) as client:
        compact = client.post(
            "/responses/compact",
            json={"model": "local-fake-model", "input": "sensitive summary"},
        )
    token = compact.json()["output"][0]["encrypted_content"]

    second = MockUpstream()
    wrong_key = CompactionCipher(bytes(range(1, 33)))
    with make_client(second, cipher=wrong_key) as client:
        response = client.post(
            "/responses",
            json={
                "model": "local-fake-model",
                "input": [{"type": "compaction", "encrypted_content": token}],
            },
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_compaction"
    assert second.calls == []


def test_compaction_item_model_mismatch_is_rejected_before_upstream() -> None:
    mock = MockUpstream()
    cipher = make_test_cipher()
    with make_client(mock, cipher=cipher) as client:
        compact = client.post(
            "/responses/compact",
            json={"model": "local-fake-model", "input": "sensitive summary"},
        )
        token = compact.json()["output"][0]["encrypted_content"]
        response = client.post(
            "/responses",
            json={
                "model": "different-model",
                "input": [{"type": "compaction", "encrypted_content": token}],
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_compaction"
    assert len(mock.calls) == 1


def test_too_many_compaction_items_are_rejected_before_upstream() -> None:
    mock = MockUpstream()
    cipher = make_test_cipher()
    with make_client(mock, cipher=cipher) as client:
        compact = client.post(
            "/responses/compact",
            json={"model": "local-fake-model", "input": "sensitive summary"},
        )
        token = compact.json()["output"][0]["encrypted_content"]
        response = client.post(
            "/responses",
            json={
                "model": "local-fake-model",
                "input": [
                    {"type": "compaction", "encrypted_content": token}
                    for _ in range(MAX_COMPACTION_ITEMS + 1)
                ],
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "oversized_compaction"
    assert len(mock.calls) == 1


def test_compact_request_rejects_state_from_another_model() -> None:
    mock = MockUpstream()
    cipher = make_test_cipher()
    with make_client(mock, cipher=cipher) as client:
        compact = client.post(
            "/responses/compact",
            json={"model": "local-fake-model", "input": "sensitive summary"},
        )
        token = compact.json()["output"][0]["encrypted_content"]
        response = client.post(
            "/responses/compact",
            json={
                "model": "different-model",
                "input": [{"type": "compaction", "encrypted_content": token}],
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_compaction"
    assert len(mock.calls) == 1


def test_compaction_upstream_failure_is_bounded() -> None:
    mock = MockUpstream()
    mock.mode = "http_error"
    with make_client(mock) as client:
        response = client.post(
            "/responses/compact",
            json={"model": "local-fake-model", "input": "sensitive summary"},
        )

    assert response.status_code == 502
    assert "encrypted_content" not in response.text
    assert "sensitive summary" not in response.text


def test_compaction_errors_and_logs_do_not_leak_summary(caplog: pytest.LogCaptureFixture) -> None:
    mock = MockUpstream()
    cipher = make_test_cipher()
    with caplog.at_level(logging.DEBUG):
        with make_client(mock, cipher=cipher) as client:
            compact = client.post(
                "/responses/compact",
                json={
                    "model": "local-fake-model",
                    "input": "The launch is Tuesday and support must be notified.",
                },
            )
            token = compact.json()["output"][0]["encrypted_content"]
            tampered = tamper_token(token)
            response = client.post(
                "/responses",
                json={
                    "model": "local-fake-model",
                    "input": [{"type": "compaction", "encrypted_content": tampered}],
                },
            )

    assert response.status_code == 400
    assert "Tuesday" not in response.text
    assert "Tuesday" not in caplog.text


def test_gateway_stats_count_and_reset_upstream_operations() -> None:
    mock = MockUpstream()
    with make_client(mock) as client:
        assert client.get("/__local/stats").json()["upstream_requests"] == 0
        client.post(
            "/responses",
            json={"model": "local-fake-model", "input": "hello"},
        )
        first = client.get("/__local/stats").json()
        client.post(
            "/responses/compact",
            json={"model": "local-fake-model", "input": "compact this"},
        )
        second = client.get("/__local/stats").json()
        reset = client.post("/__local/stats/reset").json()

    assert first["upstream_requests"] == 1
    assert second["upstream_requests"] == 2
    assert second["compact_summary_requests"] == 1
    assert reset["upstream_requests"] == 0


def test_adapter_uses_its_own_upstream_authorization() -> None:
    mock = MockUpstream()
    with make_client(
        mock,
        upstream_headers={"Authorization": "Bearer upstream-secret"},
    ) as client:
        response = client.post(
            "/responses",
            headers={"Authorization": "Bearer suite-local-token"},
            json={"model": "local-fake-model", "input": "hello"},
        )

    assert response.status_code == 200
    assert mock.calls[0]["authorization"] == "Bearer upstream-secret"


def test_hosted_upstream_requires_https_and_an_explicit_host_allowlist() -> None:
    assert (
        assert_upstream_url(
            "https://api.openai.com/v1",
            allow_hosted=True,
            allowed_host="api.openai.com",
        )
        == "https://api.openai.com/v1"
    )
    with pytest.raises(ConfigurationError):
        assert_upstream_url(
            "http://api.openai.com/v1",
            allow_hosted=True,
            allowed_host="api.openai.com",
        )
    with pytest.raises(ConfigurationError):
        assert_upstream_url(
            "https://example.test/v1",
            allow_hosted=True,
            allowed_host="api.openai.com",
        )
    with pytest.raises(ConfigurationError):
        assert_upstream_url(
            "https://user:pass@api.openai.com/v1",
            allow_hosted=True,
            allowed_host="api.openai.com",
        )


def test_hosted_credential_separation() -> None:
    with pytest.raises(ConfigurationError):
        assert_no_hosted_credentials(
            {"OPENRESPONSES_UPSTREAM_API_KEY": "redacted"}
        )
    with pytest.raises(ConfigurationError):
        assert_hosted_credentials({})
    with pytest.raises(ConfigurationError):
        assert_hosted_credentials({"OPENAI_API_KEY": "redacted"})
    assert (
        assert_hosted_credentials(
            {"OPENRESPONSES_UPSTREAM_API_KEY": "redacted"}
        )
        == "redacted"
    )


def test_gateway_fails_closed_for_hosted_or_credentialed_configuration() -> None:
    with pytest.raises(ConfigurationError):
        build_gateway_app("https://api.openai.com/v1")
    with pytest.raises(ConfigurationError):
        assert_loopback_url("https://api.openai.com/v1")
    with pytest.raises(ConfigurationError):
        assert_loopback_url("http://192.0.2.1:9999")
    with pytest.raises(ConfigurationError):
        assert_loopback_url("http://127.0.0.1:9999/v1")
    with pytest.raises(ConfigurationError):
        assert_no_hosted_credentials({"OPENAI_API_KEY": "redacted"})
    with pytest.raises(ConfigurationError):
        assert_no_hosted_credentials(
            {"OPENRESPONSES_UPSTREAM_API_KEY": "redacted"}
        )
    assert_no_hosted_credentials({})


def test_fake_upstream_is_independently_startable_and_tracks_requests() -> None:
    app = build_fake_app()
    stats: FakeStats = app.state.fake_stats
    with TestClient(app) as client:
        response = client.post(
            "/responses",
            json={"model": "local-fake-model", "input": "hello"},
        )
    assert response.status_code == 200
    assert stats.snapshot()["requests"] == 1
    assert stats.snapshot()["response_turns"] == 1


def receive_until_terminal(websocket: Any) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    while True:
        event = websocket.receive_json()
        events.append(event)
        if event.get("type") in {
            "response.completed",
            "response.failed",
            "response.incomplete",
            "error",
        }:
            return events
