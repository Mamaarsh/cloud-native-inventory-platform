from rest_framework import viewsets
from .models import Inventory, Order, Product, Warehouse
from .serializers import (
    InventorySerializer,
    OrderSerializer,
    ProductSerializer,
    WarehouseSerializer,
)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by("-created_at")
    serializer_class = WarehouseSerializer

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all().select_related(
        "product",
        "warehouse",
    )
    serializer_class = InventorySerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related(
        "user",
    ).prefetch_related(
        "items",
        "items__product",
    )
    serializer_class = OrderSerializer