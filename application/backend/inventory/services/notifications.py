import logging
from functools import partial
from django.db import transaction
from rest_framework.exceptions import ValidationError
from inventory.models import Notification

logger = logging.getLogger(__name__)

NOTIFICATION_MESSAGES = {
    Notification.EventType.PAYMENT_SUCCEEDED: (
        "Payment succeeded for order #{order_id}."
    ),
    Notification.EventType.ORDER_SHIPPED: "Order #{order_id} has been shipped.",
    Notification.EventType.ORDER_DELIVERED: (
        "Order #{order_id} has been delivered."
    ),
}

def build_notification_message(*, order_id, event_type):
    try:
        template = NOTIFICATION_MESSAGES[event_type]
    except KeyError as exc:
        raise ValidationError(
            {"event_type": f"Unsupported notification event '{event_type}'."}
        ) from exc
    return template.format(order_id=order_id)

def build_idempotency_key(*, order_id, event_type):
    return f"{event_type}:order:{order_id}"

def _schedule_notification_delivery(
    notification_id,
    order_id,
    event_type,
    idempotency_key,
):
    from inventory.tasks import send_notification

    logger.info(
        "Notification scheduled after commit for order=%s event_type=%s "
        "idempotency_key=%s",
        order_id,
        event_type,
        idempotency_key,
    )
    send_notification.delay(notification_id)

@transaction.atomic
def create_notification(*, user, order, event_type):
    idempotency_key = build_idempotency_key(
        order_id=order.pk,
        event_type=event_type,
    )
    notification, created = Notification.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "user": user,
            "order": order,
            "event_type": event_type,
            "channel": Notification.Channel.EMAIL,
            "message": build_notification_message(
                order_id=order.pk,
                event_type=event_type,
            ),
        },
    )
    if created:
        logger.info(
            "Notification created for order=%s event_type=%s "
            "idempotency_key=%s",
            order.pk,
            event_type,
            idempotency_key,
        )
        transaction.on_commit(
            partial(
                _schedule_notification_delivery,
                notification.pk,
                order.pk,
                event_type,
                idempotency_key,
            ),
            robust=True,
        )
    else:
        logger.info(
            "Existing notification returned for order=%s event_type=%s "
            "idempotency_key=%s",
            order.pk,
            event_type,
            idempotency_key,
        )
    return notification, created