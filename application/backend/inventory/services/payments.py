from django.db import models, transaction
from rest_framework.exceptions import ValidationError
from inventory.models import Notification, Order, Payment
from inventory.services.notifications import create_notification
from inventory.services.order_status import transition_order_status
from inventory.services.payment_providers import mock_payment_provider

def calculate_order_total(order):
    total = order.items.aggregate(
        total=models.Sum(
            models.F("quantity") * models.F("unit_price"),
            output_field=models.DecimalField(
                max_digits=24,
                decimal_places=2,
            ),
        )
    )["total"]
    if total is None:
        raise ValidationError(
            {"order": "An order without items cannot be paid."}
        )
    return total

@transaction.atomic
def process_payment(order):
    locked_order = Order.objects.select_for_update().get(pk=order.pk)
    if locked_order.status in {
        Order.Status.CANCELLED,
        Order.Status.DELIVERED,
    }:
        raise ValidationError(
            {
                "order": (
                    f"An order with status '{locked_order.status}' "
                    "cannot be paid."
                )
            }
        )
    payment = (
        Payment.objects.select_for_update()
        .filter(order=locked_order)
        .first()
    )
    if payment and payment.status == Payment.Status.SUCCEEDED:
        return payment, False
    amount = calculate_order_total(locked_order)
    created = payment is None
    if payment is None:
        payment = Payment(order=locked_order)
    payment.amount = amount
    payment.status = Payment.Status.PENDING
    payment.provider = mock_payment_provider.name
    payment.provider_reference = None

    # This call is local and deterministic. A future network provider should use
    # its own idempotency key and must not be called inside a long transaction.
    result = mock_payment_provider.charge(
        order_id=locked_order.pk,
        amount=amount,
    )
    payment.status = (
        Payment.Status.SUCCEEDED
        if result.success
        else Payment.Status.FAILED
    )
    payment.provider_reference = result.provider_reference
    payment.save()
    if result.success and locked_order.status == Order.Status.PENDING:
        transition_order_status(
            locked_order,
            Order.Status.PROCESSING,
        )
    if result.success:
        create_notification(
            user=locked_order.user,
            order=locked_order,
            event_type=Notification.EventType.PAYMENT_SUCCEEDED,
        )
    return payment, created