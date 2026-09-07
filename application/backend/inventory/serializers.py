from functools import partial
from django.db import transaction
from rest_framework import serializers
from .models import (
    AuditLog,
    Inventory,
    InventoryMovement,
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    Product,
    Warehouse,
)
from .services import adjust_inventory, create_order
from .services.stock import MAX_INVENTORY_QUANTITY
from .validators import validate_product_image

class ProductSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(
        required=False,
        allow_null=False,
        validators=(validate_product_image,),
    )
    remove_image = serializers.BooleanField(
        required=False,
        default=False,
        write_only=True,
    )

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "sku",
            "price",
            "is_active",
            "image",
            "remove_image",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        if attrs.get("remove_image") and "image" in attrs:
            raise serializers.ValidationError(
                {
                    "remove_image": (
                        "Image upload and removal cannot be requested together."
                    )
                }
            )
        if self.instance is None and attrs.get("remove_image"):
            raise serializers.ValidationError(
                {"remove_image": "There is no existing image to remove."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("remove_image", False)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        remove_image = validated_data.pop("remove_image", False)
        replacing_image = "image" in validated_data
        old_image_name = instance.image.name if instance.image else None
        old_image_storage = instance.image.storage if instance.image else None

        if remove_image:
            validated_data["image"] = None

        product = super().update(instance, validated_data)
        new_image_name = product.image.name if product.image else None

        if (
            old_image_name
            and old_image_storage
            and (remove_image or replacing_image)
            and old_image_name != new_image_name
        ):
            transaction.on_commit(
                partial(old_image_storage.delete, old_image_name)
            )

        return product

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_at",
        )

class InventorySerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(
        min_value=0,
        max_value=MAX_INVENTORY_QUANTITY,
    )

    class Meta:
        model = Inventory
        fields = "__all__"
        read_only_fields = (
            "id",
            "updated_at",
        )

    def validate(self, attrs):
        if self.instance is not None:
            protected_fields = {
                field: (
                    "Inventory identity and quantity cannot be changed here. "
                    "Use the adjust endpoint for stock changes."
                )
                for field in ("product", "warehouse", "quantity")
                if field in self.initial_data
            }
            if protected_fields:
                raise serializers.ValidationError(protected_fields)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        initial_quantity = validated_data.pop("quantity", 0)
        inventory = Inventory.objects.create(
            quantity=0,
            **validated_data,
        )
        if initial_quantity > 0:
            inventory, _ = adjust_inventory(
                inventory=inventory,
                quantity_delta=initial_quantity,
                movement_type=InventoryMovement.Type.INITIAL_STOCK,
                performed_by=self.context["request"].user,
                reason="Initial quantity recorded when inventory was created.",
            )
        return inventory

class AuditActorSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)

class AuditLogSerializer(serializers.ModelSerializer):
    actor = AuditActorSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor",
            "action",
            "target_type",
            "target_id",
            "target_label",
            "metadata",
            "created_at",
        )
        read_only_fields = fields

class InventoryMovementSerializer(serializers.ModelSerializer):
    performed_by = AuditActorSerializer(read_only=True)
    order_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = InventoryMovement
        fields = (
            "id",
            "inventory",
            "movement_type",
            "quantity_delta",
            "quantity_before",
            "quantity_after",
            "reason",
            "order_id",
            "performed_by",
            "created_at",
        )
        read_only_fields = fields

class InventoryAdjustmentSerializer(serializers.Serializer):
    quantity_delta = serializers.IntegerField(
        min_value=-MAX_INVENTORY_QUANTITY,
        max_value=MAX_INVENTORY_QUANTITY,
    )
    reason = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )

    def validate_quantity_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("Quantity delta cannot be zero.")
        return value

    def validate(self, attrs):
        server_fields = {
            field: "This field is calculated by the server."
            for field in (
                "quantity_before",
                "quantity_after",
                "movement_type",
                "order",
                "order_id",
                "performed_by",
            )
            if field in self.initial_data
        }
        if server_fields:
            raise serializers.ValidationError(server_fields)
        return attrs

class OrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "sku",
            "image",
        )

class OrderWarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = (
            "id",
            "name",
            "location",
        )

class OrderUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)

class OrderItemSerializer(serializers.ModelSerializer):
    product = OrderProductSerializer(read_only=True)
    warehouse = OrderWarehouseSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product",
            "warehouse",
            "quantity",
            "unit_price",
        )
        read_only_fields = fields

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "order",
            "amount",
            "status",
            "provider",
            "provider_reference",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

class OrderSerializer(serializers.ModelSerializer):
    user = OrderUserSerializer(read_only=True)
    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "status",
            "created_at",
            "updated_at",
            "items",
        )
        read_only_fields = (
            "id",
            "user",
            "status",
            "created_at",
            "updated_at",
            "items",
        )

    def validate(self, attrs):
        if self.instance is not None and "status" in self.initial_data:
            raise serializers.ValidationError(
                {"status": "Use the change-status endpoint to update status."}
            )
        return attrs

class OrderDetailSerializer(OrderSerializer):
    payment = PaymentSerializer(read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ("payment",)
        read_only_fields = fields

class OrderItemCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )
    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all()
    )
    quantity = serializers.IntegerField(min_value=1)

    def validate_product(self, product):
        if not product.is_active:
            raise serializers.ValidationError("Inactive products cannot be ordered.")
        return product

class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemCreateSerializer(many=True, allow_empty=False)

    def create(self, validated_data):
        return create_order(
            user=self.context["request"].user,
            items=validated_data["items"],
        )

class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    performed_by = AuditActorSerializer(read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = (
            "id",
            "from_status",
            "to_status",
            "performed_by",
            "created_at",
        )
        read_only_fields = fields

class PaymentRequestSerializer(serializers.Serializer):
    def validate(self, attrs):
        if self.initial_data:
            errors = {
                field: "This field is controlled by the server."
                for field in self.initial_data
            }
            raise serializers.ValidationError(errors)
        return attrs