from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase
from inventory.models import (
    Inventory,
    InventoryMovement,
    Order,
    Product,
    Warehouse,
)
from inventory.services import adjust_inventory

class InventoryAdjustmentServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="stock-service-user"
        )
        cls.product = Product.objects.create(
            name="Service Product",
            sku="MOVEMENT-SERVICE-001",
            price="10.00",
        )
        cls.warehouse = Warehouse.objects.create(
            name="Service Warehouse",
            location="Service Location",
        )
        cls.inventory = Inventory.objects.create(
            product=cls.product,
            warehouse=cls.warehouse,
            quantity=10,
        )

    def test_positive_adjustment_records_balanced_movement(self):
        inventory, movement = adjust_inventory(
            inventory=self.inventory,
            quantity_delta=5,
            performed_by=self.user,
            reason="Count correction",
        )
        self.assertEqual(inventory.quantity, 15)
        self.assertEqual(movement.quantity_before, 10)
        self.assertEqual(movement.quantity_delta, 5)
        self.assertEqual(movement.quantity_after, 15)
        self.assertEqual(
            movement.movement_type,
            InventoryMovement.Type.MANUAL_ADJUSTMENT,
        )

    def test_negative_adjustment_records_balanced_movement(self):
        inventory, movement = adjust_inventory(
            inventory=self.inventory,
            quantity_delta=-3,
            performed_by=self.user,
            reason="Damaged stock",
        )
        self.assertEqual(inventory.quantity, 7)
        self.assertEqual(
            (
                movement.quantity_before,
                movement.quantity_delta,
                movement.quantity_after,
            ),
            (10, -3, 7),
        )

    def test_zero_adjustment_is_rejected(self):
        with self.assertRaises(ValidationError):
            adjust_inventory(
                inventory=self.inventory,
                quantity_delta=0,
                performed_by=self.user,
                reason="Invalid adjustment",
            )
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)
        self.assertFalse(InventoryMovement.objects.exists())

    def test_negative_result_is_rejected_without_movement(self):
        with self.assertRaises(ValidationError):
            adjust_inventory(
                inventory=self.inventory,
                quantity_delta=-11,
                performed_by=self.user,
                reason="Too much stock removed",
            )
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)
        self.assertFalse(InventoryMovement.objects.exists())

    def test_movement_failure_rolls_back_inventory_update(self):
        with patch(
            "inventory.services.stock.InventoryMovement.objects.create",
            side_effect=IntegrityError("Simulated movement failure"),
        ):
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    adjust_inventory(
                        inventory=self.inventory,
                        quantity_delta=5,
                        performed_by=self.user,
                        reason="Rollback test",
                    )
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)
        self.assertFalse(InventoryMovement.objects.exists())

    def test_movement_cannot_be_updated_or_deleted(self):
        _, movement = adjust_inventory(
            inventory=self.inventory,
            quantity_delta=1,
            performed_by=self.user,
            reason="Immutable movement",
        )

        movement.reason = "Rewritten history"
        with self.assertRaises(DjangoValidationError):
            movement.save()
        with self.assertRaises(DjangoValidationError):
            movement.delete()

        persisted = InventoryMovement.objects.get(pk=movement.pk)
        self.assertEqual(persisted.reason, "Immutable movement")


class InventoryAdjustmentAPITests(APITestCase):
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
        cls.admin = user_model.objects.create_user(username="movement-admin")
        cls.manager = user_model.objects.create_user(username="movement-manager")
        cls.operator = user_model.objects.create_user(username="movement-operator")
        cls.auditor = user_model.objects.create_user(username="movement-auditor")
        cls.admin.groups.add(groups["Admin"])
        cls.manager.groups.add(groups["Warehouse Manager"])
        cls.operator.groups.add(groups["Operator"])
        cls.auditor.groups.add(groups["Auditor"])
        cls.product = Product.objects.create(
            name="API Product",
            sku="MOVEMENT-API-001",
            price="15.00",
        )
        cls.warehouse = Warehouse.objects.create(
            name="API Warehouse",
            location="API Location",
        )

    def setUp(self):
        self.inventory = Inventory.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=20,
        )
        self.adjust_url = reverse(
            "inventory-adjust",
            args=(self.inventory.pk,),
        )

    def test_warehouse_manager_can_adjust_inventory(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post(
            self.adjust_url,
            {
                "quantity_delta": 10,
                "reason": "Physical stock count correction",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 30)
        movement = InventoryMovement.objects.get(inventory=self.inventory)
        self.assertEqual(movement.reason, "Physical stock count correction")
        self.assertEqual(movement.performed_by, self.manager)
        self.assertEqual(
            (
                response.json()["quantity_before"],
                response.json()["quantity_delta"],
                response.json()["quantity_after"],
            ),
            (20, 10, 30),
        )

    def test_operator_cannot_adjust_inventory(self):
        self.client.force_authenticate(self.operator)
        response = self.client.post(
            self.adjust_url,
            {"quantity_delta": 5, "reason": "Not authorized"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 20)
        self.assertFalse(InventoryMovement.objects.exists())

    def test_adjustment_requires_nonzero_integer_and_reason(self):
        self.client.force_authenticate(self.manager)
        payloads = (
            {"quantity_delta": 0, "reason": "Zero"},
            {"quantity_delta": 1.5, "reason": "Decimal"},
            {"quantity_delta": 1, "reason": ""},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    self.adjust_url,
                    payload,
                    format="json",
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
        self.assertFalse(InventoryMovement.objects.exists())

    def test_adjustment_cannot_make_inventory_negative(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.adjust_url,
            {"quantity_delta": -21, "reason": "Invalid removal"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 20)
        self.assertFalse(InventoryMovement.objects.exists())

    def test_server_calculated_fields_cannot_be_supplied(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.adjust_url,
            {
                "quantity_delta": 5,
                "reason": "Attempted override",
                "quantity_before": 1000,
                "quantity_after": 1005,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 20)
        self.assertFalse(InventoryMovement.objects.exists())

    def test_direct_quantity_update_is_rejected(self):
        self.client.force_authenticate(self.manager)
        response = self.client.patch(
            reverse("inventory-detail", args=(self.inventory.pk,)),
            {"quantity": 25},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 20)
        self.assertFalse(InventoryMovement.objects.exists())

    def test_new_inventory_with_stock_records_initial_movement(self):
        self.client.force_authenticate(self.operator)
        product = Product.objects.create(
            name="Initial Product",
            sku="MOVEMENT-INITIAL-001",
            price="5.00",
        )
        response = self.client.post(
            reverse("inventory-list"),
            {
                "product": product.pk,
                "warehouse": self.warehouse.pk,
                "quantity": 8,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movement = InventoryMovement.objects.get(
            inventory_id=response.json()["id"]
        )
        self.assertEqual(movement.movement_type, InventoryMovement.Type.INITIAL_STOCK)
        self.assertEqual(
            (
                movement.quantity_before,
                movement.quantity_delta,
                movement.quantity_after,
            ),
            (0, 8, 8),
        )
        self.assertEqual(movement.performed_by, self.operator)

    def test_inventory_with_movement_history_cannot_be_deleted(self):
        self.client.force_authenticate(self.admin)
        self.client.post(
            self.adjust_url,
            {"quantity_delta": 1, "reason": "Create audit history"},
            format="json",
        )

        response = self.client.delete(
            reverse("inventory-detail", args=(self.inventory.pk,))
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Inventory.objects.filter(pk=self.inventory.pk).exists())
        self.assertTrue(
            InventoryMovement.objects.filter(inventory=self.inventory).exists()
        )

class OrderStockMovementAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name="Admin")
        cls.user = get_user_model().objects.create_user(
            username="movement-order-admin"
        )
        cls.user.groups.add(admin_group)
        cls.warehouse = Warehouse.objects.create(
            name="Movement Order Warehouse",
            location="Movement Order Location",
        )
        cls.first_product = Product.objects.create(
            name="Movement Order Product A",
            sku="MOVEMENT-ORDER-001",
            price="12.00",
        )
        cls.second_product = Product.objects.create(
            name="Movement Order Product B",
            sku="MOVEMENT-ORDER-002",
            price="18.00",
        )

    def setUp(self):
        self.first_inventory = Inventory.objects.create(
            product=self.first_product,
            warehouse=self.warehouse,
            quantity=20,
        )
        self.second_inventory = Inventory.objects.create(
            product=self.second_product,
            warehouse=self.warehouse,
            quantity=30,
        )
        self.client.force_authenticate(self.user)

    def create_order(self, items):
        return self.client.post(
            reverse("order-list"),
            {"items": items},
            format="json",
        )

    def item(self, product, quantity):
        return {
            "product": product.pk,
            "warehouse": self.warehouse.pk,
            "quantity": quantity,
        }

    def test_order_deduction_creates_linked_movement(self):
        response = self.create_order([self.item(self.first_product, 3)])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movement = InventoryMovement.objects.get(inventory=self.first_inventory)
        self.assertEqual(movement.movement_type, InventoryMovement.Type.ORDER_DEDUCTION)
        self.assertEqual(movement.order_id, response.json()["id"])
        self.assertEqual(movement.performed_by, self.user)
        self.assertEqual(
            (
                movement.quantity_before,
                movement.quantity_delta,
                movement.quantity_after,
            ),
            (20, -3, 17),
        )

    def test_multi_product_order_creates_one_movement_per_inventory(self):
        response = self.create_order(
            [
                self.item(self.first_product, 2),
                self.item(self.second_product, 4),
            ]
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movements = InventoryMovement.objects.filter(
            order_id=response.json()["id"]
        ).order_by("inventory_id")
        self.assertEqual(movements.count(), 2)
        self.assertEqual(
            list(movements.values_list("quantity_delta", flat=True)),
            [-2, -4],
        )

    def test_duplicate_lines_produce_one_aggregated_movement(self):
        response = self.create_order(
            [
                self.item(self.first_product, 2),
                self.item(self.first_product, 3),
            ]
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movement = InventoryMovement.objects.get(inventory=self.first_inventory)
        self.assertEqual(movement.quantity_delta, -5)
        self.assertEqual(movement.quantity_after, 15)

    def test_insufficient_stock_creates_no_movement_or_order(self):
        response = self.create_order([self.item(self.first_product, 21)])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(InventoryMovement.objects.exists())
        self.assertFalse(Order.objects.exists())
        self.first_inventory.refresh_from_db()
        self.assertEqual(self.first_inventory.quantity, 20)

    @patch(
        "inventory.services.orders.OrderItem.objects.bulk_create",
        side_effect=IntegrityError("Simulated item creation failure"),
    )
    def test_item_failure_rolls_back_stock_and_movements(self, mocked_create):
        self.client.raise_request_exception = False
        response = self.create_order([self.item(self.first_product, 3)])
        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        self.first_inventory.refresh_from_db()
        self.assertEqual(self.first_inventory.quantity, 20)
        self.assertFalse(InventoryMovement.objects.exists())
        self.assertFalse(Order.objects.exists())
        mocked_create.assert_called_once()

class InventoryMovementReadAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        groups = {
            name: Group.objects.create(name=name)
            for name in ("Admin", "Auditor")
        }
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(username="history-admin")
        cls.auditor = user_model.objects.create_user(username="history-auditor")
        cls.outsider = user_model.objects.create_user(username="history-outsider")
        cls.admin.groups.add(groups["Admin"])
        cls.auditor.groups.add(groups["Auditor"])
        cls.product = Product.objects.create(
            name="History Product",
            sku="MOVEMENT-HISTORY-001",
            price="7.00",
        )
        cls.warehouse = Warehouse.objects.create(
            name="History Warehouse",
            location="History Location",
        )
        cls.inventory = Inventory.objects.create(
            product=cls.product,
            warehouse=cls.warehouse,
            quantity=10,
        )
        for index in range(12):
            adjust_inventory(
                inventory=cls.inventory,
                quantity_delta=1,
                performed_by=cls.admin,
                reason=f"History movement {index}",
            )

    def setUp(self):
        self.url = reverse(
            "inventory-movements",
            args=(self.inventory.pk,),
        )

    def test_history_is_newest_first_and_paginated(self):
        self.client.force_authenticate(self.auditor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 12)
        self.assertEqual(len(response.json()["results"]), 10)
        movement_ids = [item["id"] for item in response.json()["results"]]
        self.assertEqual(movement_ids, sorted(movement_ids, reverse=True))

    def test_history_exposes_safe_display_fields(self):
        self.client.force_authenticate(self.auditor)
        response = self.client.get(self.url)
        movement = response.json()["results"][0]
        self.assertSetEqual(
            set(movement),
            {
                "id",
                "inventory",
                "movement_type",
                "quantity_delta",
                "quantity_before",
                "quantity_after",
                "reason",
                "order_id",
                "performed_by",
                "created_at",
            },
        )
        self.assertSetEqual(set(movement["performed_by"]), {"id", "username"})

    def test_history_is_read_only(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_user_without_inventory_role_cannot_read_history(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_history_uses_joined_user_and_order_data(self):
        self.client.force_authenticate(self.auditor)
        with CaptureQueriesContext(connection) as query_context:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        movement_row_queries = [
            query["sql"]
            for query in query_context.captured_queries
            if 'FROM "inventory_inventorymovement"' in query["sql"]
            and 'JOIN "users_user"' in query["sql"]
        ]
        self.assertEqual(len(movement_row_queries), 1)
        self.assertFalse(
            any(
                'FROM "users_user"' in query["sql"]
                for query in query_context.captured_queries
            )
        )

class InventoryAdjustmentConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="movement-concurrency-user"
        )
        product = Product.objects.create(
            name="Movement Concurrency Product",
            sku="MOVEMENT-CONCURRENCY-001",
            price="10.00",
        )
        warehouse = Warehouse.objects.create(
            name="Movement Concurrency Warehouse",
            location="Movement Concurrency Location",
        )
        self.inventory = Inventory.objects.create(
            product=product,
            warehouse=warehouse,
            quantity=10,
        )

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_adjustments_serialize_without_lost_updates(self):
        barrier = Barrier(2, timeout=10)

        def perform_adjustment(quantity_delta):
            close_old_connections()
            try:
                inventory = Inventory.objects.get(pk=self.inventory.pk)
                user = get_user_model().objects.get(pk=self.user.pk)
                barrier.wait()
                adjust_inventory(
                    inventory=inventory,
                    quantity_delta=quantity_delta,
                    performed_by=user,
                    reason="Concurrent adjustment",
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(perform_adjustment, (5, -3)))

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 12)
        movements = list(
            InventoryMovement.objects.filter(
                inventory=self.inventory
            ).order_by("created_at", "pk")
        )
        self.assertEqual(len(movements), 2)
        self.assertEqual(movements[0].quantity_before, 10)
        self.assertEqual(
            movements[1].quantity_before,
            movements[0].quantity_after,
        )
        self.assertEqual(movements[1].quantity_after, 12)
