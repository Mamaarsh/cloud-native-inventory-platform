from django.db import transaction
from inventory.models import Order, OrderItem
from inventory.services.stock import deduct_stock

@transaction.atomic
def create_order(*, user, items):
    deduct_stock(items)
    order = Order.objects.create(user=user)
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