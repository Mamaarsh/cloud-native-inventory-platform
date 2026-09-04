from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch
from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import close_old_connections, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from inventory.models import Notification, Order, OrderItem, Payment, Product
from inventory.services.notifications import (
    build_idempotency_key,
    create_notification,
)
from inventory.services.notification_providers import NotificationProviderResult
from inventory.tasks import send_notification

class NotificationIntegrationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name="Admin")
        cls.user = get_user_model().objects.create_user(
            username="notification-admin",
            email="notification@example.com",
        )
        cls.user.groups.add(admin_group)
        cls.product = Product.objects.create(
            name="Notification Product",
            sku="NOTIFY-001",
            price="25.00",
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

    def create_order(self, order_status=Order.Status.PENDING):
        order = Order.objects.create(user=self.user, status=order_status)
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            unit_price=Decimal("25.00"),
        )
        return order

    def pay(self, order):
        return self.client.post(
            reverse("order-pay", args=(order.pk,)),
            {},
            format="json",
        )

    def change_status(self, order, new_status):
        return self.client.post(
            reverse("order-change-status", args=(order.pk,)),
            {"status": new_status},
            format="json",
        )

    def test_successful_payment_creates_and_schedules_one_notification(self):
        order = self.create_order()
        with patch("inventory.tasks.send_notification.delay") as mocked_delay:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                response = self.pay(order)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get()
        self.assertEqual(
            notification.event_type,
            Notification.EventType.PAYMENT_SUCCEEDED,
        )
        self.assertEqual(len(callbacks), 1)
        mocked_delay.assert_called_once_with(notification.pk)

    def test_repeated_payment_does_not_duplicate_notification(self):
        order = self.create_order()
        with patch("inventory.tasks.send_notification.delay"):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                first_response = self.pay(order)
                second_response = self.pay(order)
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(len(callbacks), 1)

    def test_payment_notification_uses_order_user_and_order(self):
        order = self.create_order()
        self.pay(order)
        notification = Notification.objects.get()
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.order, order)
        self.assertEqual(
            notification.message,
            f"Payment succeeded for order #{order.pk}.",
        )

    def test_payment_processing_transition_creates_no_shipped_notification(self):
        order = self.create_order()
        self.pay(order)
        self.assertFalse(
            Notification.objects.filter(
                event_type=Notification.EventType.ORDER_SHIPPED
            ).exists()
        )

    def test_processing_to_shipped_creates_notification(self):
        order = self.create_order(Order.Status.PROCESSING)
        response = self.change_status(order, Order.Status.SHIPPED)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get()
        self.assertEqual(
            notification.event_type,
            Notification.EventType.ORDER_SHIPPED,
        )
        self.assertEqual(
            notification.message,
            f"Order #{order.pk} has been shipped.",
        )

    def test_shipped_to_delivered_creates_notification(self):
        order = self.create_order(Order.Status.SHIPPED)
        response = self.change_status(order, Order.Status.DELIVERED)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get()
        self.assertEqual(
            notification.event_type,
            Notification.EventType.ORDER_DELIVERED,
        )
        self.assertEqual(
            notification.message,
            f"Order #{order.pk} has been delivered.",
        )

    def test_invalid_transition_creates_no_notification(self):
        order = self.create_order()
        response = self.change_status(order, Order.Status.DELIVERED)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Notification.objects.exists())

    def test_notification_failure_does_not_undo_successful_payment(self):
        order = self.create_order()
        self.pay(order)
        notification = Notification.objects.get()
        failure = NotificationProviderResult(
            success=False,
            error="Temporary provider failure",
        )
        with patch(
            "inventory.tasks.mock_notification_provider.send",
            return_value=failure,
        ):
            send_notification.apply(
                args=(notification.pk,),
                retries=send_notification.max_retries,
                throw=True,
            )
        order.refresh_from_db()
        payment = Payment.objects.get(order=order)
        notification.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        self.assertEqual(order.status, Order.Status.PROCESSING)
        self.assertEqual(notification.status, Notification.Status.FAILED)

    def test_notification_failure_does_not_undo_order_transition(self):
        order = self.create_order(Order.Status.PROCESSING)
        self.change_status(order, Order.Status.SHIPPED)
        notification = Notification.objects.get()
        failure = NotificationProviderResult(
            success=False,
            error="Temporary provider failure",
        )
        with patch(
            "inventory.tasks.mock_notification_provider.send",
            return_value=failure,
        ):
            send_notification.apply(
                args=(notification.pk,),
                retries=send_notification.max_retries,
                throw=True,
            )
        order.refresh_from_db()
        notification.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)
        self.assertEqual(notification.status, Notification.Status.FAILED)

class NotificationServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="notification-service-user"
        )
        cls.order = Order.objects.create(user=cls.user)

    def test_idempotency_key_is_deterministic_and_unique(self):
        expected_key = f"payment_succeeded:order:{self.order.pk}"
        with patch("inventory.tasks.send_notification.delay") as mocked_delay:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                first, first_created = create_notification(
                    user=self.user,
                    order=self.order,
                    event_type=Notification.EventType.PAYMENT_SUCCEEDED,
                )
                second, second_created = create_notification(
                    user=self.user,
                    order=self.order,
                    event_type=Notification.EventType.PAYMENT_SUCCEEDED,
                )
        self.assertEqual(
            build_idempotency_key(
                order_id=self.order.pk,
                event_type=Notification.EventType.PAYMENT_SUCCEEDED,
            ),
            expected_key,
        )
        self.assertEqual(first.pk, second.pk)
        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(len(callbacks), 1)
        mocked_delay.assert_called_once_with(first.pk)

    def test_rolled_back_notification_is_not_published(self):
        with patch("inventory.tasks.send_notification.delay") as mocked_delay:
            try:
                with transaction.atomic():
                    create_notification(
                        user=self.user,
                        order=self.order,
                        event_type=Notification.EventType.PAYMENT_SUCCEEDED,
                    )
                    raise RuntimeError("Roll back the domain transaction")
            except RuntimeError:
                pass
        self.assertFalse(Notification.objects.exists())
        mocked_delay.assert_not_called()

class NotificationTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="notification-task-user",
            email="task@example.com",
        )
        cls.order = Order.objects.create(user=cls.user)

    def create_notification(self, **overrides):
        values = {
            "user": self.user,
            "order": self.order,
            "event_type": Notification.EventType.PAYMENT_SUCCEEDED,
            "channel": Notification.Channel.EMAIL,
            "message": f"Payment succeeded for order #{self.order.pk}.",
            "idempotency_key": (
                f"payment_succeeded:order:{self.order.pk}:{Notification.objects.count()}"
            ),
        }
        values.update(overrides)
        return Notification.objects.create(**values)

    def test_successful_delivery_marks_notification_sent(self):
        notification = self.create_notification()
        result = NotificationProviderResult(
            success=True,
            provider_reference="mock_success",
        )
        with patch(
            "inventory.tasks.mock_notification_provider.send",
            return_value=result,
        ):
            send_notification.apply(args=(notification.pk,), throw=True)
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.SENT)
        self.assertEqual(notification.attempts, 1)

    def test_successful_delivery_records_sent_at(self):
        notification = self.create_notification()
        send_notification.apply(args=(notification.pk,), throw=True)
        notification.refresh_from_db()
        self.assertIsNotNone(notification.sent_at)

    def test_successful_delivery_stores_provider_reference(self):
        notification = self.create_notification()
        result = NotificationProviderResult(
            success=True,
            provider_reference="mock_provider_reference",
        )
        with patch(
            "inventory.tasks.mock_notification_provider.send",
            return_value=result,
        ):
            send_notification.apply(args=(notification.pk,), throw=True)
        notification.refresh_from_db()
        self.assertEqual(
            notification.provider_reference,
            "mock_provider_reference",
        )

    def test_already_sent_notification_does_not_call_provider_again(self):
        notification = self.create_notification(
            status=Notification.Status.SENT,
        )
        with patch(
            "inventory.tasks.mock_notification_provider.send"
        ) as mocked_send:
            result = send_notification.apply(
                args=(notification.pk,),
                throw=True,
            )
        self.assertEqual(result.get(), Notification.Status.SENT)
        mocked_send.assert_not_called()

    def test_temporary_failure_requests_retry(self):
        notification = self.create_notification()
        failure = NotificationProviderResult(
            success=False,
            error="Provider temporarily unavailable",
        )
        with (
            patch(
                "inventory.tasks.mock_notification_provider.send",
                return_value=failure,
            ),
            patch.object(send_notification, "retry", side_effect=Retry()) as retry,
        ):
            with self.assertRaises(Retry):
                send_notification.run(notification.pk)
        retry.assert_called_once()

    def test_retry_failure_updates_attempts_and_last_error(self):
        notification = self.create_notification()
        failure = NotificationProviderResult(
            success=False,
            error="Provider temporarily unavailable",
        )
        with (
            patch(
                "inventory.tasks.mock_notification_provider.send",
                return_value=failure,
            ),
            patch.object(send_notification, "retry", side_effect=Retry()),
        ):
            with self.assertRaises(Retry):
                send_notification.run(notification.pk)
        notification.refresh_from_db()
        self.assertEqual(notification.attempts, 1)
        self.assertEqual(
            notification.last_error,
            "Provider temporarily unavailable",
        )
        self.assertEqual(notification.status, Notification.Status.PENDING)

    def test_retry_exhaustion_marks_notification_failed(self):
        notification = self.create_notification()
        failure = NotificationProviderResult(
            success=False,
            error="Provider unavailable",
        )
        with patch(
            "inventory.tasks.mock_notification_provider.send",
            return_value=failure,
        ):
            send_notification.apply(
                args=(notification.pk,),
                retries=send_notification.max_retries,
                throw=True,
            )
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertEqual(notification.attempts, 1)
        self.assertEqual(notification.last_error, "Provider unavailable")

class NotificationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="notification-concurrency-user"
        )
        self.order = Order.objects.create(user=self.user)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_event_creation_creates_one_notification(self):
        barrier = Barrier(2, timeout=10)

        def create_event():
            close_old_connections()
            try:
                order = Order.objects.get(pk=self.order.pk)
                user = get_user_model().objects.get(pk=self.user.pk)
                barrier.wait()
                notification, created = create_notification(
                    user=user,
                    order=order,
                    event_type=Notification.EventType.PAYMENT_SUCCEEDED,
                )
                return notification.pk, created
            finally:
                close_old_connections()
        with patch("inventory.tasks.send_notification.delay") as mocked_delay:
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: create_event(), range(2)))
        self.assertEqual(len({result[0] for result in results}), 1)
        self.assertCountEqual([result[1] for result in results], (True, False))
        self.assertEqual(Notification.objects.count(), 1)
        mocked_delay.assert_called_once()