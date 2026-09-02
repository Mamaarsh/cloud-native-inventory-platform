from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, OperationalError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Inventory, Order, OrderItem, Product, Warehouse

class OrderCreationAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name="Admin")
        cls.user = get_user_model().objects.create_user(
            username="order-admin",
            email="orders@example.com",
        )
        cls.user.groups.add(admin_group)
        cls.product = Product.objects.create(
            name="Active Product",
            sku="ORDER-001",
            price="100.00",
        )
        cls.second_product = Product.objects.create(
            name="Second Product",
            sku="ORDER-002",
            price="25.50",
        )
        cls.inactive_product = Product.objects.create(
            name="Inactive Product",
            sku="ORDER-003",
            price="15.00",
            is_active=False,
        )

    def setUp(self):
        self.client.force_authenticate(self.user)
        self.url = reverse("order-list")

    def order_payload(self):
        return {
            "items": [
                {"product": self.product.pk, "quantity": 2},
                {"product": self.second_product.pk, "quantity": 1},
            ]
        }

    def test_authenticated_user_can_create_order(self):
        response = self.client.post(
            self.url,
            self.order_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["status"], Order.Status.PENDING)
        self.assertEqual(len(response.json()["items"]), 2)

    def test_created_order_belongs_to_authenticated_user(self):
        response = self.client.post(
            self.url,
            self.order_payload(),
            format="json",
        )
        order = Order.objects.get(pk=response.json()["id"])
        self.assertEqual(order.user, self.user)
        self.assertEqual(response.json()["user"]["id"], self.user.pk)

    def test_nested_items_are_created(self):
        response = self.client.post(
            self.url,
            self.order_payload(),
            format="json",
        )
        order = Order.objects.get(pk=response.json()["id"])
        self.assertEqual(order.items.count(), 2)
        self.assertSetEqual(
            set(order.items.values_list("product_id", "quantity")),
            {
                (self.product.pk, 2),
                (self.second_product.pk, 1),
            },
        )

    def test_product_price_is_copied_to_order_item(self):
        response = self.client.post(
            self.url,
            {"items": [{"product": self.product.pk, "quantity": 1}]},
            format="json",
        )
        item = OrderItem.objects.get(order_id=response.json()["id"])
        self.assertEqual(item.unit_price, Decimal("100.00"))
        self.product.price = "200.00"
        self.product.save(update_fields=("price",))
        item.refresh_from_db()
        self.assertEqual(str(item.unit_price), "100.00")

    def test_inactive_product_is_rejected(self):
        response = self.client.post(
            self.url,
            {
                "items": [
                    {"product": self.inactive_product.pk, "quantity": 1}
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_zero_quantity_is_rejected(self):
        response = self.client.post(
            self.url,
            {"items": [{"product": self.product.pk, "quantity": 0}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_client_cannot_override_initial_status(self):
        payload = self.order_payload()
        payload["status"] = Order.Status.SHIPPED
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(pk=response.json()["id"])
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(response.json()["status"], Order.Status.PENDING)

    @patch(
        "inventory.serializers.OrderItem.objects.create",
        side_effect=IntegrityError("Simulated item creation failure"),
    )
    def test_failed_item_creation_rolls_back_order(self, mocked_create):
        self.client.raise_request_exception = False
        response = self.client.post(
            self.url,
            self.order_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(Order.objects.exists())
        mocked_create.assert_called_once()

class InventoryRBACAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        groups = {
            name: Group.objects.create(name=name)
            for name in (
                "Admin",
                "Warehouse Manager",
                "Operator",
                "Auditor",
            )
        }
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(username="admin")
        cls.operator = user_model.objects.create_user(username="operator")
        cls.auditor = user_model.objects.create_user(username="auditor")
        cls.warehouse_manager = user_model.objects.create_user(
            username="warehouse-manager"
        )
        cls.admin_user.groups.add(groups["Admin"])
        cls.operator.groups.add(groups["Operator"])
        cls.auditor.groups.add(groups["Auditor"])
        cls.warehouse_manager.groups.add(groups["Warehouse Manager"])
        cls.product = Product.objects.create(
            name="Test Product",
            sku="TEST-001",
            price="10.00",
        )
        cls.warehouse = Warehouse.objects.create(
            name="Main Warehouse",
            location="Test Location",
        )
        cls.inventory = Inventory.objects.create(
            product=cls.product,
            warehouse=cls.warehouse,
            quantity=10,
        )

    def test_admin_can_create_product(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.post(
            reverse("product-list"),
            {
                "name": "New Product",
                "sku": "NEW-001",
                "price": "25.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(sku="NEW-001").exists())

    def test_operator_cannot_create_product(self):
        self.client.force_authenticate(self.operator)
        response = self.client.post(
            reverse("product-list"),
            {
                "name": "Forbidden Product",
                "sku": "FORBIDDEN-001",
                "price": "25.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Product.objects.filter(sku="FORBIDDEN-001").exists())

    def test_auditor_cannot_modify_inventory(self):
        self.client.force_authenticate(self.auditor)
        response = self.client.patch(
            reverse("inventory-detail", args=(self.inventory.pk,)),
            {"quantity": 20},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)

    def test_warehouse_manager_can_update_inventory(self):
        self.client.force_authenticate(self.warehouse_manager)
        response = self.client.patch(
            reverse("inventory-detail", args=(self.inventory.pk,)),
            {"quantity": 20},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 20)

    def test_auditor_can_read_inventory(self):
        self.client.force_authenticate(self.auditor)
        response = self.client.get(
            reverse("inventory-detail", args=(self.inventory.pk,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.inventory.pk)

class HealthCheckTests(APITestCase):
    def test_liveness_returns_ok_without_database_query(self):
        with self.assertNumQueries(0):
            response = self.client.get(reverse("health-live"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_returns_ready_when_database_is_available(self):
        response = self.client.get(reverse("health-ready"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "status": "ready",
                "database": "ok",
            },
        )

    @patch(
        "inventory.views.connection.cursor",
        side_effect=OperationalError("Database unavailable"),
    )
    def test_readiness_returns_service_unavailable_when_database_fails(
        self,
        mocked_cursor,
    ):
        response = self.client.get(reverse("health-ready"))
        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertEqual(
            response.json(),
            {
                "status": "not_ready",
                "database": "unavailable",
            },
        )
        mocked_cursor.assert_called_once_with()
