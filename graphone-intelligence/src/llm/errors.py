from enum import Enum


class ErrorKind(str, Enum):
    TRANSIENT = "TRANSIENT"
    RATE_LIMIT = "RATE_LIMIT"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    AUTHENTICATION = "AUTHENTICATION"
    INVALID_REQUEST = "INVALID_REQUEST"
    PERMANENT = "PERMANENT"
    UNKNOWN = "UNKNOWN"


class LLMError(RuntimeError):
    def __init__(
        self,
        provider: str,
        kind: ErrorKind,
        message: str,
        retry_after_seconds: float | None = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.kind = kind
        self.retry_after_seconds = retry_after_seconds
