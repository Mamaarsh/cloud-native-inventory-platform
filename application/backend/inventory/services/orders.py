from django.db import transaction
from inventory.models import AuditLog, Order, OrderItem, OrderStatusHistory
from inventory.services.audit import record_audit_event
from inventory.services.stock import deduct_stock

@transaction.atomic
def create_order(*, user, items):
    order = Order.objects.create(user=user)
    OrderStatusHistory.objects.create(
        order=order,
        from_status=None,
        to_status=order.status,
        performed_by=user,
    )
    deduct_stock(items, order=order, performed_by=user)
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                product=item["product"],
                warehouse=item["warehouse"],
                quantity=item["quantity"],
                unit_price=item["product"].price,
            )
            for item in items
        ]
    )
    record_audit_event(
        actor=user,
        action=AuditLog.Action.ORDER_CREATED,
        target_type=AuditLog.TargetType.ORDER,
        target_id=order.pk,
        target_label=f"Order #{order.pk}",
        metadata={"item_count": len(items)},
    )
    return order