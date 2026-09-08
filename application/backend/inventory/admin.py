from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from .models import (
    AuditLog,
    Inventory,
    InventoryMovement,
    Notification,
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    Product,
    Warehouse,
)
from .services.audit import record_audit_event

def _admin_changes(previous, current, fields):
    changes = {}
    for field in fields:
        before = getattr(previous, field)
        after = getattr(current, field)
        if before == after:
            continue
        if field == "price":
            before = str(before)
            after = str(after)
        changes[field] = {"before": before, "after": after}
    return changes

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    actions = None
    list_display = (
        "id",
        "name",
        "sku",
        "price",
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
        "sku",
    )
    list_filter = (
        "is_active",
    )

    def has_delete_permission(self, request, obj=None):
        if obj is not None and (
            obj.inventories.exists() or obj.order_items.exists()
        ):
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        previous = Product.objects.get(pk=obj.pk) if change else None
        old_image_name = previous.image.name if previous and previous.image else None
        super().save_model(request, obj, form, change)
        if not change:
            action = AuditLog.Action.PRODUCT_CREATED
            metadata = {}
        else:
            changes = _admin_changes(
                previous,
                obj,
                ("name", "sku", "price", "is_active"),
            )
            metadata = {"changes": changes}
            new_image_name = obj.image.name if obj.image else None
            if old_image_name != new_image_name:
                metadata["image_changed"] = True
            if not changes and "image_changed" not in metadata:
                return
            if "is_active" in changes:
                action = (
                    AuditLog.Action.PRODUCT_ACTIVATED
                    if obj.is_active
                    else AuditLog.Action.PRODUCT_DEACTIVATED
                )
            else:
                action = AuditLog.Action.PRODUCT_UPDATED
        record_audit_event(
            actor=request.user,
            action=action,
            target_type=AuditLog.TargetType.PRODUCT,
            target_id=obj.pk,
            target_label=f"{obj.name} · {obj.sku}",
            metadata=metadata,
        )

    def delete_model(self, request, obj):
        if obj.inventories.exists() or obj.order_items.exists():
            raise PermissionDenied
        target_id = obj.pk
        target_label = f"{obj.name} · {obj.sku}"
        super().delete_model(request, obj)
        record_audit_event(
            actor=request.user,
            action=AuditLog.Action.PRODUCT_DELETED,
            target_type=AuditLog.TargetType.PRODUCT,
            target_id=target_id,
            target_label=target_label,
        )

    def delete_queryset(self, request, queryset):
        if any(
            product.inventories.exists() or product.order_items.exists()
            for product in queryset
        ):
            raise PermissionDenied
        targets = [
            (product.pk, f"{product.name} · {product.sku}")
            for product in queryset
        ]
        super().delete_queryset(request, queryset)
        for target_id, target_label in targets:
            record_audit_event(
                actor=request.user,
                action=AuditLog.Action.PRODUCT_DELETED,
                target_type=AuditLog.TargetType.PRODUCT,
                target_id=target_id,
                target_label=target_label,
            )

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    actions = None
    list_display = (
        "id",
        "name",
        "location",
        "created_at",
    )
    search_fields = (
        "name",
        "location",
    )

    def has_delete_permission(self, request, obj=None):
        if obj is not None and (
            obj.inventories.exists() or obj.order_items.exists()
        ):
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        previous = Warehouse.objects.get(pk=obj.pk) if change else None
        super().save_model(request, obj, form, change)
        action = (
            AuditLog.Action.WAREHOUSE_UPDATED
            if change
            else AuditLog.Action.WAREHOUSE_CREATED
        )
        metadata = (
            {
                "changes": _admin_changes(
                    previous,
                    obj,
                    ("name", "location"),
                )
            }
            if change
            else {}
        )
        if change and not metadata["changes"]:
            return
        record_audit_event(
            actor=request.user,
            action=action,
            target_type=AuditLog.TargetType.WAREHOUSE,
            target_id=obj.pk,
            target_label=obj.name,
            metadata=metadata,
        )

    def delete_model(self, request, obj):
        if obj.inventories.exists() or obj.order_items.exists():
            raise PermissionDenied
        target_id = obj.pk
        target_label = obj.name
        super().delete_model(request, obj)
        record_audit_event(
            actor=request.user,
            action=AuditLog.Action.WAREHOUSE_DELETED,
            target_type=AuditLog.TargetType.WAREHOUSE,
            target_id=target_id,
            target_label=target_label,
        )

    def delete_queryset(self, request, queryset):
        if any(
            warehouse.inventories.exists() or warehouse.order_items.exists()
            for warehouse in queryset
        ):
            raise PermissionDenied
        targets = [
            (warehouse.pk, warehouse.name)
            for warehouse in queryset
        ]
        super().delete_queryset(request, queryset)
        for target_id, target_label in targets:
            record_audit_event(
                actor=request.user,
                action=AuditLog.Action.WAREHOUSE_DELETED,
                target_type=AuditLog.TargetType.WAREHOUSE,
                target_id=target_id,
                target_label=target_label,
            )

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "warehouse",
        "quantity",
        "updated_at",
    )
    list_filter = (
        "warehouse",
    )
    readonly_fields = (
        "quantity",
        "updated_at",
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly_fields.extend(("product", "warehouse"))
        return tuple(readonly_fields)

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            record_audit_event(
                actor=request.user,
                action=AuditLog.Action.INVENTORY_CREATED,
                target_type=AuditLog.TargetType.INVENTORY,
                target_id=obj.pk,
                target_label=f"{obj.product.name} · {obj.warehouse.name}",
            )

@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "inventory",
        "movement_type",
        "quantity_delta",
        "quantity_before",
        "quantity_after",
        "order",
        "performed_by",
        "created_at",
    )
    list_filter = (
        "movement_type",
        "created_at",
    )
    search_fields = (
        "inventory__product__name",
        "inventory__product__sku",
        "inventory__warehouse__name",
        "performed_by__username",
        "order__id",
        "reason",
    )
    list_select_related = (
        "inventory__product",
        "inventory__warehouse",
        "order",
        "performed_by",
    )
    readonly_fields = (
        "inventory",
        "movement_type",
        "quantity_delta",
        "quantity_before",
        "quantity_after",
        "reason",
        "order",
        "performed_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"} and super().has_change_permission(
            request,
            obj,
        )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
    )
    readonly_fields = (
        "status",
        "created_at",
        "updated_at",
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly_fields.append("user")
        return tuple(readonly_fields)

    def has_delete_permission(self, request, obj=None):
        return False

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            OrderStatusHistory.objects.create(
                order=obj,
                from_status=None,
                to_status=obj.status,
                performed_by=request.user,
            )
            record_audit_event(
                actor=request.user,
                action=AuditLog.Action.ORDER_CREATED,
                target_type=AuditLog.TargetType.ORDER,
                target_id=obj.pk,
                target_label=f"Order #{obj.pk}",
                metadata={"item_count": 0},
            )

@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "from_status",
        "to_status",
        "performed_by",
        "created_at",
    )
    list_filter = (
        "from_status",
        "to_status",
        "created_at",
    )
    search_fields = (
        "order__id",
        "order__user__username",
        "performed_by__username",
    )
    list_select_related = (
        "order",
        "order__user",
        "performed_by",
    )
    readonly_fields = (
        "order",
        "from_status",
        "to_status",
        "performed_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"} and super().has_change_permission(
            request,
            obj,
        )

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "actor",
        "action",
        "target_type",
        "target_id",
        "target_label",
        "created_at",
    )
    list_filter = (
        "action",
        "target_type",
        "created_at",
    )
    search_fields = (
        "actor__username",
        "target_label",
        "target_id",
    )
    list_select_related = ("actor",)
    readonly_fields = (
        "actor",
        "action",
        "target_type",
        "target_id",
        "target_label",
        "metadata",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"} and super().has_change_permission(
            request,
            obj,
        )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product",
        "warehouse",
        "quantity",
        "unit_price",
    )
    readonly_fields = (
        "order",
        "product",
        "warehouse",
        "quantity",
        "unit_price",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"} and super().has_change_permission(
            request,
            obj,
        )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "amount",
        "status",
        "provider",
        "provider_reference",
        "created_at",
    )
    list_filter = (
        "status",
        "provider",
    )
    search_fields = (
        "provider_reference",
        "order__id",
        "order__user__username",
    )
    readonly_fields = (
        "order",
        "amount",
        "status",
        "provider",
        "provider_reference",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"} and super().has_change_permission(
            request,
            obj,
        )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "order",
        "event_type",
        "channel",
        "status",
        "attempts",
        "created_at",
        "sent_at",
    )
    list_filter = (
        "status",
        "event_type",
        "channel",
    )
    search_fields = (
        "user__username",
        "order__id",
        "provider_reference",
        "idempotency_key",
    )
    readonly_fields = (
        "user",
        "order",
        "event_type",
        "channel",
        "status",
        "message",
        "provider_reference",
        "idempotency_key",
        "attempts",
        "last_error",
        "created_at",
        "updated_at",
        "sent_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"} and super().has_change_permission(
            request,
            obj,
        )