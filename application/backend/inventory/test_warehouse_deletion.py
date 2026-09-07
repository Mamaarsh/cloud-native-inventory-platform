from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.deletion import ProtectedError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from inventory.models import (
    Inventory,
    InventoryMovement,
    Order,
    OrderItem,
    Product,
    Warehouse,
)

class WarehouseDeletionAPITests(APITestCase):
    protected_detail = (
        "This warehouse cannot be deleted because it is referenced by "
        "inventory or order history."
    )

    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name="Admin")
        operator_group = Group.objects.create(name="Operator")
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(
            username="delete-warehouse-admin"
        )
        cls.operator = user_model.objects.create_user(
            username="delete-warehouse-operator"
        )
        cls.admin.groups.add(admin_group)
        cls.operator.groups.add(operator_group)
        cls.product = Product.objects.create(
            name="Warehouse Deletion Product",
            sku="DELETE-WAREHOUSE-001",
            price="10.00",
        )

    def create_warehouse(self, name):
        return Warehouse.objects.create(
            name=name,
            location="Deletion Location",
        )

    def delete(self, user, warehouse):
        self.client.force_authenticate(user)
        return self.client.delete(
            reverse("warehouse-detail", args=(warehouse.pk,)),
        )

    def assert_protected_conflict(self, response):
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            response.headers["Content-Type"].split(";", maxsplit=1)[0],
            "application/json",
        )
        self.assertEqual(response.json(), {"detail": self.protected_detail})
        response_text = response.content.decode()
        self.assertNotIn("ProtectedError", response_text)
        self.assertNotIn("Traceback", response_text)
        self.assertNotIn("OrderItem object", response_text)
        self.assertNotIn("InventoryMovement object", response_text)

    def test_unused_warehouse_can_be_deleted(self):
        warehouse = self.create_warehouse("Unused Warehouse")
        response = self.delete(self.admin, warehouse)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Warehouse.objects.filter(pk=warehouse.pk).exists())

    def test_warehouse_referenced_by_inventory_is_rejected_cleanly(self):
        warehouse = self.create_warehouse("Inventory Warehouse")
        inventory = Inventory.objects.create(
            product=self.product,
            warehouse=warehouse,
            quantity=5,
        )
        response = self.delete(self.admin, warehouse)
        self.assert_protected_conflict(response)
        self.assertTrue(Warehouse.objects.filter(pk=warehouse.pk).exists())
        self.assertTrue(Inventory.objects.filter(pk=inventory.pk).exists())

    def test_warehouse_with_stock_audit_history_is_not_deleted(self):
        warehouse = self.create_warehouse("Movement Warehouse")
        inventory = Inventory.objects.create(
            product=self.product,
            warehouse=warehouse,
            quantity=5,
        )
        movement = InventoryMovement.objects.create(
            inventory=inventory,
            movement_type=InventoryMovement.Type.INITIAL_STOCK,
            quantity_delta=5,
            quantity_before=0,
            quantity_after=5,
            performed_by=self.admin,
        )
        response = self.delete(self.admin, warehouse)
        self.assert_protected_conflict(response)
        self.assertTrue(InventoryMovement.objects.filter(pk=movement.pk).exists())

    def test_warehouse_referenced_by_order_item_is_rejected_cleanly(self):
        warehouse = self.create_warehouse("Order Warehouse")
        order = Order.objects.create(user=self.admin)
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product,
            warehouse=warehouse,
            quantity=1,
            unit_price="10.00",
        )
        response = self.delete(self.admin, warehouse)
        self.assert_protected_conflict(response)
        self.assertTrue(OrderItem.objects.filter(pk=order_item.pk).exists())

    def test_protected_error_fallback_returns_the_same_safe_conflict(self):
        warehouse = self.create_warehouse("Race Warehouse")
        protected_error = ProtectedError(
            "Database-specific protected relation details",
            set(),
        )
        with patch.object(Warehouse, "delete", side_effect=protected_error):
            response = self.delete(self.admin, warehouse)
        self.assert_protected_conflict(response)
        self.assertTrue(Warehouse.objects.filter(pk=warehouse.pk).exists())

    def test_non_admin_delete_permission_remains_denied(self):
        warehouse = self.create_warehouse("Forbidden Warehouse")
        response = self.delete(self.operator, warehouse)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Warehouse.objects.filter(pk=warehouse.pk).exists())