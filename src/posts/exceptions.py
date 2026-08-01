from enum import Enum
from dataclasses import dataclass
import openai
import httpx
import logging
class OpenAIAction(str, Enum):
    RETRY = "retry"
    CHECK_NETWORK = "check_network"
    RECREATE_RESOURCE = "recreate_resource"
    FAIL_USER = "fail_user"
    FAIL_FAST = "fail_fast"
    FORBIDDEN = "forbidden"
    UNKNOWN = "unknown"

@dataclass
class OpenAIErrorDecision:
    action: OpenAIAction
    message: str
    retryable: bool = False

def handle_openai_error(e: Exception) -> OpenAIErrorDecision:
    if isinstance(e, openai.RateLimitError):
        return OpenAIErrorDecision(
            action=OpenAIAction.RETRY,
            message="Rate limit reached when calling OpenAI API",
            retryable=True,
        )
    if isinstance(e, openai.APITimeoutError):
        return OpenAIErrorDecision(
            action=OpenAIAction.RETRY,
            message="OpenAI API request timed out",
            retryable=True,
        )
    if isinstance(e, openai.InternalServerError):
        return OpenAIErrorDecision(
            action=OpenAIAction.RETRY,
            message="OpenAI API internal server error",
            retryable=True,
        )
    if isinstance(e, openai.ConflictError):
        return OpenAIErrorDecision(
            action=OpenAIAction.RETRY,
            message="Conflict while calling OpenAI API",
            retryable=True,
        )
    if isinstance(e, openai.APIConnectionError):
        return OpenAIErrorDecision(
            action=OpenAIAction.CHECK_NETWORK,
            message="Network error while connecting to OpenAI API",
        )
    if isinstance(e, openai.NotFoundError):
        return OpenAIErrorDecision(
            action=OpenAIAction.RECREATE_RESOURCE,
            message="Requested OpenAI resource was not found",
        )
    if isinstance(e, openai.BadRequestError):
        return OpenAIErrorDecision(
            action=OpenAIAction.FAIL_USER,
            message="Bad request sent to OpenAI API",
        )
    if isinstance(e, openai.UnprocessableEntityError):
        return OpenAIErrorDecision(
            action=OpenAIAction.FAIL_USER,
            message="OpenAI API could not process the request",
        )
    if isinstance(e, openai.AuthenticationError):
        return OpenAIErrorDecision(
            action=OpenAIAction.FAIL_FAST,
            message="Invalid OpenAI credentials",
        )
    if isinstance(e, openai.PermissionDeniedError):
        return OpenAIErrorDecision(
            action=OpenAIAction.FORBIDDEN,
            message="Permission denied by OpenAI API",
        )
    return OpenAIErrorDecision(
        action=OpenAIAction.UNKNOWN,
        message=f"Unexpected OpenAI error: {type(e).__name__}",
    )

logger = logging.getLogger("http_client")

def handle_httpx_exception(e: Exception, *, context: str = "") -> None:
    """
    Inspects an exception against the httpx exception hierarchy and logs
    an appropriate message. Order matters: check the most specific
    subclasses BEFORE their parent classes, otherwise isinstance() will
    match the parent first and you'll never hit the specific branch.
    """
    prefix = f"[{context}] " if context else ""

    # --- Timeouts (subclass of TransportError) ---
    if isinstance(e, httpx.ConnectTimeout):
        logger.warning(f"{prefix}Timed out connecting to host: {e}")
    elif isinstance(e, httpx.ReadTimeout):
        logger.warning(f"{prefix}Timed out reading response: {e}")
    elif isinstance(e, httpx.WriteTimeout):
        logger.warning(f"{prefix}Timed out sending request data: {e}")
    elif isinstance(e, httpx.PoolTimeout):
        logger.warning(f"{prefix}Timed out waiting for a connection from the pool: {e}")
    elif isinstance(e, httpx.TimeoutException):
        # Catch-all in case a future subclass isn't handled above
        logger.warning(f"{prefix}Request timed out: {e}")

    # --- Network errors (subclass of TransportError) ---
    elif isinstance(e, httpx.ConnectError):
        logger.error(f"{prefix}Failed to establish connection: {e}")
    elif isinstance(e, httpx.ReadError):
        logger.error(f"{prefix}Network error while reading response: {e}")
    elif isinstance(e, httpx.WriteError):
        logger.error(f"{prefix}Network error while sending request: {e}")
    elif isinstance(e, httpx.CloseError):
        logger.error(f"{prefix}Network error while closing connection: {e}")
    elif isinstance(e, httpx.NetworkError):
        logger.error(f"{prefix}Network error: {e}")

    # --- Protocol errors (subclass of TransportError) ---
    elif isinstance(e, httpx.LocalProtocolError):
        logger.error(f"{prefix}Client violated the HTTP protocol: {e}")
    elif isinstance(e, httpx.RemoteProtocolError):
        logger.error(f"{prefix}Server sent malformed/invalid HTTP: {e}")
    elif isinstance(e, httpx.ProtocolError):
        logger.error(f"{prefix}Protocol error: {e}")

    # --- Other transport-level errors ---
    elif isinstance(e, httpx.ProxyError):
        logger.error(f"{prefix}Proxy connection error: {e}")
    elif isinstance(e, httpx.UnsupportedProtocol):
        logger.error(f"{prefix}Unsupported protocol in URL: {e}")
    elif isinstance(e, httpx.TransportError):
        logger.error(f"{prefix}Transport-level error: {e}")

    # --- Other RequestError subclasses (not transport-level) ---
    elif isinstance(e, httpx.DecodingError):
        logger.error(f"{prefix}Failed to decode response body (bad encoding): {e}")
    elif isinstance(e, httpx.TooManyRedirects):
        logger.warning(f"{prefix}Too many redirects: {e}")
    elif isinstance(e, httpx.RequestError):
        logger.error(f"{prefix}Request error: {e}")

    # --- Response received, but 4xx/5xx status ---
    elif isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if 400 <= status < 500:
            logger.warning(f"{prefix}Client error {status} for {e.request.url}: {e.response.text[:200]}")
        else:
            logger.error(f"{prefix}Server error {status} for {e.request.url}: {e.response.text[:200]}")

    # --- Catch-all for the base class ---
    elif isinstance(e, httpx.HTTPError):
        logger.error(f"{prefix}Unclassified HTTPX error: {e}")

    # --- Other non-hierarchy httpx exceptions worth knowing about ---
    elif isinstance(e, httpx.InvalidURL):
        logger.error(f"{prefix}Invalid URL: {e}")
    elif isinstance(e, httpx.CookieConflict):
        logger.error(f"{prefix}Cookie conflict: {e}")
    elif isinstance(e, httpx.StreamError):
        logger.error(f"{prefix}Stream handling error: {e}")

    else:
        logger.exception(f"{prefix}Unexpected non-httpx exception: {e}")