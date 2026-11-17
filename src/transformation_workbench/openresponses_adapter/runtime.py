"""Loopback runtime and CLI for local or explicitly hosted upstream modes."""

from __future__ import annotations

import argparse
import asyncio
import os
import socket
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette

from .compaction import COMPACTION_KEY_ENV, CompactionCipher, CompactionError
from .gateway import (
    ConfigurationError,
    assert_loopback_url,
    assert_upstream_url,
    build_gateway_app,
)

UPSTREAM_KEY_ENV = "OPENRESPONSES_UPSTREAM_API_KEY"
HOSTED_CREDENTIAL_ENV = (
    "OPENAI_API_KEY",
    "OPENRESPONSES_API_KEY",
    UPSTREAM_KEY_ENV,
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "OPENCODE_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
)


def assert_no_hosted_credentials(
    environ: Mapping[str, str] | None = None,
) -> None:
    source = os.environ if environ is None else environ
    configured = [name for name in HOSTED_CREDENTIAL_ENV if source.get(name)]
    if configured:
        raise ConfigurationError(
            "Hosted credential environment variables are set; "
            "run the local adapter with a clean environment."
        )


def assert_hosted_credentials(
    environ: Mapping[str, str] | None = None,
) -> str:
    source = os.environ if environ is None else environ
    configured = [
        name
        for name in HOSTED_CREDENTIAL_ENV
        if name != UPSTREAM_KEY_ENV and source.get(name)
    ]
    if configured:
        raise ConfigurationError(
            "Only the dedicated upstream key variable may be set for hosted mode."
        )
    key = source.get(UPSTREAM_KEY_ENV)
    if not key:
        raise ConfigurationError(
            "The dedicated upstream API key is not configured."
        )
    return key


def _bind_loopback_socket() -> tuple[socket.socket, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    return sock, int(sock.getsockname()[1])


@asynccontextmanager
async def serve_loopback(
    app_factory: Callable[[str], Starlette],
) -> AsyncIterator[str]:
    sock, port = _bind_loopback_socket()
    base_url = f"http://127.0.0.1:{port}"
    server: uvicorn.Server | None = None
    task: asyncio.Task[None] | None = None
    try:
        app = app_factory(base_url)
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                log_level="warning",
                access_log=False,
            )
        )
        task = asyncio.create_task(server.serve(sockets=[sock]))
        while not server.started:
            if task.done():
                await task
            await asyncio.sleep(0.01)
        yield base_url
    finally:
        if server is not None:
            server.should_exit = True
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=10)
            except Exception:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        sock.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the loopback Open Responses adapter prototype."
    )
    parser.add_argument("--upstream-url", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--compaction-ttl-seconds", type=int, default=24 * 60 * 60)
    parser.add_argument("--allow-hosted-upstream", action="store_true")
    parser.add_argument("--allowed-upstream-host")
    parser.add_argument("--upstream-auth-header", default="Authorization")
    parser.add_argument("--upstream-auth-scheme", default="Bearer")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise ConfigurationError("gateway host must be loopback")
    if args.allow_hosted_upstream:
        if not args.allowed_upstream_host:
            raise ConfigurationError(
                "hosted mode requires an explicit allowed upstream host"
            )
        upstream_key = assert_hosted_credentials()
        os.environ.pop(UPSTREAM_KEY_ENV, None)
        headers = {
            args.upstream_auth_header: (
                f"{args.upstream_auth_scheme} {upstream_key}".strip()
            )
        }
    else:
        assert_no_hosted_credentials()
        headers = {}
    if args.allow_hosted_upstream:
        upstream_url = assert_upstream_url(
            args.upstream_url,
            allow_hosted=True,
            allowed_host=args.allowed_upstream_host,
        )
    else:
        upstream_url = assert_loopback_url(args.upstream_url)
    try:
        cipher = CompactionCipher.from_env(
            ttl_seconds=args.compaction_ttl_seconds,
        )
        os.environ.pop(COMPACTION_KEY_ENV, None)
    except CompactionError as exc:
        raise ConfigurationError(str(exc)) from exc
    app = build_gateway_app(
        upstream_url,
        timeout=args.timeout,
        compaction_cipher=cipher,
        upstream_headers=headers,
        allow_hosted_upstream=args.allow_hosted_upstream,
        allowed_upstream_host=args.allowed_upstream_host,
    )
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()
