"""Error taxonomy for the Zoho Inventory connector.

The MCP layer translates these into structured error payloads so an agent can
react appropriately (retry later, stop, or rephrase the query) instead of
parsing a stack trace. Every error carries a retryable flag.
"""

from __future__ import annotations


class ZohoError(Exception):
    """Base class for every connector error."""

    retryable: bool = False

    def __init__(self, message: str, *, code: str | int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class AuthError(ZohoError):
    """Credentials are missing, invalid, or revoked. The agent should stop."""

    retryable = False


class RateLimitError(ZohoError):
    """Zoho throttled the request or the daily quota is spent. Retry later."""

    retryable = True

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class NotFoundError(ZohoError):
    """The requested resource does not exist. The agent should rephrase."""

    retryable = False


class ValidationError(ZohoError):
    """Our request was malformed or used an unsupported parameter."""

    retryable = False


class UpstreamError(ZohoError):
    """Zoho server error or a network failure. Retryable with backoff."""

    retryable = True
