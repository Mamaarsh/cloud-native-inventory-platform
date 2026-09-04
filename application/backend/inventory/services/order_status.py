from django.db import transaction
from rest_framework.exceptions import ValidationError
from inventory.models import Notification, Order
from inventory.services.notifications import create_notification

ALLOWED_STATUS_TRANSITIONS = {
    Order.Status.PENDING: {
        Order.Status.PROCESSING,
        Order.Status.CANCELLED,
    },
    Order.Status.PROCESSING: {
        Order.Status.SHIPPED,
        Order.Status.CANCELLED,
    },
    Order.Status.SHIPPED: {Order.Status.DELIVERED},
    Order.Status.DELIVERED: set(),
    Order.Status.CANCELLED: set(),
}

@transaction.atomic
def transition_order_status(order, new_status):
    locked_order = Order.objects.select_for_update().get(pk=order.pk)
    allowed_statuses = ALLOWED_STATUS_TRANSITIONS[locked_order.status]
    if new_status not in allowed_statuses:
        raise ValidationError(
            {
                "status": (
                    f"Cannot transition order from '{locked_order.status}' "
                    f"to '{new_status}'."
                )
            }
        )
    locked_order.status = new_status
    locked_order.save(update_fields=("status", "updated_at"))
    notification_event = {
        Order.Status.SHIPPED: Notification.EventType.ORDER_SHIPPED,
        Order.Status.DELIVERED: Notification.EventType.ORDER_DELIVERED,
    }.get(new_status)
    if notification_event:
        create_notification(
            user=locked_order.user,
            order=locked_order,
            event_type=notification_event,
        )
    return locked_order