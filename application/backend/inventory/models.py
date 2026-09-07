from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from .validators import validate_product_image

class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(
        upload_to="products/%Y/%m/",
        validators=(validate_product_image,),
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"

class Warehouse(models.Model):
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Inventory(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventories",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="inventories",
    )
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                name="unique_product_per_warehouse",
            )
        ]

    def __str__(self):
        return f"{self.product} - {self.warehouse}: {self.quantity}"

class InventoryMovement(models.Model):
    class Type(models.TextChoices):
        INITIAL_STOCK = "initial_stock", "Initial stock"
        MANUAL_ADJUSTMENT = "manual_adjustment", "Manual adjustment"
        ORDER_DEDUCTION = "order_deduction", "Order deduction"

    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=30, choices=Type.choices)
    quantity_delta = models.IntegerField()
    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()
    reason = models.CharField(max_length=255, blank=True, default="")
    order = models.ForeignKey(
        "Order",
        on_delete=models.PROTECT,
        related_name="inventory_movements",
        null=True,
        blank=True,
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="inventory_movements",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = (
            models.Index(fields=("inventory", "-created_at")),
        )
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(quantity_delta=0),
                name="inventory_movement_delta_nonzero",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    quantity_after=(
                        models.F("quantity_before")
                        + models.F("quantity_delta")
                    )
                ),
                name="inventory_movement_balances",
            ),
        )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Inventory movements are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Inventory movements are immutable.")

    def __str__(self):
        return (
            f"Inventory #{self.inventory_id}: "
            f"{self.quantity_before} -> {self.quantity_after}"
        )

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.status}"

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="order_items",
        null=True,
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    def __str__(self):
        return f"{self.product} x {self.quantity}"

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name="payment",
    )
    amount = models.DecimalField(max_digits=24, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    provider = models.CharField(max_length=50, default="mock")
    provider_reference = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for order #{self.order_id} - {self.status}"

class Notification(models.Model):
    class EventType(models.TextChoices):
        PAYMENT_SUCCEEDED = "payment_succeeded", "Payment succeeded"
        ORDER_SHIPPED = "order_shipped", "Order shipped"
        ORDER_DELIVERED = "order_delivered", "Order delivered"

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    event_type = models.CharField(
        max_length=40,
        choices=EventType.choices,
    )
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        default=Channel.EMAIL,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    message = models.TextField()
    provider_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    idempotency_key = models.CharField(max_length=255, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Notification #{self.id} - {self.event_type} - {self.status}"

# Module-level aliases let drf-spectacular assign stable, distinct schema names
# while preserving the established Order.Status and Payment.Status APIs.
OrderStatus = Order.Status
PaymentStatus = Payment.Status