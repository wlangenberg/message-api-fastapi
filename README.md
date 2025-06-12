# Message Service API

Simple project for learning more about the FastAPI web framework in practice.  

## Summary

This is a REST API for submitting messages to recipients, saved in an in-memory "database".

## Features

- **Send Messages**: Submit messages to recipients identified by anything like email, phone, username, etc.
- **Fetch New Messages**: Retrieve unread messages and mark them as read
- **Message History**: Get paginated message history including previously read messages
- **Delete Messages**: Remove single or multiple messages
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

## Architecture & Design Decisions

### Storage Layer
Thread-safe in-memory storage. 
This makes the service stateful, meaning you can't really scale horizontally that easily. 
However, the application uses an interface for the storage which makes it easy to at least implement new storages and just make sure to implement the MessageStore interface.
See the interface in: `storage_interface.py`.

The service uses a thread-safe in-memory storage implementation.
This design makes the service stateful, which limits the ability to scale horizontally out of the box.
However, the storage logic is abstracted behind a MessageStore interface, allowing for easy replacement or extension with alternative storage backends.

You can find the interface definition in: `storage_interface.py`.

### API Design
The API follows RESTful principles, utilizing appropriate HTTP methods and status codes to ensure clarity and consistency.
Input validation is handled through Pydantic models, ensuring data integrity and type safety.
The API is documented using OpenAPI/Swagger, complete with example requests and responses.
Error responses are generally consistent and meaningful, though some default Pydantic error messages may still be returned in certain cases.

### Data Models

- **Message:**  
  - message_id: UUID
  - recipient: str
  - ?sender: str
  - content: str
  - status: Enum(READ/UNREAD)
  - timestamp: datetime

## Requirements

- Python 3.11+
- GNU Make (Optional)

## Setup

Clone repo  
```bash
git clone git@github.com:wlangenberg/message-api-fastapi.git
cd message-api-fastapi
```

If you have `make` installed:  
```bash
make install
make run
```

If you do not have `make` installed:
```bash
# Install dependencies
pip install -r requirements.txt

# Run the service in dev mode
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# NOTE: The service is not production ready so I have not spent any time researching how to best serve the app in prod mode.
```

This will start the API and bind it to all network interfaces on port 8000.

- Accessible locally at: http://localhost:8080
- API documentation: http://localhost:8080/docs


## API Endpoints

### Core Functionality

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/messages` | Fetch all messages paginated (does not mark them as read) |
| GET | `/messages/{recipient}` | Fetch all messages paginated for a given recipient (does not mark them as read) |
| GET | `/messages/new/{recipient}` | Fetch new (unread) messages for a given recipient and marks them as read |
| POST | `/messages` | Send a new message |
| DELETE | `/messages/{message_id}` | Delete a single message |
| DELETE | `/messages` | Delete multiple messages |

### Additional Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/recipients` | List all recipients that has got any message (unread or read)|
| GET | `/stats` | Service statistics over amount of recipients, total messages sent, read, unread and messages for each recipient |
| GET | `/docs` | Swagger, API documentation |

## Usage Examples

### 1. Send a Message

```bash
curl -X POST http://localhost:8080/messages \
  -H 'Content-Type: application/json' \
  -d '{
    "recipient": "user@example.com",
    "content": "Hello, this is a test message!",
    "sender": "admin@example.com"
  }'
```

**Response:**
```json
{
  "id": "1f08f927-6dab-4fe8-8faa-18ea2bbc1245",
  "recipient": "user@example.com",
  "content": "Hello, this is a test message!",
  "sender": "admin@example.com",
  "timestamp": "2025-06-12T12:00:00Z",
  "status": "unread"
}
```

### 2. Fetch New Messages

```bash
curl http://localhost:8080/messages/new/user@example.com
```

**Response:**
```json
{
  "messages": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "recipient": "user@example.com",
      "content": "Hello, this is a test message!",
      "sender": "admin@example.com",
      "timestamp": "2025-06-11T10:00:00Z",
      "status": "read"
    }
  ],
  "total": 1,
  "recipient": "user@example.com"
}
```

### 3. Fetch All Messages with Pagination

```bash
curl 'http://localhost:8080/messages?start=0&limit=10'
```
**Response:**
```json
{
  "messages": [
    {
      "id": "a5316885-81d1-4c52-8bb5-1168acfd0fa9",
      "recipient": "admin@example.com",
      "content": "Hello worlds!",
      "sender": "Frank",
      "timestamp": "2025-06-12T20:29:01.846987Z",
      "status": "read"
    },
    {
      "id": "b15f3413-2a45-4d54-8aac-1f2c62a26074",
      "recipient": "user@example.com",
      "content": "Hello there!",
      "sender": "Sam",
      "timestamp": "2025-06-12T20:28:00.624706Z",
      "status": "unread"
    }
  ],
  "total": 2,
  "start": 0,
  "limit": 10,
}
```

### 4. Delete a Message

```bash
curl -X DELETE http://localhost:8080/messages/3fec4cc2-6c99-4444-bb5c-bc75a0a4e0ea
```

**Response:**
```json
{
  "deleted_count": 1,
  "message_ids": [
    "3fec4cc2-6c99-4444-bb5c-bc75a0a4e0ea"
  ],
  "timestamp": "2025-06-12T20:26:23.747063Z"
}
```

### 5. Delete Multiple Messages

```bash
curl -X DELETE \
  'http://localhost:8080/messages?message_ids=e191fa81-4a8c-4475-8441-ab67bb413144&message_ids=31bf5b87-7dc7-4b3b-8290-1bf640232d8b' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "deleted_count": 2,
  "message_ids": [
    "e191fa81-4a8c-4475-8441-ab67bb413144",
    "31bf5b87-7dc7-4b3b-8290-1bf640232d8b"
  ],
  "timestamp": "2025-06-12T20:23:22.644287Z"
}
```

## Project Structure

```
message-service/
├── Makefile                 # Build and run commands
├── README.md                # This documentation
├── exceptions.py            # Custom exception classes
├── main.py                  # FastAPI application
├── models.py                # Pydantic models and data structures
├── requirements.txt         # Python dependencies
├── routes.py                # FastAPI routes
├── storage_inmemory.py      # In-memory storage implementation
├── storage_interface.py     # Interface for storage layer
└── test_message_service.py  # Comprehensive test suite
```
