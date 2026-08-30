from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    InventoryViewSet,
    OrderViewSet,
    ProductViewSet,
    WarehouseViewSet,
)

router = DefaultRouter()

router.register(
    "products",
    ProductViewSet,
    basename="product",
)
router.register(
    "warehouses",
    WarehouseViewSet,
    basename="warehouse",
)
router.register(
    "inventory",
    InventoryViewSet,
    basename="inventory",
)
router.register(
    "orders",
    OrderViewSet,
    basename="order",
)

urlpatterns = [
    path("", include(router.urls)),
]