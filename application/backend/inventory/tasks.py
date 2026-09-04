import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from inventory.models import Notification
from inventory.services.notification_providers import (
    NotificationProviderError,
    mock_notification_provider,
)

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=2,
    acks_late=True,
    reject_on_worker_lost=True,
)
def send_notification(self, notification_id):
    retry_error = None
    with transaction.atomic():
        try:
            notification = (
                Notification.objects.select_for_update()
                .select_related("user")
                .get(pk=notification_id)
            )
        except Notification.DoesNotExist:
            return "missing"
        if notification.status in {
            Notification.Status.SENT,
            Notification.Status.FAILED,
        }:
            return notification.status
        attempt_number = notification.attempts + 1
        logger.info(
            "Notification delivery started notification=%s attempt=%s",
            notification.pk,
            attempt_number,
        )
        recipient = notification.user.email or notification.user.username
        try:
            result = mock_notification_provider.send(
                recipient=recipient,
                message=notification.message,
            )
        except NotificationProviderError as exc:
            result = None
            retry_error = str(exc)
        notification.attempts += 1
        if result is not None and result.success:
            notification.status = Notification.Status.SENT
            notification.provider_reference = result.provider_reference
            notification.last_error = ""
            notification.sent_at = timezone.now()
        else:
            result_error = result.error if result is not None else ""
            retry_error = (
                retry_error or result_error or "Provider rejected delivery."
            )
            notification.last_error = retry_error
            if self.request.retries >= self.max_retries:
                notification.status = Notification.Status.FAILED
        notification.save(
            update_fields=(
                "attempts",
                "last_error",
                "provider_reference",
                "sent_at",
                "status",
                "updated_at",
            )
        )
        if result is not None and result.success:
            logger.info(
                "Notification successfully sent notification=%s attempt=%s "
                "provider_reference=%s",
                notification.pk,
                attempt_number,
                notification.provider_reference,
            )
        else:
            provider_reference = (
                result.provider_reference if result is not None else None
            )
            logger.warning(
                "Notification provider failure notification=%s attempt=%s "
                "provider_reference=%s",
                notification.pk,
                attempt_number,
                provider_reference,
            )
            if notification.status == Notification.Status.FAILED:
                logger.error(
                    "Notification terminal failure notification=%s attempt=%s "
                    "provider_reference=%s",
                    notification.pk,
                    attempt_number,
                    provider_reference,
                )
    if retry_error and self.request.retries < self.max_retries:
        countdown = min(2 ** self.request.retries, 30)
        logger.warning(
            "Notification retry scheduled notification=%s attempt=%s "
            "countdown=%s",
            notification.pk,
            attempt_number,
            countdown,
        )
        raise self.retry(
            exc=NotificationProviderError(retry_error),
            countdown=countdown,
        )
    return notification.status