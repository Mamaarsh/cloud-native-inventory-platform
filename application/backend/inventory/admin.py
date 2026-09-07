from django.contrib import admin
from django.db import transaction
from .models import (
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

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
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

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
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
    )

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