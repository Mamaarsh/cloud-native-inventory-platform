from rest_framework import serializers
from .models import Inventory, Order, OrderItem, Payment, Product, Warehouse
from .services import create_order

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

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