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

class ProductDeletionAPITests(APITestCase):
    protected_detail = (
        "This product cannot be deleted because it is referenced by inventory "
        "or order history. Deactivate it instead."
    )

    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name="Admin")
        operator_group = Group.objects.create(name="Operator")
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(username="delete-product-admin")
        cls.operator = user_model.objects.create_user(
            username="delete-product-operator"
        )
        cls.admin.groups.add(admin_group)
        cls.operator.groups.add(operator_group)
        cls.warehouse = Warehouse.objects.create(
            name="Deletion Warehouse",
            location="Deletion Location",
        )

    def create_product(self, sku):
        return Product.objects.create(
            name=f"Deletion Product {sku}",
            sku=sku,
            price="10.00",
        )

    def delete(self, user, product):
        self.client.force_authenticate(user)
        return self.client.delete(
            reverse("product-detail", args=(product.pk,)),
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

    def test_unused_product_can_be_deleted(self):
        product = self.create_product("DELETE-UNUSED")
        response = self.delete(self.admin, product)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_product_referenced_by_inventory_is_rejected_cleanly(self):
        product = self.create_product("DELETE-INVENTORY")
        inventory = Inventory.objects.create(
            product=product,
            warehouse=self.warehouse,
            quantity=5,
        )
        response = self.delete(self.admin, product)
        self.assert_protected_conflict(response)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        self.assertTrue(Inventory.objects.filter(pk=inventory.pk).exists())

    def test_product_with_stock_audit_history_is_not_deleted(self):
        product = self.create_product("DELETE-MOVEMENT")
        inventory = Inventory.objects.create(
            product=product,
            warehouse=self.warehouse,
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
        response = self.delete(self.admin, product)
        self.assert_protected_conflict(response)
        self.assertTrue(InventoryMovement.objects.filter(pk=movement.pk).exists())

    def test_product_referenced_by_order_item_is_rejected_cleanly(self):
        product = self.create_product("DELETE-ORDER")
        order = Order.objects.create(user=self.admin)
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            warehouse=self.warehouse,
            quantity=1,
            unit_price="10.00",
        )
        response = self.delete(self.admin, product)
        self.assert_protected_conflict(response)
        self.assertTrue(OrderItem.objects.filter(pk=order_item.pk).exists())

    def test_protected_error_fallback_returns_the_same_safe_conflict(self):
        product = self.create_product("DELETE-RACE")
        protected_error = ProtectedError(
            "Database-specific protected relation details",
            set(),
        )
        with patch.object(Product, "delete", side_effect=protected_error):
            response = self.delete(self.admin, product)
        self.assert_protected_conflict(response)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_non_admin_delete_permission_remains_denied(self):
        product = self.create_product("DELETE-FORBIDDEN")
        response = self.delete(self.operator, product)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())