class AutomationError(RuntimeError):
    """Base error for reusable browser automation helpers."""


class SelectorNotFoundError(AutomationError):
    """Raised when a configured selector cannot resolve a usable element."""


class PageStateError(AutomationError):
    """Raised when the page is not in the expected state for the next action."""


class VerificationError(AutomationError):
    """Raised when post-submit verification does not pass."""
