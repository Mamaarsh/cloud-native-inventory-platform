from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import OperationalError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Inventory, Product, Warehouse

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
