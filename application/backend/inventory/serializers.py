from functools import partial

from django.db import transaction
from rest_framework import serializers
from .models import Inventory, Order, OrderItem, Payment, Product, Warehouse
from .services import create_order
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
    class Meta:
        model = Inventory
        fields = "__all__"
        read_only_fields = (
            "id",
            "updated_at",
        )

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

class PaymentRequestSerializer(serializers.Serializer):
    def validate(self, attrs):
        if self.initial_data:
            errors = {
                field: "This field is controlled by the server."
                for field in self.initial_data
            }
            raise serializers.ValidationError(errors)
        return attrs
