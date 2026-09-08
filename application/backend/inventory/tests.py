from io import BytesIO
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection
from django.db import IntegrityError, OperationalError
from django.test import (
    TransactionTestCase,
    override_settings,
    skipUnlessDBFeature,
)
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase
from redis.exceptions import RedisError
from .models import (
    Inventory,
    Notification,
    Order,
    OrderItem,
    Payment,
    Product,
    Warehouse,
)
from .services import create_order, process_payment
from .services.payment_providers import PaymentProviderResult

class PaymentAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name="Admin")
        cls.user = get_user_model().objects.create_user(
            username="payment-admin"
        )
        cls.user.groups.add(admin_group)
        cls.warehouse = Warehouse.objects.create(
            name="Payment Warehouse",
            location="Payment Location",
        )
        cls.first_product = Product.objects.create(
            name="Payment Product A",
            sku="PAY-001",
            price="200.00",
        )
        cls.second_product = Product.objects.create(
            name="Payment Product B",
            sku="PAY-002",
            price="20.00",
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

    def create_order(self, status=Order.Status.PENDING, with_items=True):
        order = Order.objects.create(user=self.user, status=status)
        if with_items:
            OrderItem.objects.create(
                order=order,
                product=self.first_product,
                warehouse=self.warehouse,
                quantity=2,
                unit_price=Decimal("100.00"),
            )
            OrderItem.objects.create(
                order=order,
                product=self.second_product,
                warehouse=self.warehouse,
                quantity=3,
                unit_price=Decimal("20.00"),
            )
        return order

    def pay(self, order, data=None):
        return self.client.post(
            reverse("order-pay", args=(order.pk,)),
            {} if data is None else data,
            format="json",
        )

    def detail(self, order):
        return self.client.get(reverse("order-detail", args=(order.pk,)))

    def test_pending_order_can_be_paid_successfully(self):
        order = self.create_order()
        response = self.pay(order)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["status"], Payment.Status.SUCCEEDED)

    def test_successful_payment_creates_payment(self):
        order = self.create_order()
        response = self.pay(order)
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.pk, response.json()["id"])
        self.assertEqual(payment.provider, "mock")
        self.assertTrue(payment.provider_reference.startswith("mock_"))

    def test_amount_uses_historical_order_item_prices(self):
        order = self.create_order()
        response = self.pay(order)
        self.assertEqual(response.json()["amount"], "260.00")
        self.assertEqual(order.payment.amount, Decimal("260.00"))

    def test_product_price_change_does_not_change_payment_amount(self):
        order = self.create_order()
        self.first_product.price = Decimal("999.00")
        self.first_product.save(update_fields=("price",))
        response = self.pay(order)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["amount"], "260.00")

    def test_client_cannot_provide_amount(self):
        order = self.create_order()
        response = self.pay(order, {"amount": "1.00"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Payment.objects.filter(order=order).exists())

    def test_client_cannot_override_payment_status(self):
        order = self.create_order()
        response = self.pay(order, {"status": Payment.Status.REFUNDED})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Payment.objects.filter(order=order).exists())

    def test_client_cannot_inject_provider_reference(self):
        order = self.create_order()
        response = self.pay(
            order,
            {"provider_reference": "client-controlled"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Payment.objects.filter(order=order).exists())

    def test_successful_payment_moves_pending_order_to_processing(self):
        order = self.create_order()
        self.pay(order)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PROCESSING)

    @patch(
        "inventory.services.payments.mock_payment_provider.charge",
        return_value=PaymentProviderResult(
            success=False,
            provider_reference="mock_failed",
        ),
    )
    def test_failed_payment_leaves_order_pending(self, mocked_charge):
        order = self.create_order()
        response = self.pay(order)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["status"], Payment.Status.FAILED)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        mocked_charge.assert_called_once()

    def test_cancelled_order_cannot_be_paid(self):
        order = self.create_order(status=Order.Status.CANCELLED)
        response = self.pay(order)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Payment.objects.filter(order=order).exists())

    def test_delivered_order_cannot_be_paid(self):
        order = self.create_order(status=Order.Status.DELIVERED)
        response = self.pay(order)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Payment.objects.filter(order=order).exists())

    def test_empty_order_cannot_be_paid(self):
        order = self.create_order(with_items=False)
        response = self.pay(order)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Payment.objects.filter(order=order).exists())

    @patch(
        "inventory.services.payments.mock_payment_provider.charge",
        return_value=PaymentProviderResult(
            success=True,
            provider_reference="mock_idempotent",
        ),
    )
    def test_repeated_payment_returns_existing_payment(self, mocked_charge):
        order = self.create_order()
        first_response = self.pay(order)
        second_response = self.pay(order)
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.json()["id"], second_response.json()["id"])
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)
        mocked_charge.assert_called_once()

    def test_payment_response_has_expected_fields(self):
        order = self.create_order()
        response = self.pay(order)
        self.assertSetEqual(
            set(response.json()),
            {
                "id",
                "order",
                "amount",
                "status",
                "provider",
                "provider_reference",
                "created_at",
                "updated_at",
            },
        )

    def test_unpaid_order_detail_has_null_payment(self):
        order = self.create_order()

        response = self.detail(order)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.json()["payment"])

    def test_successful_payment_persists_in_order_detail(self):
        order = self.create_order()
        payment_response = self.pay(order)

        response = self.detail(order)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = response.json()["payment"]
        self.assertSetEqual(
            set(payment),
            {
                "id",
                "order",
                "amount",
                "status",
                "provider",
                "provider_reference",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(payment["id"], payment_response.json()["id"])
        self.assertEqual(payment["order"], order.pk)
        self.assertEqual(payment["amount"], "260.00")
        self.assertEqual(payment["status"], Payment.Status.SUCCEEDED)
        self.assertEqual(payment["provider"], "mock")
        self.assertEqual(
            payment["provider_reference"],
            payment_response.json()["provider_reference"],
        )

    def test_failed_payment_is_exposed_and_remains_payable(self):
        order = self.create_order()
        with patch(
            "inventory.services.payments.mock_payment_provider.charge",
            return_value=PaymentProviderResult(
                success=False,
                provider_reference="mock_failed_detail",
            ),
        ) as mocked_failure:
            failed_response = self.pay(order)

        response = self.detail(order)

        self.assertEqual(failed_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["payment"]["status"],
            Payment.Status.FAILED,
        )
        mocked_failure.assert_called_once()

        with patch(
            "inventory.services.payments.mock_payment_provider.charge",
            return_value=PaymentProviderResult(
                success=True,
                provider_reference="mock_retry_succeeded",
            ),
        ) as mocked_retry:
            retry_response = self.pay(order)

        self.assertEqual(retry_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            retry_response.json()["id"],
            failed_response.json()["id"],
        )
        self.assertEqual(
            retry_response.json()["status"],
            Payment.Status.SUCCEEDED,
        )
        mocked_retry.assert_called_once()

    def test_payment_fields_cannot_be_changed_through_order_patch(self):
        order = self.create_order()
        self.pay(order)
        payment = Payment.objects.get(order=order)
        original_values = (
            payment.status,
            payment.amount,
            payment.provider,
            payment.provider_reference,
        )

        response = self.client.patch(
            reverse("order-detail", args=(order.pk,)),
            {
                "payment": {
                    "status": Payment.Status.REFUNDED,
                    "amount": "1.00",
                    "provider": "client-controlled",
                    "provider_reference": "client-controlled",
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(
            (
                payment.status,
                payment.amount,
                payment.provider,
                payment.provider_reference,
            ),
            original_values,
        )

    def test_non_admin_cannot_use_pay_action(self):
        operator_group, _ = Group.objects.get_or_create(name="Operator")
        operator = get_user_model().objects.create_user(
            username="payment-operator"
        )
        operator.groups.add(operator_group)
        order = self.create_order()
        self.client.force_authenticate(operator)

        response = self.pay(order)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Payment.objects.filter(order=order).exists())

    def test_order_detail_joins_payment_without_a_separate_query(self):
        order = self.create_order()
        self.pay(order)

        with CaptureQueriesContext(connection) as query_context:
            response = self.detail(order)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statements = [query["sql"] for query in query_context.captured_queries]
        self.assertTrue(
            any('JOIN "inventory_payment"' in sql for sql in statements)
        )
        self.assertFalse(
            any('FROM "inventory_payment"' in sql for sql in statements)
        )

class PaymentConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="payment-concurrency-user"
        )
        product = Product.objects.create(
            name="Payment Concurrency Product",
            sku="PAY-CONCURRENT-001",
            price="50.00",
        )
        warehouse = Warehouse.objects.create(
            name="Payment Concurrency Warehouse",
            location="Payment Concurrency Location",
        )
        self.order = Order.objects.create(user=self.user)
        OrderItem.objects.create(
            order=self.order,
            product=product,
            warehouse=warehouse,
            quantity=2,
            unit_price=Decimal("50.00"),
        )

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_payment_attempts_create_one_payment(self):
        barrier = Barrier(2, timeout=10)

        def attempt_payment():
            close_old_connections()
            try:
                order = Order.objects.get(pk=self.order.pk)
                barrier.wait()
                payment, created = process_payment(order)
                return payment.pk, created
            finally:
                close_old_connections()
        provider_result = PaymentProviderResult(
            success=True,
            provider_reference="mock_concurrent",
        )
        with (
            patch(
                "inventory.services.payments.mock_payment_provider.charge",
                return_value=provider_result,
            ) as mocked_charge,
            patch("inventory.tasks.send_notification.delay") as mocked_delivery,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(
                    executor.map(lambda _: attempt_payment(), range(2))
                )
        payment_ids = {payment_id for payment_id, _ in results}
        created_flags = [created for _, created in results]
        self.assertEqual(len(payment_ids), 1)
        self.assertCountEqual(created_flags, (True, False))
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)
        mocked_charge.assert_called_once()
        mocked_delivery.assert_called_once()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PROCESSING)

class OrderStatusWorkflowAPITests(APITestCase):
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
        cls.admin_user = user_model.objects.create_user(
            username="status-admin"
        )
        cls.warehouse_manager = user_model.objects.create_user(
            username="status-warehouse-manager"
        )
        cls.operator = user_model.objects.create_user(
            username="status-operator"
        )
        cls.auditor = user_model.objects.create_user(
            username="status-auditor"
        )
        cls.admin_user.groups.add(groups["Admin"])
        cls.warehouse_manager.groups.add(groups["Warehouse Manager"])
        cls.operator.groups.add(groups["Operator"])
        cls.auditor.groups.add(groups["Auditor"])

    def create_order(self, status=Order.Status.PENDING):
        return Order.objects.create(user=self.admin_user, status=status)

    def change_status(self, user, order, new_status):
        self.client.force_authenticate(user)
        return self.client.post(
            reverse("order-change-status", args=(order.pk,)),
            {"status": new_status},
            format="json",
        )

    def test_admin_can_change_pending_to_processing(self):
        order = self.create_order()
        response = self.change_status(
            self.admin_user,
            order,
            Order.Status.PROCESSING,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], Order.Status.PROCESSING)

    def test_warehouse_manager_can_change_processing_to_shipped(self):
        order = self.create_order(status=Order.Status.PROCESSING)
        response = self.change_status(
            self.warehouse_manager,
            order,
            Order.Status.SHIPPED,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], Order.Status.SHIPPED)

    def test_operator_cannot_change_status(self):
        order = self.create_order()
        response = self.change_status(
            self.operator,
            order,
            Order.Status.PROCESSING,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_auditor_cannot_change_status(self):
        order = self.create_order()
        response = self.change_status(
            self.auditor,
            order,
            Order.Status.PROCESSING,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_transition_is_rejected(self):
        order = self.create_order()
        response = self.change_status(
            self.admin_user,
            order,
            Order.Status.DELIVERED,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_delivered_order_cannot_change_status(self):
        order = self.create_order(status=Order.Status.DELIVERED)
        response = self.change_status(
            self.admin_user,
            order,
            Order.Status.CANCELLED,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)

    def test_successful_transition_updates_database(self):
        order = self.create_order()
        self.change_status(
            self.admin_user,
            order,
            Order.Status.PROCESSING,
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PROCESSING)

    def test_response_uses_order_serializer_format(self):
        order = self.create_order()
        response = self.change_status(
            self.admin_user,
            order,
            Order.Status.PROCESSING,
        )
        self.assertSetEqual(
            set(response.json()),
            {
                "id",
                "user",
                "status",
                "created_at",
                "updated_at",
                "items",
            },
        )
        self.assertEqual(response.json()["items"], [])

    def test_status_cannot_be_changed_with_normal_patch(self):
        order = self.create_order()
        self.client.force_authenticate(self.admin_user)
        response = self.client.patch(
            reverse("order-detail", args=(order.pk,)),
            {"status": Order.Status.PROCESSING},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

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
        cls.warehouse = Warehouse.objects.create(
            name="Order Warehouse",
            location="Order Test Location",
        )
        Inventory.objects.create(
            product=cls.product,
            warehouse=cls.warehouse,
            quantity=100,
        )
        Inventory.objects.create(
            product=cls.second_product,
            warehouse=cls.warehouse,
            quantity=100,
        )

    def setUp(self):
        self.client.force_authenticate(self.user)
        self.url = reverse("order-list")

    def order_payload(self):
        return {
            "items": [
                {
                    "product": self.product.pk,
                    "warehouse": self.warehouse.pk,
                    "quantity": 2,
                },
                {
                    "product": self.second_product.pk,
                    "warehouse": self.warehouse.pk,
                    "quantity": 1,
                },
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
            {
                "items": [
                    {
                        "product": self.product.pk,
                        "warehouse": self.warehouse.pk,
                        "quantity": 1,
                    }
                ]
            },
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
                    {
                        "product": self.inactive_product.pk,
                        "warehouse": self.warehouse.pk,
                        "quantity": 1,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_zero_quantity_is_rejected(self):
        response = self.client.post(
            self.url,
            {
                "items": [
                    {
                        "product": self.product.pk,
                        "warehouse": self.warehouse.pk,
                        "quantity": 0,
                    }
                ]
            },
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
        "inventory.services.orders.OrderItem.objects.bulk_create",
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
        inventories = Inventory.objects.filter(
            warehouse=self.warehouse
        ).order_by("product_id")
        self.assertEqual(
            list(inventories.values_list("quantity", flat=True)),
            [100, 100],
        )
        mocked_create.assert_called_once()

class OrderStockManagementAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name="Admin")
        cls.user = get_user_model().objects.create_user(
            username="stock-admin"
        )
        cls.user.groups.add(admin_group)
        cls.primary_warehouse = Warehouse.objects.create(
            name="Primary Warehouse",
            location="Primary Location",
        )
        cls.secondary_warehouse = Warehouse.objects.create(
            name="Secondary Warehouse",
            location="Secondary Location",
        )
        cls.first_product = Product.objects.create(
            name="First Stock Product",
            sku="STOCK-001",
            price="12.50",
        )
        cls.second_product = Product.objects.create(
            name="Second Stock Product",
            sku="STOCK-002",
            price="30.00",
        )
        cls.first_inventory = Inventory.objects.create(
            product=cls.first_product,
            warehouse=cls.primary_warehouse,
            quantity=10,
        )
        cls.second_inventory = Inventory.objects.create(
            product=cls.second_product,
            warehouse=cls.secondary_warehouse,
            quantity=20,
        )

    def setUp(self):
        self.client.force_authenticate(self.user)
        self.url = reverse("order-list")

    def item(self, product, warehouse, quantity):
        return {
            "product": product.pk,
            "warehouse": warehouse.pk,
            "quantity": quantity,
        }

    def test_successful_order_decreases_inventory(self):
        response = self.client.post(
            self.url,
            {
                "items": [
                    self.item(
                        self.first_product,
                        self.primary_warehouse,
                        4,
                    )
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.first_inventory.refresh_from_db()
        self.assertEqual(self.first_inventory.quantity, 6)

    def test_insufficient_stock_creates_no_order_or_items(self):
        response = self.client.post(
            self.url,
            {
                "items": [
                    self.item(
                        self.first_product,
                        self.primary_warehouse,
                        11,
                    )
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient stock", response.json()["items"][0])
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())

    def test_multiple_items_decrease_respective_inventory(self):
        response = self.client.post(
            self.url,
            {
                "items": [
                    self.item(
                        self.first_product,
                        self.primary_warehouse,
                        3,
                    ),
                    self.item(
                        self.second_product,
                        self.secondary_warehouse,
                        5,
                    ),
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.first_inventory.refresh_from_db()
        self.second_inventory.refresh_from_db()
        self.assertEqual(self.first_inventory.quantity, 7)
        self.assertEqual(self.second_inventory.quantity, 15)

    def test_one_failed_item_rolls_back_entire_stock_operation(self):
        response = self.client.post(
            self.url,
            {
                "items": [
                    self.item(
                        self.first_product,
                        self.primary_warehouse,
                        2,
                    ),
                    self.item(
                        self.second_product,
                        self.secondary_warehouse,
                        21,
                    ),
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.first_inventory.refresh_from_db()
        self.second_inventory.refresh_from_db()
        self.assertEqual(self.first_inventory.quantity, 10)
        self.assertEqual(self.second_inventory.quantity, 20)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())

    def test_inventory_never_becomes_negative(self):
        response = self.client.post(
            self.url,
            {
                "items": [
                    self.item(
                        self.first_product,
                        self.primary_warehouse,
                        100,
                    )
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.first_inventory.refresh_from_db()
        self.assertEqual(self.first_inventory.quantity, 10)
        self.assertGreaterEqual(self.first_inventory.quantity, 0)

    def test_duplicate_items_are_aggregated_for_stock_validation(self):
        duplicate_item = self.item(
            self.first_product,
            self.primary_warehouse,
            6,
        )

        response = self.client.post(
            self.url,
            {"items": [duplicate_item, duplicate_item]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.first_inventory.refresh_from_db()
        self.assertEqual(self.first_inventory.quantity, 10)
        self.assertFalse(Order.objects.exists())

    def test_missing_inventory_returns_bad_request(self):
        response = self.client.post(
            self.url,
            {
                "items": [
                    self.item(
                        self.first_product,
                        self.secondary_warehouse,
                        1,
                    )
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No inventory exists", response.json()["items"][0])
        self.assertFalse(Order.objects.exists())

    def test_response_includes_warehouse_and_existing_order_fields(self):
        response = self.client.post(
            self.url,
            {
                "items": [
                    self.item(
                        self.first_product,
                        self.primary_warehouse,
                        1,
                    )
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertSetEqual(
            set(response.json()),
            {
                "id",
                "user",
                "status",
                "created_at",
                "updated_at",
                "items",
            },
        )
        item = response.json()["items"][0]
        self.assertEqual(item["warehouse"]["id"], self.primary_warehouse.pk)
        self.assertEqual(item["unit_price"], "12.50")

class OrderStockConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="concurrency-user"
        )
        self.product = Product.objects.create(
            name="Concurrent Product",
            sku="CONCURRENT-001",
            price="10.00",
        )
        self.warehouse = Warehouse.objects.create(
            name="Concurrent Warehouse",
            location="Concurrent Location",
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=10,
        )

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_orders_cannot_oversell_locked_inventory(self):
        barrier = Barrier(2, timeout=10)

        def attempt_order():
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=self.user.pk)
                product = Product.objects.get(pk=self.product.pk)
                warehouse = Warehouse.objects.get(pk=self.warehouse.pk)
                barrier.wait()
                create_order(
                    user=user,
                    items=[
                        {
                            "product": product,
                            "warehouse": warehouse,
                            "quantity": 8,
                        }
                    ],
                )
            except ValidationError:
                return "rejected"
            finally:
                close_old_connections()
            return "created"
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: attempt_order(), range(2)))
        self.assertCountEqual(results, ("created", "rejected"))
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 2)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)


class ProductImageAPITests(APITestCase):
    def setUp(self):
        self.temporary_media = TemporaryDirectory()
        self.addCleanup(self.temporary_media.cleanup)
        media_override = override_settings(
            MEDIA_ROOT=self.temporary_media.name
        )
        media_override.enable()
        self.addCleanup(media_override.disable)

        admin_group = Group.objects.create(name="Admin")
        self.admin_user = get_user_model().objects.create_user(
            username="product-image-admin"
        )
        self.admin_user.groups.add(admin_group)
        self.client.force_authenticate(self.admin_user)
        self.product_url = reverse("product-list")

    def image_upload(
        self,
        name="product.png",
        image_format="PNG",
        size=(32, 32),
    ):
        buffer = BytesIO()
        Image.new("RGB", size, color=(20, 100, 180)).save(
            buffer,
            format=image_format,
        )
        content_types = {
            "BMP": "image/bmp",
            "GIF": "image/gif",
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
        }
        return SimpleUploadedFile(
            name,
            buffer.getvalue(),
            content_type=content_types[image_format],
        )

    def create_product(self, image=None, **overrides):
        payload = {
            "name": "Image Product",
            "sku": "IMAGE-001",
            "price": "49.90",
            **overrides,
        }
        if image is not None:
            payload["image"] = image
        return self.client.post(
            self.product_url,
            payload,
            format="multipart" if image is not None else "json",
        )

    def create_order_item(self, product):
        warehouse = Warehouse.objects.create(
            name="Image Warehouse",
            location="Image Test Location",
        )
        order = Order.objects.create(user=self.admin_user)
        OrderItem.objects.create(
            order=order,
            product=product,
            warehouse=warehouse,
            quantity=1,
            unit_price=product.price,
        )
        return order

    def test_product_can_be_created_without_image(self):
        response = self.create_product()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.json()["image"])
        self.assertFalse(Product.objects.get(pk=response.json()["id"]).image)

    def test_product_can_be_created_with_valid_image(self):
        response = self.create_product(self.image_upload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.json()["image"])

    def test_supported_image_formats_are_accepted(self):
        formats = (
            ("JPEG", "product.jpg"),
            ("PNG", "product.png"),
            ("WEBP", "product.webp"),
        )
        for index, (image_format, filename) in enumerate(formats):
            with self.subTest(image_format=image_format):
                response = self.create_product(
                    self.image_upload(filename, image_format),
                    sku=f"IMAGE-{index + 10}",
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_201_CREATED,
                )

    def test_uploaded_image_is_persisted(self):
        response = self.create_product(self.image_upload())
        product = Product.objects.get(pk=response.json()["id"])

        self.assertTrue(product.image.name.startswith("products/"))
        self.assertTrue(product.image.storage.exists(product.image.name))

    def test_product_api_returns_deployment_independent_image_url(self):
        response = self.create_product(self.image_upload())
        product = Product.objects.get(pk=response.json()["id"])
        image_url = response.json()["image"]

        self.assertTrue(image_url.endswith(product.image.url))
        self.assertIn("/media/products/", image_url)
        self.assertNotIn(self.temporary_media.name, image_url)

    def test_patch_without_image_preserves_existing_image(self):
        create_response = self.create_product(self.image_upload())
        product = Product.objects.get(pk=create_response.json()["id"])
        original_image_name = product.image.name

        response = self.client.patch(
            reverse("product-detail", args=(product.pk,)),
            {"price": "59.90"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertEqual(product.image.name, original_image_name)
        self.assertTrue(product.image.storage.exists(original_image_name))

    def test_product_image_can_be_replaced(self):
        create_response = self.create_product(self.image_upload())
        product = Product.objects.get(pk=create_response.json()["id"])
        original_image_name = product.image.name
        storage = product.image.storage

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                reverse("product-detail", args=(product.pk,)),
                {"image": self.image_upload("replacement.webp", "WEBP")},
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertNotEqual(product.image.name, original_image_name)
        self.assertTrue(storage.exists(product.image.name))
        self.assertFalse(storage.exists(original_image_name))

    def test_product_image_can_be_removed_explicitly(self):
        create_response = self.create_product(self.image_upload())
        product = Product.objects.get(pk=create_response.json()["id"])
        original_image_name = product.image.name
        storage = product.image.storage

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                reverse("product-detail", args=(product.pk,)),
                {"remove_image": True},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.json()["image"])
        product.refresh_from_db()
        self.assertFalse(product.image)
        self.assertFalse(storage.exists(original_image_name))

    def test_invalid_non_image_upload_is_rejected(self):
        invalid_file = SimpleUploadedFile(
            "not-an-image.png",
            b"This is not image data.",
            content_type="image/png",
        )

        response = self.create_product(invalid_file)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", response.json())
        self.assertFalse(Product.objects.exists())

    def test_oversized_image_is_rejected(self):
        oversized_image = self.image_upload(
            "oversized.bmp",
            "BMP",
            size=(2000, 1000),
        )
        self.assertGreater(oversized_image.size, 5 * 1024 * 1024)

        response = self.create_product(oversized_image)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("5 MB", response.json()["image"][0])
        self.assertFalse(Product.objects.exists())

    def test_unsupported_image_format_is_rejected(self):
        response = self.create_product(
            self.image_upload("animated.gif", "GIF")
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unsupported image format", response.json()["image"][0])
        self.assertFalse(Product.objects.exists())

    def test_svg_upload_is_rejected(self):
        svg_file = SimpleUploadedFile(
            "product.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
            content_type="image/svg+xml",
        )

        response = self.create_product(svg_file)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", response.json())
        self.assertFalse(Product.objects.exists())

    def test_image_with_executable_filename_extension_is_rejected(self):
        response = self.create_product(
            self.image_upload("product.html", "PNG")
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", response.json())
        self.assertFalse(Product.objects.exists())

    def test_image_content_must_match_filename_extension(self):
        response = self.create_product(
            self.image_upload("product.jpg", "PNG")
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "filename extension does not match",
            response.json()["image"][0],
        )
        self.assertFalse(Product.objects.exists())

    def test_persian_product_name_is_preserved_with_image(self):
        response = self.create_product(
            self.image_upload(),
            name="اسکنر انبار",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(pk=response.json()["id"])
        self.assertEqual(product.name, "اسکنر انبار")

    def test_product_permissions_remain_unchanged_for_image_uploads(self):
        operator_group = Group.objects.create(name="Operator")
        operator = get_user_model().objects.create_user(
            username="product-image-operator"
        )
        operator.groups.add(operator_group)
        self.client.force_authenticate(operator)

        response = self.create_product(
            self.image_upload(),
            sku="IMAGE-FORBIDDEN",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Product.objects.filter(sku="IMAGE-FORBIDDEN").exists())

    def test_order_detail_and_list_expose_product_image(self):
        product_response = self.create_product(self.image_upload())
        product = Product.objects.get(pk=product_response.json()["id"])
        order = self.create_order_item(product)

        detail_response = self.client.get(
            reverse("order-detail", args=(order.pk,))
        )
        list_response = self.client.get(reverse("order-list"))

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        detail_image = detail_response.json()["items"][0]["product"]["image"]
        self.assertTrue(detail_image.endswith(product.image.url))
        listed_order = next(
            item
            for item in list_response.json()["results"]
            if item["id"] == order.pk
        )
        self.assertTrue(
            listed_order["items"][0]["product"]["image"].endswith(
                product.image.url
            )
        )

    def test_order_without_product_image_serializes_null(self):
        product = Product.objects.create(
            name="Product Without Image",
            sku="IMAGE-NONE",
            price="20.00",
        )
        order = self.create_order_item(product)

        response = self.client.get(
            reverse("order-detail", args=(order.pk,))
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(
            response.json()["items"][0]["product"]["image"]
        )

    def test_order_uses_current_product_image_and_historical_price(self):
        product_response = self.create_product(self.image_upload())
        product = Product.objects.get(pk=product_response.json()["id"])
        order = self.create_order_item(product)
        historical_price = order.items.get().unit_price

        with self.captureOnCommitCallbacks(execute=True):
            update_response = self.client.patch(
                reverse("product-detail", args=(product.pk,)),
                {"image": self.image_upload("current.webp", "WEBP")},
                format="multipart",
            )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()

        response = self.client.get(
            reverse("order-detail", args=(order.pk,))
        )

        item = response.json()["items"][0]
        self.assertTrue(item["product"]["image"].endswith(product.image.url))
        self.assertEqual(Decimal(item["unit_price"]), historical_price)


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

    def test_warehouse_manager_cannot_bypass_inventory_adjustment(self):
        self.client.force_authenticate(self.warehouse_manager)
        response = self.client.patch(
            reverse("inventory-detail", args=(self.inventory.pk,)),
            {"quantity": 20},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)

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

    @patch(
        "inventory.views.Redis.from_url",
        side_effect=RedisError("Redis unavailable"),
    )
    def test_readiness_succeeds_when_database_is_available_even_if_redis_fails(
        self,
        mocked_from_url,
    ):
        response = self.client.get(reverse("health-ready"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "status": "ready",
                "checks": {
                    "database": "ok",
                },
            },
        )
        mocked_from_url.assert_not_called()

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
                "checks": {
                    "database": "unavailable",
                },
            },
        )
        mocked_cursor.assert_called_once_with()

    @patch("inventory.views.Redis.from_url")
    def test_dependencies_endpoint_returns_healthy(
        self,
        mocked_from_url,
    ):
        redis_client = mocked_from_url.return_value
        response = self.client.get(reverse("health-dependencies"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "status": "healthy",
                "checks": {
                    "database": "ok",
                    "redis": "ok",
                },
            },
        )
        redis_client.ping.assert_called_once_with()
        redis_client.close.assert_called_once_with()

    @patch(
        "inventory.views.Redis.from_url",
        side_effect=RedisError("Redis unavailable"),
    )
    def test_dependencies_endpoint_reports_degraded_when_redis_fails(
        self,
        mocked_from_url,
    ):
        response = self.client.get(reverse("health-dependencies"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "status": "degraded",
                "checks": {
                    "database": "ok",
                    "redis": "unavailable",
                },
            },
        )
        mocked_from_url.assert_called_once()

    @patch("inventory.views.Redis.from_url")
    @patch(
        "inventory.views.connection.cursor",
        side_effect=OperationalError("Database unavailable"),
    )
    def test_dependencies_endpoint_reports_unhealthy_when_database_fails(
        self,
        mocked_cursor,
        mocked_from_url,
    ):
        response = self.client.get(reverse("health-dependencies"))
        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertEqual(
            response.json(),
            {
                "status": "unhealthy",
                "checks": {
                    "database": "unavailable",
                    "redis": "ok",
                },
            },
        )
        mocked_cursor.assert_called_once_with()
        mocked_from_url.return_value.ping.assert_called_once_with()
