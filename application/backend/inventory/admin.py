from django.contrib import admin
from .models import Inventory, Order, OrderItem, Payment, Product, Warehouse

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