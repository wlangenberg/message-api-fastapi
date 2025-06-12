from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from models import Message


class MessageStore(ABC):
    @abstractmethod
    def create_message(
        self, recipient: str, content: str, sender: Optional[str] = None
    ) -> Message:
        pass

    @abstractmethod
    def get_message(self, message_id: UUID) -> Message:
        pass

    @abstractmethod
    def get_new_messages(self, recipient: str) -> List[Message]:
        pass

    @abstractmethod
    def get_messages_paginated_all(
        self, start: int = 0, limit: int = 10
    ) -> Tuple[List[Message], int]:
        pass

    @abstractmethod
    def get_messages_paginated(
        self, recipient: str, start: int = 0, limit: int = 10
    ) -> Tuple[List[Message], int]:
        pass

    @abstractmethod
    def delete_message(self, message_id: UUID) -> None:
        pass

    @abstractmethod
    def delete_multiple_messages(self, message_ids: List[UUID]) -> List[UUID]:
        pass

    @abstractmethod
    def get_all_recipients(self) -> List[str]:
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def clear_all(self) -> None:
        pass
