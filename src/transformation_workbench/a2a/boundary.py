"""Small local-only guards for the Week 3 A2A slice."""

from urllib.parse import urlparse

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})


def require_loopback_url(url: str) -> None:
    """Reject anything except an explicit local root HTTP endpoint."""
    parsed = urlparse(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in LOOPBACK_HOSTS
        or parsed.port is None
        or parsed.path not in ("", "/")
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(
            "A2A endpoints must be explicit loopback root HTTP URLs such as "
            "http://127.0.0.1:<port>."
        )
