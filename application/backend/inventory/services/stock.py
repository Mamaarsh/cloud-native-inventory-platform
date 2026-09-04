from collections import defaultdict
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from inventory.models import Inventory

@transaction.atomic
def deduct_stock(order_items):
    requested_quantities = defaultdict(int)
    item_references = {}
    for item in order_items:
        product = item["product"]
        warehouse = item["warehouse"]
        key = (product.pk, warehouse.pk)
        requested_quantities[key] += item["quantity"]
        item_references[key] = (product, warehouse)
    inventory_filter = Q()
    for product_id, warehouse_id in sorted(requested_quantities):
        inventory_filter |= Q(
            product_id=product_id,
            warehouse_id=warehouse_id,
        )
    locked_inventory = Inventory.objects.select_for_update().filter(
        inventory_filter
    ).order_by("product_id", "warehouse_id")
    inventory_by_key = {
        (inventory.product_id, inventory.warehouse_id): inventory
        for inventory in locked_inventory
    }
    errors = []
    for key, requested_quantity in requested_quantities.items():
        product, warehouse = item_references[key]
        inventory = inventory_by_key.get(key)
        if inventory is None:
            errors.append(
                f"No inventory exists for product '{product}' "
                f"in warehouse '{warehouse}'."
            )
        elif requested_quantity > inventory.quantity:
            errors.append(
                f"Insufficient stock for product '{product}' "
                f"in warehouse '{warehouse}': requested "
                f"{requested_quantity}, available {inventory.quantity}."
            )
    if errors:
        raise ValidationError({"items": errors})
    updated_at = timezone.now()
    inventories_to_update = []
    for key, requested_quantity in requested_quantities.items():
        inventory = inventory_by_key[key]
        inventory.quantity -= requested_quantity
        inventory.updated_at = updated_at
        inventories_to_update.append(inventory)
    Inventory.objects.bulk_update(
        inventories_to_update,
        fields=("quantity", "updated_at"),
    )