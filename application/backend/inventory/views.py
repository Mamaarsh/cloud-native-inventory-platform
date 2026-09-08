import logging
from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.db.models import Prefetch
from django.db.models.deletion import ProtectedError
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from redis import Redis
from redis.exceptions import RedisError
from config.api_schema import (
    DependencyHealthResponseSerializer,
    DetailResponseSerializer,
    EMPTY_OBJECT_SCHEMA,
    LivenessResponseSerializer,
    ReadinessResponseSerializer,
    VALIDATION_ERROR_SCHEMA,
)
from users.permissions import (
    InventoryAdjustmentPermission,
    InventoryPermission,
    IsAuditViewer,
    OrderPermission,
    OrderStatusPermission,
    ProductPermission,
    WarehousePermission,
)
from .models import AuditLog, Inventory, Order, OrderItem, Product, Warehouse
from .serializers import (
    AuditLogSerializer,
    InventoryAdjustmentSerializer,
    InventoryMovementSerializer,
    InventorySerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderSerializer,
    OrderStatusHistorySerializer,
    OrderStatusUpdateSerializer,
    PaymentRequestSerializer,
    PaymentSerializer,
    ProductSerializer,
    WarehouseSerializer,
)
from .services import (
    adjust_inventory,
    process_payment,
    record_audit_event,
    transition_order_status,
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

logger = logging.getLogger(__name__)

class ProductDeletionConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "This product cannot be deleted because it is referenced by inventory "
        "or order history. Deactivate it instead."
    )
    default_code = "product_in_use"

class WarehouseDeletionConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "This warehouse cannot be deleted because it is referenced by "
        "inventory or order history."
    )
    default_code = "warehouse_in_use"

def _product_label(product):
    return f"{product.name} · {product.sku}"

def _warehouse_label(warehouse):
    return warehouse.name

def _inventory_label(inventory):
    return f"{inventory.product.name} · {inventory.warehouse.name}"

def _changed_values(before, instance, fields):
    changes = {}
    for field in fields:
        old_value = before[field]
        new_value = getattr(instance, field)
        if old_value != new_value:
            changes[field] = {
                "before": str(old_value) if field == "price" else old_value,
                "after": str(new_value) if field == "price" else new_value,
            }
    return changes

@extend_schema(
    operation_id="health_liveness",
    tags=("Health",),
    description=(
        "Confirms that the Django application process can respond. "
        "No dependency is checked."
    ),
    responses={status.HTTP_200_OK: LivenessResponseSerializer},
)
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

@extend_schema(
    operation_id="health_readiness",
    tags=("Health",),
    description=(
        "Checks the critical PostgreSQL dependency. Redis does not affect "
        "application readiness."
    ),
    responses={
        status.HTTP_200_OK: ReadinessResponseSerializer,
        status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
            response=ReadinessResponseSerializer,
            description="PostgreSQL is unavailable.",
        ),
    },
)
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

@extend_schema(
    operation_id="health_dependencies",
    tags=("Health",),
    description=(
        "Reports PostgreSQL and Redis health for monitoring. Redis failure "
        "is degraded; PostgreSQL failure is unhealthy."
    ),
    responses={
        status.HTTP_200_OK: DependencyHealthResponseSerializer,
        status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
            response=DependencyHealthResponseSerializer,
            description="PostgreSQL is unavailable.",
        ),
    },
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

@extend_schema_view(
    destroy=extend_schema(
        responses={
            status.HTTP_204_NO_CONTENT: None,
            status.HTTP_401_UNAUTHORIZED: DetailResponseSerializer,
            status.HTTP_403_FORBIDDEN: DetailResponseSerializer,
            status.HTTP_404_NOT_FOUND: DetailResponseSerializer,
            status.HTTP_409_CONFLICT: OpenApiResponse(
                response=DetailResponseSerializer,
                description=(
                    "The product is referenced by inventory or order history."
                ),
            ),
        }
    )
)
@extend_schema(tags=("Products",))
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

    @transaction.atomic
    def perform_create(self, serializer):
        product = serializer.save()
        record_audit_event(
            actor=self.request.user,
            action=AuditLog.Action.PRODUCT_CREATED,
            target_type=AuditLog.TargetType.PRODUCT,
            target_id=product.pk,
            target_label=_product_label(product),
        )

    @transaction.atomic
    def perform_update(self, serializer):
        product = serializer.instance
        before = {
            field: getattr(product, field)
            for field in ("name", "sku", "price", "is_active")
        }
        old_image_name = product.image.name if product.image else None
        updated_product = serializer.save()
        changes = _changed_values(
            before,
            updated_product,
            ("name", "sku", "price", "is_active"),
        )
        new_image_name = (
            updated_product.image.name if updated_product.image else None
        )
        metadata = {"changes": changes}
        if old_image_name != new_image_name:
            metadata["image_changed"] = True
        if not changes and "image_changed" not in metadata:
            return
        if "is_active" in changes:
            action = (
                AuditLog.Action.PRODUCT_ACTIVATED
                if updated_product.is_active
                else AuditLog.Action.PRODUCT_DEACTIVATED
            )
        else:
            action = AuditLog.Action.PRODUCT_UPDATED
        record_audit_event(
            actor=self.request.user,
            action=action,
            target_type=AuditLog.TargetType.PRODUCT,
            target_id=updated_product.pk,
            target_label=_product_label(updated_product),
            metadata=metadata,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        if instance.inventories.exists() or instance.order_items.exists():
            raise ProductDeletionConflict()
        target_id = instance.pk
        target_label = _product_label(instance)
        try:
            instance.delete()
        except ProtectedError as exc:
            raise ProductDeletionConflict() from exc
        record_audit_event(
            actor=self.request.user,
            action=AuditLog.Action.PRODUCT_DELETED,
            target_type=AuditLog.TargetType.PRODUCT,
            target_id=target_id,
            target_label=target_label,
        )

@extend_schema_view(
    destroy=extend_schema(
        responses={
            status.HTTP_204_NO_CONTENT: None,
            status.HTTP_401_UNAUTHORIZED: DetailResponseSerializer,
            status.HTTP_403_FORBIDDEN: DetailResponseSerializer,
            status.HTTP_404_NOT_FOUND: DetailResponseSerializer,
            status.HTTP_409_CONFLICT: OpenApiResponse(
                response=DetailResponseSerializer,
                description=(
                    "The warehouse is referenced by inventory or order history."
                ),
            ),
        }
    )
)
@extend_schema(tags=("Warehouses",))
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

    @transaction.atomic
    def perform_create(self, serializer):
        warehouse = serializer.save()
        record_audit_event(
            actor=self.request.user,
            action=AuditLog.Action.WAREHOUSE_CREATED,
            target_type=AuditLog.TargetType.WAREHOUSE,
            target_id=warehouse.pk,
            target_label=_warehouse_label(warehouse),
        )

    @transaction.atomic
    def perform_update(self, serializer):
        warehouse = serializer.instance
        before = {
            field: getattr(warehouse, field)
            for field in ("name", "location")
        }
        updated_warehouse = serializer.save()
        changes = _changed_values(
            before,
            updated_warehouse,
            ("name", "location"),
        )
        if not changes:
            return
        record_audit_event(
            actor=self.request.user,
            action=AuditLog.Action.WAREHOUSE_UPDATED,
            target_type=AuditLog.TargetType.WAREHOUSE,
            target_id=updated_warehouse.pk,
            target_label=_warehouse_label(updated_warehouse),
            metadata={"changes": changes},
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        if instance.inventories.exists() or instance.order_items.exists():
            raise WarehouseDeletionConflict()
        target_id = instance.pk
        target_label = _warehouse_label(instance)
        try:
            instance.delete()
        except ProtectedError as exc:
            raise WarehouseDeletionConflict() from exc
        record_audit_event(
            actor=self.request.user,
            action=AuditLog.Action.WAREHOUSE_DELETED,
            target_type=AuditLog.TargetType.WAREHOUSE,
            target_id=target_id,
            target_label=target_label,
        )

@extend_schema(tags=("Inventory",))
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

    @transaction.atomic
    def perform_create(self, serializer):
        inventory = serializer.save()
        record_audit_event(
            actor=self.request.user,
            action=AuditLog.Action.INVENTORY_CREATED,
            target_type=AuditLog.TargetType.INVENTORY,
            target_id=inventory.pk,
            target_label=_inventory_label(inventory),
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        if instance.movements.exists():
            raise ValidationError(
                {
                    "inventory": (
                        "Inventory with movement history cannot be deleted."
                    )
                }
            )
        target_id = instance.pk
        target_label = _inventory_label(instance)
        super().perform_destroy(instance)
        record_audit_event(
            actor=self.request.user,
            action=AuditLog.Action.INVENTORY_DELETED,
            target_type=AuditLog.TargetType.INVENTORY,
            target_id=target_id,
            target_label=target_label,
        )

    @extend_schema(
        tags=("Inventory",),
        description=(
            "Atomically adjusts stock and creates an immutable inventory "
            "movement. The resulting quantity cannot be negative."
        ),
        request=InventoryAdjustmentSerializer,
        responses={
            status.HTTP_201_CREATED: InventoryMovementSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=VALIDATION_ERROR_SCHEMA,
                description="The adjustment failed validation.",
            ),
            status.HTTP_401_UNAUTHORIZED: DetailResponseSerializer,
            status.HTTP_403_FORBIDDEN: DetailResponseSerializer,
            status.HTTP_404_NOT_FOUND: DetailResponseSerializer,
        },
    )
    @action(
        detail=True,
        methods=("post",),
        url_path="adjust",
        permission_classes=(InventoryAdjustmentPermission,),
    )
    def adjust(self, request, *args, **kwargs):
        input_serializer = InventoryAdjustmentSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        inventory = self.get_object()
        _, movement = adjust_inventory(
            inventory=inventory,
            quantity_delta=input_serializer.validated_data["quantity_delta"],
            performed_by=request.user,
            reason=input_serializer.validated_data["reason"],
        )
        return Response(
            InventoryMovementSerializer(movement).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=("Inventory",),
        filters=False,
        description=(
            "Returns the paginated immutable movement history for this "
            "inventory record, newest first."
        ),
        responses={status.HTTP_200_OK: InventoryMovementSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=("get",),
        url_path="movements",
    )
    def movements(self, request, *args, **kwargs):
        inventory = self.get_object()
        queryset = inventory.movements.select_related(
            "performed_by",
            "order",
        ).order_by("-created_at", "-pk")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = InventoryMovementSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(InventoryMovementSerializer(queryset, many=True).data)

@extend_schema(
    tags=("Audit",),
    description=(
        "Read-only immutable activity. Access is limited to application "
        "Admins and Auditors."
    ),
)
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer
    permission_classes = (IsAuditViewer,)
    filter_backends = (
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    )
    filterset_fields = (
        "action",
        "target_type",
        "actor",
    )
    search_fields = (
        "target_label",
        "target_id",
        "actor__username",
    )
    ordering_fields = ("created_at",)
    ordering = ("-created_at", "-id")

@extend_schema(tags=("Orders",))
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
    ).order_by("-created_at", "-id")
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

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            return queryset.select_related("payment")
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        if self.action == "retrieve":
            return OrderDetailSerializer
        return OrderSerializer

    def perform_destroy(self, instance):
        if (
            instance.status_history.exists()
            or instance.inventory_movements.exists()
        ):
            raise ValidationError(
                {"order": "Orders with audit history cannot be deleted."}
            )
        super().perform_destroy(instance)

    @extend_schema(
        tags=("Orders",),
        description="Creates an order and deducts stock atomically.",
        request=OrderCreateSerializer,
        responses={
            status.HTTP_201_CREATED: OrderSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=VALIDATION_ERROR_SCHEMA,
                description="The order failed validation or stock checks.",
            ),
            status.HTTP_401_UNAUTHORIZED: DetailResponseSerializer,
            status.HTTP_403_FORBIDDEN: DetailResponseSerializer,
        },
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
        tags=("Orders",),
        description=(
            "Applies a permitted order state transition. Direct status "
            "updates through PATCH are not supported."
        ),
        request=OrderStatusUpdateSerializer,
        responses={
            status.HTTP_200_OK: OrderSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=VALIDATION_ERROR_SCHEMA,
                description="The requested status transition is invalid.",
            ),
            status.HTTP_401_UNAUTHORIZED: DetailResponseSerializer,
            status.HTTP_403_FORBIDDEN: DetailResponseSerializer,
            status.HTTP_404_NOT_FOUND: DetailResponseSerializer,
        },
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
            performed_by=request.user,
        )
        order = self.get_queryset().get(pk=order.pk)
        response_serializer = OrderSerializer(
            order,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data)

    @extend_schema(
        tags=("Orders",),
        filters=False,
        description=(
            "Returns the complete chronological status history. The bounded "
            "state machine keeps this response intentionally unpaginated."
        ),
        responses={
            status.HTTP_200_OK: OrderStatusHistorySerializer(many=True),
        },
    )
    @action(
        detail=True,
        methods=("get",),
        url_path="history",
        pagination_class=None,
    )
    def history(self, request, *args, **kwargs):
        order = self.get_object()
        history = order.status_history.select_related(
            "performed_by",
        ).order_by("created_at", "pk")
        return Response(OrderStatusHistorySerializer(history, many=True).data)

    @extend_schema(
        tags=("Payments",),
        description=(
            "Process this order with the mock payment provider. Send an "
            "empty JSON object; amount and all payment fields are controlled "
            "by the server."
        ),
        request={"application/json": EMPTY_OBJECT_SCHEMA},
        responses={
            status.HTTP_200_OK: PaymentSerializer,
            status.HTTP_201_CREATED: PaymentSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=VALIDATION_ERROR_SCHEMA,
                description="The order cannot be paid in its current state.",
            ),
            status.HTTP_401_UNAUTHORIZED: DetailResponseSerializer,
            status.HTTP_403_FORBIDDEN: DetailResponseSerializer,
            status.HTTP_404_NOT_FOUND: DetailResponseSerializer,
        },
    )
    @action(detail=True, methods=("post",), url_path="pay")
    def pay(self, request, *args, **kwargs):
        input_serializer = PaymentRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        order = self.get_object()
        payment, created = process_payment(
            order,
            performed_by=request.user,
        )
        response_serializer = PaymentSerializer(payment)
        response_status = (
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        return Response(response_serializer.data, status=response_status)