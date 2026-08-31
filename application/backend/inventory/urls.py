from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    InventoryViewSet,
    OrderViewSet,
    ProductViewSet,
    WarehouseViewSet,
    health_live,
    health_ready,
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
    path("health/live/", health_live, name="health-live"),
    path("health/ready/", health_ready, name="health-ready"),
    path("", include(router.urls)),
]