from django.db import transaction
from rest_framework.exceptions import ValidationError
from inventory.models import Order

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
    return locked_order