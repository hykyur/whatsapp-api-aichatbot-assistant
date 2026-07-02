from enum import Enum
from dataclasses import dataclass
import openai

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