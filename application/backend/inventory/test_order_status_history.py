from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import (
    TransactionTestCase,
    skipUnlessDBFeature,
)
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase
from inventory.models import (
    Inventory,
    Order,
    OrderItem,
    OrderStatusHistory,
    Product,
    Warehouse,
)
from inventory.services.order_status import (
    ALLOWED_STATUS_TRANSITIONS,
    transition_order_status,
)
from inventory.services.payment_providers import PaymentProviderResult

class OrderStatusHistoryCreationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name="Admin")
        cls.user = get_user_model().objects.create_user(
            username="history-creator",
        )
        cls.user.groups.add(admin_group)
        cls.product = Product.objects.create(
            name="History Product",
            sku="ORDER-HISTORY-001",
            price="25.00",
        )
        cls.warehouse = Warehouse.objects.create(
            name="History Warehouse",
            location="History Location",
        )

    def setUp(self):
        self.client.force_authenticate(self.user)
        self.inventory = Inventory.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=10,
        )

    def order_payload(self, quantity=2):
        return {
            "items": [
                {
                    "product": self.product.pk,
                    "warehouse": self.warehouse.pk,
                    "quantity": quantity,
                }
            ]
        }

    def test_new_order_creates_initial_history_event(self):
        response = self.client.post(
            reverse("order-list"),
            self.order_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = OrderStatusHistory.objects.get(order_id=response.json()["id"])
        self.assertIsNone(event.from_status)
        self.assertEqual(event.to_status, Order.Status.PENDING)
        self.assertEqual(event.performed_by, self.user)
        self.assertIsNotNone(event.created_at)

    def test_failed_order_creation_rolls_back_initial_history(self):
        response = self.client.post(
            reverse("order-list"),
            self.order_payload(quantity=11),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderStatusHistory.objects.exists())

class OrderStatusHistoryTransitionTests(APITestCase):
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
        cls.admin = user_model.objects.create_user(username="history-admin")
        cls.manager = user_model.objects.create_user(username="history-manager")
        cls.operator = user_model.objects.create_user(username="history-operator")
        cls.auditor = user_model.objects.create_user(username="history-auditor")
        cls.outsider = user_model.objects.create_user(username="history-outsider")
        cls.admin.groups.add(groups["Admin"])
        cls.manager.groups.add(groups["Warehouse Manager"])
        cls.operator.groups.add(groups["Operator"])
        cls.auditor.groups.add(groups["Auditor"])
        cls.product = Product.objects.create(
            name="Transition Product",
            sku="ORDER-HISTORY-002",
            price="40.00",
        )
        cls.warehouse = Warehouse.objects.create(
            name="Transition Warehouse",
            location="Transition Location",
        )

    def create_legacy_order(self, status_value=Order.Status.PENDING):
        return Order.objects.create(user=self.admin, status=status_value)

    def change_status(self, user, order, new_status):
        self.client.force_authenticate(user)
        return self.client.post(
            reverse("order-change-status", args=(order.pk,)),
            {"status": new_status},
            format="json",
        )

    def test_valid_transition_records_statuses_actor_and_timestamp(self):
        order = self.create_legacy_order()
        response = self.change_status(
            self.admin,
            order,
            Order.Status.PROCESSING,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PROCESSING)
        event = OrderStatusHistory.objects.get(order=order)
        self.assertEqual(event.from_status, Order.Status.PENDING)
        self.assertEqual(event.to_status, Order.Status.PROCESSING)
        self.assertEqual(event.performed_by, self.admin)
        self.assertIsNotNone(event.created_at)

    def test_warehouse_manager_transition_records_actor(self):
        order = self.create_legacy_order(Order.Status.PROCESSING)
        response = self.change_status(
            self.manager,
            order,
            Order.Status.SHIPPED,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            OrderStatusHistory.objects.get(order=order).performed_by,
            self.manager,
        )

    def test_invalid_transition_changes_neither_order_nor_history(self):
        order = self.create_legacy_order()
        response = self.change_status(
            self.admin,
            order,
            Order.Status.DELIVERED,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertFalse(OrderStatusHistory.objects.filter(order=order).exists())

    def test_unauthorized_transition_creates_no_history(self):
        order = self.create_legacy_order()
        response = self.change_status(
            self.operator,
            order,
            Order.Status.PROCESSING,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertFalse(OrderStatusHistory.objects.filter(order=order).exists())

    def test_history_failure_rolls_back_status_update(self):
        order = self.create_legacy_order()
        with patch(
            "inventory.services.order_status.OrderStatusHistory.objects.create",
            side_effect=IntegrityError("Simulated history failure"),
        ):
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    transition_order_status(
                        order,
                        Order.Status.PROCESSING,
                        performed_by=self.admin,
                    )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertFalse(OrderStatusHistory.objects.filter(order=order).exists())

    def test_direct_status_patch_cannot_bypass_history(self):
        order = self.create_legacy_order()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            reverse("order-detail", args=(order.pk,)),
            {"status": Order.Status.PROCESSING},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertFalse(OrderStatusHistory.objects.filter(order=order).exists())

    def test_successful_payment_transition_records_request_actor(self):
        order = self.create_legacy_order()
        OrderItem.objects.create(
            order=order,
            product=self.product,
            warehouse=self.warehouse,
            quantity=2,
            unit_price=Decimal("40.00"),
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("order-pay", args=(order.pk,)),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = OrderStatusHistory.objects.get(order=order)
        self.assertEqual(event.from_status, Order.Status.PENDING)
        self.assertEqual(event.to_status, Order.Status.PROCESSING)
        self.assertEqual(event.performed_by, self.admin)

    @patch(
        "inventory.services.payments.mock_payment_provider.charge",
        return_value=PaymentProviderResult(
            success=False,
            provider_reference="mock_history_failure",
        ),
    )
    def test_failed_payment_creates_no_status_history(self, mocked_charge):
        order = self.create_legacy_order()
        OrderItem.objects.create(
            order=order,
            product=self.product,
            warehouse=self.warehouse,
            quantity=1,
            unit_price=Decimal("40.00"),
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("order-pay", args=(order.pk,)),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertFalse(OrderStatusHistory.objects.filter(order=order).exists())
        mocked_charge.assert_called_once()

    def test_history_model_is_immutable(self):
        order = self.create_legacy_order()
        event = OrderStatusHistory.objects.create(
            order=order,
            from_status=None,
            to_status=Order.Status.PENDING,
            performed_by=self.admin,
        )
        event.to_status = Order.Status.PROCESSING
        with self.assertRaises(DjangoValidationError):
            event.save()
        with self.assertRaises(DjangoValidationError):
            event.delete()
        event.refresh_from_db()
        self.assertEqual(event.to_status, Order.Status.PENDING)

    def test_database_rejects_invalid_history_states(self):
        order = self.create_legacy_order()
        invalid_events = (
            {
                "from_status": Order.Status.PENDING,
                "to_status": Order.Status.PENDING,
            },
            {
                "from_status": Order.Status.PENDING,
                "to_status": "unknown",
            },
        )
        for event_fields in invalid_events:
            with self.subTest(event_fields=event_fields):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        OrderStatusHistory.objects.create(
                            order=order,
                            performed_by=self.admin,
                            **event_fields,
                        )

    def test_order_with_history_cannot_be_deleted_through_api(self):
        order = self.create_legacy_order()
        OrderStatusHistory.objects.create(
            order=order,
            from_status=None,
            to_status=Order.Status.PENDING,
            performed_by=self.admin,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.delete(
            reverse("order-detail", args=(order.pk,)),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())
        self.assertTrue(OrderStatusHistory.objects.filter(order=order).exists())

class OrderStatusHistoryReadAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        groups = {
            name: Group.objects.create(name=name)
            for name in ("Admin", "Auditor")
        }
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(username="history-reader-admin")
        cls.auditor = user_model.objects.create_user(
            username="history-reader-auditor"
        )
        cls.outsider = user_model.objects.create_user(
            username="history-reader-outsider"
        )
        cls.admin.groups.add(groups["Admin"])
        cls.auditor.groups.add(groups["Auditor"])

    def setUp(self):
        self.order = Order.objects.create(user=self.admin)
        self.initial_event = OrderStatusHistory.objects.create(
            order=self.order,
            from_status=None,
            to_status=Order.Status.PENDING,
            performed_by=self.admin,
        )
        self.processing_event = OrderStatusHistory.objects.create(
            order=self.order,
            from_status=Order.Status.PENDING,
            to_status=Order.Status.PROCESSING,
            performed_by=self.admin,
        )
        self.other_order = Order.objects.create(user=self.admin)
        OrderStatusHistory.objects.create(
            order=self.other_order,
            from_status=None,
            to_status=Order.Status.PENDING,
            performed_by=self.admin,
        )
        self.url = reverse("order-history", args=(self.order.pk,))

    def test_history_is_chronological_scoped_and_has_safe_fields(self):
        self.client.force_authenticate(self.auditor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [entry["id"] for entry in response.json()],
            [self.initial_event.pk, self.processing_event.pk],
        )
        self.assertSetEqual(
            set(response.json()[0]),
            {
                "id",
                "from_status",
                "to_status",
                "performed_by",
                "created_at",
            },
        )
        self.assertSetEqual(
            set(response.json()[0]["performed_by"]),
            {"id", "username"},
        )

    def test_history_endpoint_is_read_only(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url,
            {"to_status": Order.Status.DELIVERED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        delete_response = self.client.delete(self.url)
        self.assertEqual(
            delete_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_inventory_reader_can_read_but_outsider_cannot(self):
        self.client.force_authenticate(self.auditor)
        allowed_response = self.client.get(self.url)
        self.client.force_authenticate(self.outsider)
        denied_response = self.client.get(self.url)
        self.assertEqual(allowed_response.status_code, status.HTTP_200_OK)
        self.assertEqual(denied_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_history_query_joins_actor_without_n_plus_one_queries(self):
        self.client.force_authenticate(self.admin)
        with CaptureQueriesContext(connection) as query_context:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        history_queries = [
            query["sql"]
            for query in query_context.captured_queries
            if 'FROM "inventory_orderstatushistory"' in query["sql"]
        ]
        self.assertEqual(len(history_queries), 1)
        self.assertIn('JOIN "users_user"', history_queries[0])

    def test_legacy_order_without_history_remains_readable(self):
        legacy_order = Order.objects.create(user=self.admin)
        self.client.force_authenticate(self.auditor)
        detail_response = self.client.get(
            reverse("order-detail", args=(legacy_order.pk,)),
        )
        history_response = self.client.get(
            reverse("order-history", args=(legacy_order.pk,)),
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertEqual(history_response.json(), [])

class OrderStatusHistoryConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="history-concurrency-user",
        )
        self.order = Order.objects.create(user=self.user)

    @skipUnlessDBFeature("has_select_for_update")
    def test_conflicting_transitions_serialize_into_a_valid_chain(self):
        barrier = Barrier(2, timeout=10)

        def perform_transition(new_status):
            close_old_connections()
            try:
                stale_order = Order.objects.get(pk=self.order.pk)
                user = get_user_model().objects.get(pk=self.user.pk)
                barrier.wait()
                transition_order_status(
                    stale_order,
                    new_status,
                    performed_by=user,
                )
                return "updated"
            except ValidationError:
                return "rejected"
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    perform_transition,
                    (Order.Status.PROCESSING, Order.Status.CANCELLED),
                )
            )
        self.order.refresh_from_db()
        events = list(
            OrderStatusHistory.objects.filter(order=self.order).order_by(
                "created_at",
                "pk",
            )
        )
        current_status = Order.Status.PENDING
        for event in events:
            self.assertEqual(event.from_status, current_status)
            self.assertIn(
                event.to_status,
                ALLOWED_STATUS_TRANSITIONS[current_status],
            )
            current_status = event.to_status
        self.assertEqual(current_status, self.order.status)
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertIn(results.count("updated"), {1, 2})
        self.assertEqual(results.count("rejected"), 2 - results.count("updated"))
