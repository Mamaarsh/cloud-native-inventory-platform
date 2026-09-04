import logging
from django.conf import settings
from django.db import DatabaseError, connection
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from redis import Redis
from redis.exceptions import RedisError
from users.permissions import (
    InventoryPermission,
    OrderPermission,
    OrderStatusPermission,
    ProductPermission,
    WarehousePermission,
)
from .models import Inventory, Order, OrderItem, Product, Warehouse
from .serializers import (
    InventorySerializer,
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
    PaymentRequestSerializer,
    PaymentSerializer,
    ProductSerializer,
    WarehouseSerializer,
)
from .services import process_payment, transition_order_status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

logger = logging.getLogger(__name__)

@api_view(["GET"])
def health_live(request):
    return Response({"status": "ok"})

def _check_database():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return "ok"
    except DatabaseError as exc:
        logger.warning(
            "Health check failed dependency=database error=%s",
            exc.__class__.__name__,
        )
    return "unavailable"

def _check_redis():
    redis_client = None
    try:
        redis_client = Redis.from_url(
            settings.CELERY_BROKER_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        redis_client.ping()
        return "ok"
    except (RedisError, ValueError) as exc:
        logger.warning(
            "Health check failed dependency=redis error=%s",
            exc.__class__.__name__,
        )
    finally:
        if redis_client is not None:
            try:
                redis_client.close()
            except RedisError as exc:
                logger.warning(
                    "Health check failed dependency=redis operation=close "
                    "error=%s",
                    exc.__class__.__name__,
                )
    return "unavailable"

@api_view(["GET"])
def health_ready(request):
    database_status = _check_database()
    checks = {"database": database_status}
    if database_status != "ok":
        logger.warning(
            "Readiness check failed database=%s",
            database_status,
        )
        return Response(
            {"status": "not_ready", "checks": checks},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    logger.debug("Readiness check succeeded database=ok")
    return Response(
        {
            "status": "ready",
            "checks": checks,
        }
    )

@api_view(["GET"])
def health_dependencies(request):
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
    }
    if checks["database"] != "ok":
        dependency_status = "unhealthy"
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif checks["redis"] != "ok":
        dependency_status = "degraded"
        response_status = status.HTTP_200_OK
    else:
        dependency_status = "healthy"
        response_status = status.HTTP_200_OK
    if dependency_status == "healthy":
        logger.debug("Dependency check succeeded database=ok redis=ok")
    else:
        logger.warning(
            "Dependency check status=%s database=%s redis=%s",
            dependency_status,
            checks["database"],
            checks["redis"],
        )
    return Response(
        {"status": dependency_status, "checks": checks},
        status=response_status,
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
        Prefetch(
            "items",
            queryset=OrderItem.objects.select_related(
                "product",
                "warehouse",
            ),
        )
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
        order = self.get_queryset().get(pk=order.pk)
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

    @extend_schema(
        request=OrderStatusUpdateSerializer,
        responses={status.HTTP_200_OK: OrderSerializer},
    )
    @action(
        detail=True,
        methods=("post",),
        url_path="change-status",
        permission_classes=(OrderStatusPermission,),
    )
    def change_status(self, request, *args, **kwargs):
        input_serializer = OrderStatusUpdateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        order = self.get_object()
        order = transition_order_status(
            order,
            input_serializer.validated_data["status"],
        )
        order = self.get_queryset().get(pk=order.pk)
        response_serializer = OrderSerializer(
            order,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data)

    @extend_schema(
        description=(
            "Process this order with the mock payment provider. Send an "
            "empty JSON object; amount and all payment fields are controlled "
            "by the server."
        ),
        request=PaymentRequestSerializer,
        responses={
            status.HTTP_200_OK: PaymentSerializer,
            status.HTTP_201_CREATED: PaymentSerializer,
        },
    )
    @action(detail=True, methods=("post",), url_path="pay")
    def pay(self, request, *args, **kwargs):
        input_serializer = PaymentRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        order = self.get_object()
        payment, created = process_payment(order)
        response_serializer = PaymentSerializer(payment)
        response_status = (
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        return Response(response_serializer.data, status=response_status)