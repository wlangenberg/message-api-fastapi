from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from routes import get_storage
from storage_inmemory import InMemoryStore

# Create test client
client = TestClient(app)

# Global in-memory store
test_storage = InMemoryStore()


# Override storage dependency for testing
def override_get_storage():
    return test_storage


app.dependency_overrides[get_storage] = override_get_storage


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear storage before each test"""
    test_storage.clear_all()


class TestSendMessage:
    def test_send_message_success(self):
        """Test successful message creation"""
        # Arrange
        message_data = {
            "recipient": "user@example.com",
            "content": "Hello, world!",
            "sender": "admin@example.com",
        }

        # Act
        response = client.post("/messages", json=message_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["recipient"] == message_data["recipient"]
        assert data["content"] == message_data["content"]
        assert data["sender"] == message_data["sender"]
        assert data["status"] == "unread"
        assert "id" in data
        assert "timestamp" in data

    def test_send_message_without_sender(self):
        """Test sending message without sender"""
        # Arrange
        message_data = {"recipient": "user", "content": "Hello!"}

        # Act
        response = client.post("/messages", json=message_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["recipient"] == message_data["recipient"]
        assert data["content"] == message_data["content"]
        assert data["sender"] is None

    def test_send_message_empty_content(self):
        """Test validation with empty content"""
        # Arrange
        message_data = {"recipient": "user@example.com", "content": ""}

        # Act
        response = client.post("/messages", json=message_data)

        # Assert
        assert response.status_code == 422

    def test_send_message_empty_recipient(self):
        """Test validation with empty recipient"""
        # Arrange
        message_data = {"recipient": "", "content": "Hello, world!"}

        # Act
        response = client.post("/messages", json=message_data)

        # Assert
        assert response.status_code == 422


class TestFetchNewMessages:
    """Test fetching new messages functionality"""

    def test_fetch_new_messages_success(self):
        """Test fetching new messages"""
        # Arrange
        message_data = {"recipient": "user@example.com", "content": "Hello, world!"}
        client.post("/messages", json=message_data)

        # Act
        response = client.get("/messages/new/user@example.com")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["recipient"] == message_data["recipient"]
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == message_data["content"]
        assert data["messages"][0]["status"] == "read"

    def test_fetch_new_messages_nonexistent_recipient(self):
        # Arrange

        # Act
        response = client.get("/messages/new/nonexistent@example.com")

        # Assert
        assert response.status_code == 404

    def test_fetch_new_messages_multiple(self):
        """Test fetching multiple new messages"""
        # Arrange
        recipient = "user@example.com"
        for i in range(3):
            client.post(
                "/messages",
                json={"recipient": recipient, "content": f"Message {i + 1}"},
            )

        # Act
        response = client.get(f"/messages/new/{recipient}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["messages"]) == 3

    def test_fetch_new_messages_twice(self):
        """Test that messages are marked as read after first fetch"""
        # Arrange
        recipient = "user@example.com"
        client.post(
            "/messages", json={"recipient": recipient, "content": "Hello, world!"}
        )

        # Act
        response1 = client.get(f"/messages/new/{recipient}")
        response2 = client.get(f"/messages/new/{recipient}")

        # Assert
        assert response1.status_code == 200
        assert response1.json()["total"] == 1
        assert response2.status_code == 200
        assert response2.json()["total"] == 0


class TestFetchMessages:
    """Test fetching messages with pagination"""

    def test_fetch_messages_recipient_success(self):
        """Test fetching all messages for a recipient with pagination"""
        # Arrange
        recipient = "user@example.com"
        for i in range(5):
            client.post(
                "/messages",
                json={"recipient": recipient, "content": f"Message {i + 1}"},
            )

        # Act
        response = client.get(f"/messages/{recipient}?start=0&limit=3")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["messages"]) == 3
        assert data["start"] == 0
        assert data["limit"] == 3

    def test_fetch_messages_success(self):
        """Test fetching all messages with pagination"""
        # Arrange
        recipient = "user.1337"
        for i in range(10):
            client.post(
                "/messages",
                json={"recipient": recipient, "content": f"Message {i + 1}"},
            )

        # Act
        response = client.get("/messages/?start=0&limit=6")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["messages"]) == 6
        assert data["start"] == 0
        assert data["limit"] == 6

    def test_fetch_messages_pagination(self):
        """Test message pagination"""
        # Arrange
        recipient = "user@example.com"
        for i in range(10):
            client.post(
                "/messages",
                json={"recipient": recipient, "content": f"Message {i + 1}"},
            )

        # Act & Assert
        response1 = client.get(f"/messages/{recipient}?start=0&limit=5")
        data1 = response1.json()
        assert len(data1["messages"]) == 5
        assert data1["total"] == 10

        response2 = client.get(f"/messages/{recipient}?start=5&limit=5")
        data2 = response2.json()
        assert len(data2["messages"]) == 5
        assert data2["total"] == 10

    def test_fetch_messages_nonexistent_recipient(self):
        # Arrange

        # Act
        response = client.get("/messages/nonexistent@example.com")

        # Assert
        assert response.status_code == 404

    def test_fetch_messages_default_pagination(self):
        """Test default pagination parameters"""
        # Arrange
        recipient = "user@example.com"
        client.post(
            "/messages", json={"recipient": recipient, "content": "Hello, world!"}
        )

        # Act
        response = client.get(f"/messages/{recipient}")

        # Assert
        data = response.json()
        assert data["start"] == 0
        assert data["limit"] == 10


class TestDeleteMessage:
    """Test message deletion functionality"""

    def test_delete_message_success(self):
        # Arrange
        response = client.post(
            "/messages",
            json={"recipient": "user@example.com", "content": "Hello, world!"},
        )
        message_id = response.json()["id"]

        # Act
        response = client.delete(f"/messages/{message_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 1
        assert message_id in [str(mid) for mid in data["message_ids"]]

    def test_delete_nonexistent_message(self):
        # Arrange
        fake_id = str(uuid4())

        # Act
        response = client.delete(f"/messages/{fake_id}")

        # Assert
        assert response.status_code == 404


class TestDeleteMultipleMessages:
    """Test multiple message deletion functionality"""

    def test_delete_multiple_messages_success(self):
        # Arrange
        message_ids = []
        for i in range(3):
            response = client.post(
                "/messages",
                json={"recipient": "user@example.com", "content": f"Message {i + 1}"},
            )
            message_ids.append(response.json()["id"])

        # Act
        response = client.delete("/messages", params={"message_ids": message_ids})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 3
        assert len(data["message_ids"]) == 3

    def test_delete_multiple_messages_partial(self):
        # Arrange
        response = client.post(
            "/messages",
            json={"recipient": "user@example.com", "content": "Hello, world!"},
        )
        existing_id = response.json()["id"]
        fake_id = str(uuid4())
        message_ids = [existing_id, fake_id]

        # Act
        response = client.delete("/messages", params={"message_ids": message_ids})

        # Assert
        assert response.status_code == 200
        assert response.json()["deleted_count"] == 1

    def test_delete_multiple_messages_empty_list(self):
        # Act
        response = client.delete("/messages", params={"message_ids": []})

        # Assert
        assert response.status_code == 400

    def test_delete_multiple_messages_too_many(self):
        # Arrange
        message_ids = [str(uuid4()) for _ in range(101)]

        # Act
        response = client.delete("/messages", params={"message_ids": message_ids})

        # Assert
        assert response.status_code == 400


class TestListRecipients:
    """Test recipient listing functionality"""

    def test_list_recipients_empty(self):
        # Arrange

        # Act
        response = client.get("/recipients")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_list_recipients_with_messages(self):
        # Arrange
        recipients = ["user1@example.com", "user2@example.com", "user3@example.com"]
        for r in recipients:
            client.post("/messages", json={"recipient": r, "content": "Hello!"})

        # Act
        response = client.get("/recipients")

        # Assert
        assert response.status_code == 200
        assert set(response.json()) == set(recipients)


class TestStatistics:
    """Test statistics functionality"""

    def test_get_statistics_empty(self):
        # Arrange

        # Act
        response = client.get("/stats")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 0
        assert data["total_recipients"] == 0
        assert data["total_read"] == 0
        assert data["total_unread"] == 0

    def test_get_statistics_with_messages(self):
        # Arrange
        for i in range(3):
            client.post(
                "/messages",
                json={"recipient": f"user{i}@example.com", "content": f"Message {i}"},
            )

        # Mark one message as read
        client.get("/messages/new/user0@example.com")

        # Act
        response = client.get("/stats")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 3
        assert data["total_recipients"] == 3
        assert data["total_read"] == 1
        assert data["total_unread"] == 2


class TestIntegrationScenarios:
    """Some Integration tests"""

    def test_complete_message_lifecycle(self):
        # Arrange
        message_data = {
            "recipient": "Willie",
            "content": "Winter is coming!",
            "sender": "Jon Snow",
        }

        # Act & Assert
        response = client.post("/messages", json=message_data)
        assert response.status_code == 201
        message_id = response.json()["id"]

        response = client.get("/messages/new/Willie")
        assert response.json()["total"] == 1

        response = client.get("/messages/Willie")
        assert response.json()["total"] == 1

        response = client.delete(f"/messages/{message_id}")
        assert response.status_code == 200

        response = client.get("/messages/Willie")
        assert response.status_code == 404

    def test_multiple_recipients_scenario(self):
        # Arrange
        recipients = ["willie", "spiderman", "batman"]
        for i, r in enumerate(recipients):
            for _ in range(i + 1):
                client.post(
                    "/messages", json={"recipient": r, "content": "Important Message"}
                )

        # Act & Assert
        for i, r in enumerate(recipients):
            response = client.get(f"/messages/{r}")
            assert response.json()["total"] == i + 1

        response = client.get("/stats")
        data = response.json()
        assert data["total_messages"] == 6
        assert data["total_recipients"] == 3

    def test_create_and_get_ordered_result_back(self):
        # Arrange
        amount_of_messages = 100
        message_data = [
            {"recipient": f"{i}", "content": "Winter is coming!", "sender": "Bob"}
            for i in range(amount_of_messages)
        ]

        for message in message_data:
            client.post("/messages", json=message)

        # Act & Assert
        response = client.get("/messages?start=0&limit=200")
        data = response.json()

        # order should be the "descending by timestamp", so reveresed from the order we sent
        original_recipients = [str(i) for i in range(amount_of_messages)]
        original_recipients.reverse()
        message_recipients = list(
            map(lambda x: x.get("recipient"), data.get("messages"))
        )

        assert original_recipients == message_recipients


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
