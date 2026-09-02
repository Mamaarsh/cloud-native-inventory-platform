from django.db import DatabaseError, connection
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from users.permissions import (
    InventoryPermission,
    OrderPermission,
    ProductPermission,
    WarehousePermission,
)
from .models import Inventory, Order, Product, Warehouse
from .serializers import (
    InventorySerializer,
    OrderSerializer,
    ProductSerializer,
    WarehouseSerializer,
)

@api_view(["GET"])
def health_live(request):
    return Response({"status": "ok"})

@api_view(["GET"])
def health_ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return Response(
            {
                "status": "not_ready",
                "database": "unavailable",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(
        {
            "status": "ready",
            "database": "ok",
        }
    )

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer
    permission_classes = (ProductPermission,)

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by("-created_at")
    serializer_class = WarehouseSerializer
    permission_classes = (WarehousePermission,)

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all().select_related(
        "product",
        "warehouse",
    )
    serializer_class = InventorySerializer
    permission_classes = (InventoryPermission,)

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related(
        "user",
    ).prefetch_related(
        "items",
        "items__product",
    )
    serializer_class = OrderSerializer
    permission_classes = (OrderPermission,)