from collections import defaultdict
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from inventory.models import AuditLog, Inventory, InventoryMovement
from inventory.services.audit import record_audit_event

MAX_INVENTORY_QUANTITY = 2_147_483_647

def _apply_locked_stock_change(
    *,
    inventory,
    quantity_delta,
    movement_type,
    performed_by=None,
    reason="",
    order=None,
):
    valid_movement_types = {
        value for value, _ in InventoryMovement.Type.choices
    }
    if movement_type not in valid_movement_types:
        raise ValidationError(
            {"movement_type": "Unsupported inventory movement type."}
        )
    if isinstance(quantity_delta, bool) or not isinstance(quantity_delta, int):
        raise ValidationError(
            {"quantity_delta": "Quantity delta must be a whole number."}
        )
    if quantity_delta == 0:
        raise ValidationError(
            {"quantity_delta": "Quantity delta cannot be zero."}
        )

    normalized_reason = reason.strip()
    if (
        movement_type == InventoryMovement.Type.MANUAL_ADJUSTMENT
        and not normalized_reason
    ):
        raise ValidationError(
            {"reason": "A reason is required for manual adjustments."}
        )
    if len(normalized_reason) > 255:
        raise ValidationError(
            {"reason": "Ensure this value has at most 255 characters."}
        )
    if (
        movement_type == InventoryMovement.Type.ORDER_DEDUCTION
        and order is None
    ):
        raise ValidationError(
            {"order": "Order deductions require an order reference."}
        )

    quantity_before = inventory.quantity
    quantity_after = quantity_before + quantity_delta
    if quantity_after < 0:
        raise ValidationError(
            {
                "quantity_delta": (
                    "This adjustment would make inventory negative."
                )
            }
        )
    if quantity_after > MAX_INVENTORY_QUANTITY:
        raise ValidationError(
            {"quantity_delta": "The resulting inventory quantity is too large."}
        )

    inventory.quantity = quantity_after
    inventory.updated_at = timezone.now()
    inventory.save(update_fields=("quantity", "updated_at"))
    movement = InventoryMovement.objects.create(
        inventory=inventory,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        reason=normalized_reason,
        order=order,
        performed_by=performed_by,
    )
    return inventory, movement

@transaction.atomic
def adjust_inventory(
    *,
    inventory,
    quantity_delta,
    movement_type=InventoryMovement.Type.MANUAL_ADJUSTMENT,
    performed_by=None,
    reason="",
    order=None,
):
    locked_inventory = Inventory.objects.select_for_update().get(
        pk=inventory.pk
    )
    updated_inventory, movement = _apply_locked_stock_change(
        inventory=locked_inventory,
        quantity_delta=quantity_delta,
        movement_type=movement_type,
        performed_by=performed_by,
        reason=reason,
        order=order,
    )
    if movement_type == InventoryMovement.Type.MANUAL_ADJUSTMENT:
        record_audit_event(
            actor=performed_by,
            action=AuditLog.Action.INVENTORY_ADJUSTED,
            target_type=AuditLog.TargetType.INVENTORY,
            target_id=updated_inventory.pk,
            target_label=(
                f"{updated_inventory.product.name} · "
                f"{updated_inventory.warehouse.name}"
            ),
            metadata={"movement_id": movement.pk},
        )
    return updated_inventory, movement

@transaction.atomic
def deduct_stock(order_items, *, order, performed_by):
    requested_quantities = defaultdict(int)
    item_references = {}
    for item in order_items:
        product = item["product"]
        warehouse = item["warehouse"]
        key = (product.pk, warehouse.pk)
        requested_quantities[key] += item["quantity"]
        item_references[key] = (product, warehouse)
    if not requested_quantities:
        raise ValidationError({"items": "At least one order item is required."})
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
    for key in sorted(requested_quantities):
        requested_quantity = requested_quantities[key]
        inventory = inventory_by_key[key]
        _apply_locked_stock_change(
            inventory=inventory,
            quantity_delta=-requested_quantity,
            movement_type=InventoryMovement.Type.ORDER_DEDUCTION,
            performed_by=performed_by,
            reason="Stock deducted when the order was created.",
            order=order,
        )