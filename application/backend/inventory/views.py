from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
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
    OrderCreateSerializer,
    OrderSerializer,
    ProductSerializer,
    WarehouseSerializer,
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

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
    filter_backends = (
        DjangoFilterBackend, 
        SearchFilter, 
        OrderingFilter,
    )
    filterset_fields = (
        'sku',
    )
    search_fields = (
        'name',
        'sku',
    )
    ordering_fields = (
        'name',
        'price',
        'created_at',
    )

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by("-created_at")
    serializer_class = WarehouseSerializer
    permission_classes = (WarehousePermission,)
    filter_backends = (
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    )
    filterset_fields = (
        "location",
    )
    search_fields = (
        "name",
        "location",
    )
    ordering_fields = (
        "name",
        "created_at",
    )

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all().select_related(
        "product",
        "warehouse",
    )
    serializer_class = InventorySerializer
    permission_classes = (InventoryPermission,)
    filter_backends = (
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    )
    filterset_fields = (
        "product",
        "warehouse",
    )
    search_fields = (
        "product__name",
        "product__sku",
        "warehouse__name",
    )
    ordering_fields = (
        "quantity",
        "updated_at",
    )

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related(
        "user",
    ).prefetch_related(
        "items",
        "items__product",
    )
    serializer_class = OrderSerializer
    permission_classes = (OrderPermission,)
    filter_backends = (
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    )
    filterset_fields = (
        "status",
        "user",
    )
    search_fields = (
        "user__username",
        "user__email",
        "items__product__name",
        "items__product__sku",
    )
    ordering_fields = (
        "created_at",
        "updated_at",
        "status",
    )

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    @extend_schema(
        request=OrderCreateSerializer,
        responses={status.HTTP_201_CREATED: OrderSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        response_serializer = OrderSerializer(
            order,
            context=self.get_serializer_context(),
        )
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )