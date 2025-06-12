import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from exceptions import MessageNotFoundError, RecipientNotFoundError
from models import Message
from storage_interface import MessageStore

logger = logging.getLogger(__name__)


class InMemoryStore(MessageStore):
    def __init__(self):
        self._lock = threading.RLock()
        self._messages: Dict[UUID, Message] = {}
        self._recipient_messages: Dict[str, List[UUID]] = defaultdict(list)
        self._read_status: Dict[str, Set[UUID]] = defaultdict(set)

    def create_message(
        self, recipient: str, content: str, sender: Optional[str] = None
    ) -> Message:
        """
        Create and store a new message

        Args:
            recipient: Message recipient identifier
            content: Message content
            sender: Optional sender identifier

        Returns:
            Message: The created message object
        """
        with self._lock:
            message = Message(recipient=recipient, content=content, sender=sender)
            self._messages[message.id] = message
            self._recipient_messages[recipient].append(message.id)
            logger.debug(f"Created message {message.id} for recipient {recipient}")
            return message

    def get_message(self, message_id: UUID) -> Message:
        """
        Retrieve a single message by ID

        Args:
            message_id: UUID of the message

        Returns:
            Message: The requested message

        Raises:
            MessageNotFoundError: If message doesn't exist
        """
        with self._lock:
            if message_id not in self._messages:
                raise MessageNotFoundError(f"Message {message_id} not found")
            return self._messages[message_id]

    def get_new_messages(self, recipient: str) -> List[Message]:
        """
        Get new (unread) messages for a recipient and mark them as read

        Args:
            recipient: Recipient identifier

        Returns:
            List[Message]: List of new messages

        Raises:
            RecipientNotFoundError: If recipient has no messages
        """
        with self._lock:
            if recipient not in self._recipient_messages:
                raise RecipientNotFoundError(
                    f"No messages found for recipient {recipient}"
                )

            # Get unread message IDs
            message_ids = self._recipient_messages[recipient]
            read_ids = self._read_status[recipient]
            new_message_ids = [mid for mid in message_ids if mid not in read_ids]

            # Retrieve messages and mark as read
            new_messages = []
            for message_id in new_message_ids:
                if message_id in self._messages:
                    message = self._messages[message_id]
                    message.mark_as_read()
                    self._read_status[recipient].add(message_id)
                    new_messages.append(message)

            new_messages.sort(key=lambda m: m.timestamp, reverse=True)

            logger.debug(
                f"Retrieved {len(new_messages)} new messages for recipient {recipient}"
            )
            return new_messages

    def get_messages_paginated_all(
        self, start: int = 0, limit: int = 10
    ) -> Tuple[List[Message], int]:
        """
        Get paginated messages for a recipient (including previously read)

        Args:
            recipient: Recipient identifier
            start: Start index (0-based)
            limit: Maximum number of messages to return

        Returns:
            Tuple[List[Message], int]: (messages, total_count)

        Raises:
            RecipientNotFoundError: If recipient has no messages
        """
        with self._lock:
            all_messages = list(self._messages.values())
            total_count = len(all_messages)
            all_messages.sort(key=lambda m: m.timestamp, reverse=True)

            # Pagination
            end = start + limit
            paginated_messages = all_messages[start:end]

            logger.debug(
                f"Retrieved {len(paginated_messages)} messages (start={start}, limit={limit})"
            )
            return paginated_messages, total_count

    def get_messages_paginated(
        self, recipient: str, start: int = 0, limit: int = 10
    ) -> Tuple[List[Message], int]:
        """
        Get paginated messages for a recipient (including previously read)

        Args:
            recipient: Recipient identifier
            start: Start index (0-based)
            limit: Maximum number of messages to return

        Returns:
            Tuple[List[Message], int]: (messages, total_count)

        Raises:
            RecipientNotFoundError: If recipient has no messages
        """
        with self._lock:
            if recipient not in self._recipient_messages:
                raise RecipientNotFoundError(
                    f"No messages found for recipient {recipient}"
                )

            message_ids = self._recipient_messages[recipient]
            total_count = len(message_ids)

            # Get messages and sort by timestamp (newest first)
            all_messages = []
            for message_id in message_ids:
                if message_id in self._messages:
                    all_messages.append(self._messages[message_id])

            all_messages.sort(key=lambda m: m.timestamp, reverse=True)

            # Apply pagination
            end = start + limit
            paginated_messages = all_messages[start:end]

            logger.debug(
                f"Retrieved {len(paginated_messages)} messages (start={start}, limit={limit}) for recipient {recipient}"
            )
            return paginated_messages, total_count

    def delete_message(self, message_id: UUID) -> None:
        """
        Delete a single message

        Args:
            message_id: UUID of the message to delete

        Raises:
            MessageNotFoundError: If message doesn't exist
        """
        with self._lock:
            if message_id not in self._messages:
                raise MessageNotFoundError(f"Message {message_id} not found")

            message = self._messages[message_id]
            recipient = message.recipient

            # Remove from main storage
            del self._messages[message_id]

            # Remove from recipient index
            if recipient in self._recipient_messages:
                if message_id in self._recipient_messages[recipient]:
                    self._recipient_messages[recipient].remove(message_id)

                # Clean up empty recipient entry
                if not self._recipient_messages[recipient]:
                    del self._recipient_messages[recipient]

            # Remove from read status
            if recipient in self._read_status:
                self._read_status[recipient].discard(message_id)

                # Clean up empty read status entry
                if not self._read_status[recipient]:
                    del self._read_status[recipient]

            logger.debug(f"Deleted message {message_id}")

    def delete_multiple_messages(self, message_ids: List[UUID]) -> List[UUID]:
        """
        Delete multiple messages

        Args:
            message_ids: List of message UUIDs to delete

        Returns:
            List[UUID]: List of successfully deleted message IDs
        """
        deleted_ids = []

        for message_id in message_ids:
            try:
                self.delete_message(message_id)
                deleted_ids.append(message_id)
            except MessageNotFoundError:
                logger.warning(f"Message {message_id} not found during bulk delete")
                continue

        logger.debug(f"Deleted {len(deleted_ids)} out of {len(message_ids)} messages")
        return deleted_ids

    def get_all_recipients(self) -> List[str]:
        """
        Get all recipients that have received messages

        Returns:
            List[str]: List of recipient identifiers
        """
        with self._lock:
            return list(self._recipient_messages.keys())

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics

        Returns:
            Dict[str, Any]: Statistics about stored messages
        """
        with self._lock:
            total_messages = len(self._messages)
            total_recipients = len(self._recipient_messages)

            # Calculate read/unread counts
            total_read = sum(len(read_set) for read_set in self._read_status.values())
            total_unread = total_messages - total_read

            # Messages per recipient
            messages_per_recipient = {
                recipient: len(message_ids)
                for recipient, message_ids in self._recipient_messages.items()
            }

            return {
                "total_messages": total_messages,
                "total_recipients": total_recipients,
                "total_read": total_read,
                "total_unread": total_unread,
                "messages_per_recipient": messages_per_recipient,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def clear_all(self) -> None:
        """
        Clear all stored data
        """
        with self._lock:
            self._messages.clear()
            self._recipient_messages.clear()
            self._read_status.clear()
            logger.info("Cleared all stored messages")
