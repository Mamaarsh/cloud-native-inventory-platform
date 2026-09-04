from dataclasses import dataclass
from uuid import uuid4

class NotificationProviderError(Exception):
    """Expected, retryable failure reported by a notification provider."""

@dataclass(frozen=True)
class NotificationProviderResult:
    success: bool
    provider_reference: str | None = None
    error: str = ""

class MockNotificationProvider:
    def send(self, *, recipient: str, message: str):
        return NotificationProviderResult(
            success=True,
            provider_reference=f"mock_{uuid4().hex}",
        )

mock_notification_provider = MockNotificationProvider()