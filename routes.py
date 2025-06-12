import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from exceptions import MessageNotFoundError, RecipientNotFoundError
from models import (
    DeleteResponse,
    MessageCreate,
    MessageResponse,
    MessagesResponsePaginated,
    MessagesResponseNew,
    MessagesResponseRecipientPaginated,
)
from storage_inmemory import InMemoryStore
from storage_interface import MessageStore

logger = logging.getLogger(__name__)
router = APIRouter()
storage = InMemoryStore()


def get_storage() -> MessageStore:
    return storage


@router.get("/", tags=["Health"])
async def root():
    return {
        "service": "Willies Message API",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/messages", response_model=MessagesResponsePaginated, tags=["Messages"])
async def fetch_messages_all(
    start: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=500),
    storage: MessageStore = Depends(get_storage),
):
    try:
        messages, total = storage.get_messages_paginated_all(start, limit)
        logger.info(
            f"Retrieved {len(messages)} messages (start={start}, limit={limit})"
        )
        return MessagesResponsePaginated(
            messages=[MessageResponse.from_message(msg) for msg in messages],
            total=total,
            start=start,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


@router.get(
    "/messages/new/{recipient}",
    response_model=MessagesResponseNew,
    tags=["Messages"],
)
async def fetch_new_messages(
    recipient: str, storage: MessageStore = Depends(get_storage)
):
    try:
        messages = storage.get_new_messages(recipient)
        logger.info(
            f"Retrieved {len(messages)} new messages for recipient: {recipient}"
        )
        return MessagesResponseNew(
            messages=[MessageResponse.from_message(msg) for msg in messages],
            total=len(messages),
            recipient=recipient,
        )
    except RecipientNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching new messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


@router.get(
    "/messages/{recipient}", response_model=MessagesResponseRecipientPaginated, tags=["Messages"]
)
async def fetch_messages(
    recipient: str,
    start: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    storage: MessageStore = Depends(get_storage),
):
    try:
        messages, total = storage.get_messages_paginated(recipient, start, limit)
        logger.info(f"Retrieved {len(messages)} messages for recipient: {recipient}")
        return MessagesResponseRecipientPaginated(
            messages=[MessageResponse.from_message(msg) for msg in messages],
            total=total,
            recipient=recipient,
            start=start,
            limit=limit,
        )
    except RecipientNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


@router.post("/messages", response_model=MessageResponse, tags=["Messages"])
async def send_message(
    message_data: MessageCreate, storage: MessageStore = Depends(get_storage)
):
    try:
        message = storage.create_message(
            recipient=message_data.recipient,
            content=message_data.content,
            sender=message_data.sender,
        )
        logger.info(
            f"Message created: {message.id} for recipient: {message_data.recipient}"
        )
        return MessageResponse.from_message(message)
    except Exception as e:
        logger.error(f"Error creating message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create message")


@router.delete("/messages", response_model=DeleteResponse, tags=["Messages"])
async def delete_multiple_messages(
    message_ids: Optional[List[UUID]] = Query(None),
    storage: MessageStore = Depends(get_storage),
):
    if not message_ids:
        raise HTTPException(status_code=400, detail="No message IDs provided")
    if len(message_ids) > 100:
        raise HTTPException(status_code=400, detail="Too many message IDs (max 100)")
    try:
        deleted_ids = storage.delete_multiple_messages(message_ids)
        logger.info(f"Deleted {len(deleted_ids)} messages")
        return DeleteResponse(
            deleted_count=len(deleted_ids),
            message_ids=deleted_ids,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Error deleting messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete messages")


@router.delete(
    "/messages/{message_id}", response_model=DeleteResponse, tags=["Messages"]
)
async def delete_message(
    message_id: UUID, storage: MessageStore = Depends(get_storage)
):
    try:
        storage.delete_message(message_id)
        logger.info(f"Deleted message: {message_id}")
        return DeleteResponse(
            deleted_count=1,
            message_ids=[message_id],
            timestamp=datetime.now(timezone.utc),
        )
    except MessageNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete message")


@router.get("/recipients", response_model=List[str], tags=["Recipients"])
async def list_recipients(storage: MessageStore = Depends(get_storage)):
    try:
        return storage.get_all_recipients()
    except Exception as e:
        logger.error(f"Error fetching recipients: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch recipients")


@router.get("/stats", tags=["Statistics"])
async def get_statistics(storage: MessageStore = Depends(get_storage)):
    try:
        return storage.get_statistics()
    except Exception as e:
        logger.error(f"Error fetching statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")
