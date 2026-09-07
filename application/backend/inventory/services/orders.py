from django.db import transaction
from inventory.models import Order, OrderItem, OrderStatusHistory
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
    return order