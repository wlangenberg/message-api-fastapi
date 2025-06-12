class MessageServiceError(Exception):
    """Base exception for message service errors"""

    pass


class MessageNotFoundError(MessageServiceError):
    """Raised when a requested message cannot be found"""

    pass


class RecipientNotFoundError(MessageServiceError):
    """Raised when a recipient has no messages"""

    pass


class InvalidMessageError(MessageServiceError):
    """Raised when message data is invalid"""

    pass


class StorageError(MessageServiceError):
    """Raised when storage operations fail"""

    pass
