from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from inventory.models import (
    AuditLog,
    Inventory,
    InventoryMovement,
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    Product,
    Warehouse,
)
from inventory.services.audit import record_audit_event


class AuditLogModelServiceTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_user(
            username="audit-service-actor"
        )

    def test_service_creates_safe_snapshot_event(self):
        event = record_audit_event(
            actor=self.actor,
            action=AuditLog.Action.USER_ROLE_CHANGED,
            target_type=AuditLog.TargetType.USER,
            target_id=42,
            target_label="operator1",
            metadata={"old_role": "Operator", "new_role": "Auditor"},
        )

        self.assertEqual(event.actor, self.actor)
        self.assertEqual(event.target_id, "42")
        self.assertEqual(event.target_label, "operator1")
        self.assertEqual(
            event.metadata,
            {"old_role": "Operator", "new_role": "Auditor"},
        )

    def test_target_snapshot_survives_target_deletion(self):
        product = Product.objects.create(
            name="Deleted Snapshot Product",
            sku="AUDIT-SNAPSHOT-001",
            price="10.00",
        )
        product_id = product.pk
        event = record_audit_event(
            actor=self.actor,
            action=AuditLog.Action.PRODUCT_DELETED,
            target_type=AuditLog.TargetType.PRODUCT,
            target_id=product_id,
            target_label=f"{product.name} · {product.sku}",
        )

        product.delete()
        event.refresh_from_db()
        self.assertEqual(event.target_id, str(product_id))
        self.assertEqual(
            event.target_label,
            "Deleted Snapshot Product · AUDIT-SNAPSHOT-001",
        )

    def test_actor_is_set_null_when_user_is_deleted(self):
        event = record_audit_event(
            actor=self.actor,
            action=AuditLog.Action.USER_PASSWORD_CHANGED,
            target_type=AuditLog.TargetType.USER,
            target_id=self.actor.pk,
            target_label=self.actor.username,
        )

        self.actor.delete()
        event.refresh_from_db()
        self.assertIsNone(event.actor)

    def test_instance_update_and_delete_are_rejected(self):
        event = record_audit_event(
            actor=self.actor,
            action=AuditLog.Action.PRODUCT_CREATED,
            target_type=AuditLog.TargetType.PRODUCT,
            target_id=1,
            target_label="Immutable Product",
        )
        event.target_label = "Rewritten history"

        with self.assertRaises(DjangoValidationError):
            event.save()
        with self.assertRaises(DjangoValidationError):
            event.delete()
        event.refresh_from_db()
        self.assertEqual(event.target_label, "Immutable Product")

    def test_sensitive_or_unsupported_metadata_is_rejected(self):
        unsafe_metadata = {
            "changes": {
                "password": {"before": "old-secret", "after": "new-secret"}
            }
        }

        with self.assertRaises(DjangoValidationError):
            record_audit_event(
                actor=self.actor,
                action=AuditLog.Action.PRODUCT_UPDATED,
                target_type=AuditLog.TargetType.PRODUCT,
                target_id=1,
                target_label="Safe Product",
                metadata=unsafe_metadata,
            )
        self.assertFalse(AuditLog.objects.exists())


class AuditLogReadAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.groups = {
            name: Group.objects.create(name=name)
            for name in ("Admin", "Warehouse Manager", "Operator", "Auditor")
        }
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(username="audit-admin")
        cls.auditor = user_model.objects.create_user(username="audit-auditor")
        cls.manager = user_model.objects.create_user(username="audit-manager")
        cls.operator = user_model.objects.create_user(username="audit-operator")
        cls.unassigned_superuser = user_model.objects.create_superuser(
            username="audit-unassigned-superuser"
        )
        cls.admin.groups.add(cls.groups["Admin"])
        cls.auditor.groups.add(cls.groups["Auditor"])
        cls.manager.groups.add(cls.groups["Warehouse Manager"])
        cls.operator.groups.add(cls.groups["Operator"])
        cls.first_event = record_audit_event(
            actor=cls.admin,
            action=AuditLog.Action.PRODUCT_CREATED,
            target_type=AuditLog.TargetType.PRODUCT,
            target_id=10,
            target_label="Audit Printer · AUD-010",
        )
        cls.second_event = record_audit_event(
            actor=cls.auditor,
            action=AuditLog.Action.WAREHOUSE_CREATED,
            target_type=AuditLog.TargetType.WAREHOUSE,
            target_id=20,
            target_label="Main Audit Warehouse",
        )
        cls.url = reverse("audit-log-list")

    def test_admin_and_auditor_can_list_newest_first(self):
        for user in (self.admin, self.auditor):
            with self.subTest(user=user.username):
                self.client.force_authenticate(user)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    [row["id"] for row in response.json()["results"][:2]],
                    [self.second_event.pk, self.first_event.pk],
                )

    def test_manager_operator_and_anonymous_are_denied(self):
        for user, expected_status in (
            (self.manager, status.HTTP_403_FORBIDDEN),
            (self.operator, status.HTTP_403_FORBIDDEN),
            (self.unassigned_superuser, status.HTTP_403_FORBIDDEN),
            (None, status.HTTP_401_UNAUTHORIZED),
        ):
            with self.subTest(user=getattr(user, "username", "anonymous")):
                self.client.force_authenticate(user)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, expected_status)

    def test_filters_search_and_pagination_shape(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(
            self.url,
            {
                "target_type": AuditLog.TargetType.PRODUCT,
                "action": AuditLog.Action.PRODUCT_CREATED,
                "actor": self.admin.pk,
                "search": "Printer",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertSetEqual(
            set(response.json()),
            {"count", "next", "previous", "results"},
        )
        self.assertEqual(response.json()["count"], 1)
        row = response.json()["results"][0]
        self.assertEqual(row["actor"]["username"], self.admin.username)
        self.assertEqual(row["target_label"], "Audit Printer · AUD-010")

    def test_endpoint_uses_project_pagination(self):
        for index in range(9):
            record_audit_event(
                actor=self.admin,
                action=AuditLog.Action.PRODUCT_CREATED,
                target_type=AuditLog.TargetType.PRODUCT,
                target_id=100 + index,
                target_label=f"Pagination Product {index}",
            )
        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 11)
        self.assertEqual(len(response.json()["results"]), 10)
        self.assertIsNotNone(response.json()["next"])

    def test_endpoint_is_read_only(self):
        self.client.force_authenticate(self.admin)
        detail_url = reverse("audit-log-detail", args=(self.first_event.pk,))
        responses = (
            self.client.post(self.url, {}, format="json"),
            self.client.patch(detail_url, {"target_label": "Changed"}, format="json"),
            self.client.delete(detail_url),
        )
        self.assertTrue(
            all(
                response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
                for response in responses
            )
        )

    def test_actor_is_joined_without_n_plus_one_queries(self):
        self.client.force_authenticate(self.auditor)
        with CaptureQueriesContext(connection) as query_context:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit_queries = [
            query["sql"]
            for query in query_context.captured_queries
            if 'FROM "inventory_auditlog"' in query["sql"]
        ]
        self.assertEqual(len(audit_queries), 2)
        row_query = next(sql for sql in audit_queries if "JOIN" in sql)
        self.assertIn('JOIN "users_user"', row_query)
        self.assertFalse(
            any(
                'FROM "users_user"' in query["sql"]
                for query in query_context.captured_queries
            )
        )


class AuditedMutationAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.groups = {
            name: Group.objects.create(name=name)
            for name in ("Admin", "Warehouse Manager", "Operator", "Auditor")
        }
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(
            username="mutation-audit-admin",
            password="Audit-admin-password-4821!",
        )
        cls.manager = user_model.objects.create_user(
            username="mutation-audit-manager"
        )
        cls.pending_user = user_model.objects.create_user(
            username="mutation-pending-user",
            is_active=False,
        )
        cls.admin.groups.add(cls.groups["Admin"])
        cls.manager.groups.add(cls.groups["Warehouse Manager"])

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_user_registration_activation_role_and_password_are_audited_safely(self):
        self.client.force_authenticate(None)
        registration_response = self.client.post(
            reverse("users:register"),
            {
                "username": "audit-registered-user",
                "email": "audit-registered@example.com",
                "password": "Granite-River-4821!",
                "password_confirm": "Granite-River-4821!",
            },
            format="json",
        )
        self.assertEqual(registration_response.status_code, status.HTTP_201_CREATED)
        registered_user = get_user_model().objects.get(
            username="audit-registered-user"
        )
        registration_event = AuditLog.objects.get(
            action=AuditLog.Action.USER_REGISTERED,
            target_id=str(registered_user.pk),
        )
        self.assertIsNone(registration_event.actor)
        self.assertEqual(registration_event.metadata, {})

        self.client.force_authenticate(self.admin)
        update_response = self.client.patch(
            reverse("users:admin-user-detail", args=(self.pending_user.pk,)),
            {"is_active": True, "role": "Operator"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        actions = set(
            AuditLog.objects.filter(target_id=str(self.pending_user.pk))
            .values_list("action", flat=True)
        )
        self.assertIn(AuditLog.Action.USER_ACTIVATED, actions)
        self.assertIn(AuditLog.Action.USER_ROLE_CHANGED, actions)
        role_event = AuditLog.objects.get(
            action=AuditLog.Action.USER_ROLE_CHANGED,
            target_id=str(self.pending_user.pk),
        )
        self.assertEqual(
            role_event.metadata,
            {"old_role": None, "new_role": "Operator"},
        )

        password_response = self.client.post(
            reverse("users:change-password"),
            {
                "current_password": "Audit-admin-password-4821!",
                "new_password": "New-audit-password-5932!",
                "new_password_confirm": "New-audit-password-5932!",
            },
            format="json",
        )
        self.assertEqual(password_response.status_code, status.HTTP_200_OK)
        password_event = AuditLog.objects.get(
            action=AuditLog.Action.USER_PASSWORD_CHANGED,
            target_id=str(self.admin.pk),
        )
        self.assertEqual(password_event.metadata, {})
        serialized_event = str(password_event.metadata)
        self.assertNotIn("Audit-admin-password", serialized_event)
        self.assertNotIn("New-audit-password", serialized_event)

    def test_product_lifecycle_is_audited_and_failed_delete_is_not(self):
        create_response = self.client.post(
            reverse("product-list"),
            {
                "name": "Audited Product",
                "sku": "AUDITED-PRODUCT-001",
                "price": "30.10",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        product_id = create_response.json()["id"]

        update_response = self.client.patch(
            reverse("product-detail", args=(product_id,)),
            {"price": "32.00"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        update_event = AuditLog.objects.get(
            action=AuditLog.Action.PRODUCT_UPDATED,
            target_id=str(product_id),
        )
        self.assertEqual(
            update_event.metadata["changes"]["price"],
            {"before": "30.10", "after": "32.00"},
        )

        deactivate_response = self.client.patch(
            reverse("product-detail", args=(product_id,)),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(deactivate_response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.PRODUCT_DEACTIVATED,
                target_id=str(product_id),
            ).exists()
        )
        reactivate_response = self.client.patch(
            reverse("product-detail", args=(product_id,)),
            {"is_active": True},
            format="json",
        )
        self.assertEqual(reactivate_response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.PRODUCT_ACTIVATED,
                target_id=str(product_id),
            ).exists()
        )

        product = Product.objects.get(pk=product_id)
        warehouse = Warehouse.objects.create(
            name="Protected Audit Warehouse",
            location="Protected",
        )
        Inventory.objects.create(
            product=product,
            warehouse=warehouse,
            quantity=0,
        )
        delete_response = self.client.delete(
            reverse("product-detail", args=(product_id,))
        )
        self.assertEqual(delete_response.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(
            AuditLog.objects.filter(
                action=AuditLog.Action.PRODUCT_DELETED,
                target_id=str(product_id),
            ).exists()
        )

        unused_response = self.client.post(
            reverse("product-list"),
            {
                "name": "Unused Audited Product",
                "sku": "AUDITED-PRODUCT-DELETE",
                "price": "5.00",
                "is_active": True,
            },
            format="json",
        )
        unused_id = unused_response.json()["id"]
        successful_delete = self.client.delete(
            reverse("product-detail", args=(unused_id,))
        )
        self.assertEqual(successful_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.PRODUCT_DELETED,
                target_id=str(unused_id),
            ).exists()
        )

    def test_product_update_rolls_back_when_audit_creation_fails(self):
        product = Product.objects.create(
            name="Rollback Product",
            sku="AUDIT-ROLLBACK-001",
            price="10.00",
        )
        with patch(
            "inventory.views.record_audit_event",
            side_effect=IntegrityError("Simulated audit failure"),
        ):
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    self.client.patch(
                        reverse("product-detail", args=(product.pk,)),
                        {"price": "20.00"},
                        format="json",
                    )
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal("10.00"))

    def test_role_change_rolls_back_when_audit_creation_fails(self):
        managed_user = get_user_model().objects.create_user(
            username="role-audit-rollback-user"
        )
        with patch(
            "users.serializers.record_audit_event",
            side_effect=IntegrityError("Simulated audit failure"),
        ):
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    self.client.patch(
                        reverse(
                            "users:admin-user-detail",
                            args=(managed_user.pk,),
                        ),
                        {"role": "Operator"},
                        format="json",
                    )
        managed_user.refresh_from_db()
        self.assertFalse(managed_user.groups.exists())

    def test_warehouse_create_update_and_delete_are_audited(self):
        create_response = self.client.post(
            reverse("warehouse-list"),
            {"name": "Audited Warehouse", "location": "North"},
            format="json",
        )
        warehouse_id = create_response.json()["id"]
        self.client.patch(
            reverse("warehouse-detail", args=(warehouse_id,)),
            {"location": "South"},
            format="json",
        )
        self.client.delete(reverse("warehouse-detail", args=(warehouse_id,)))

        self.assertSetEqual(
            set(
                AuditLog.objects.filter(target_id=str(warehouse_id)).values_list(
                    "action", flat=True
                )
            ),
            {
                AuditLog.Action.WAREHOUSE_CREATED,
                AuditLog.Action.WAREHOUSE_UPDATED,
                AuditLog.Action.WAREHOUSE_DELETED,
            },
        )

    def test_inventory_adjustment_references_authoritative_movement(self):
        product = Product.objects.create(
            name="Audited Stock Product",
            sku="AUDITED-STOCK-001",
            price="8.00",
        )
        warehouse = Warehouse.objects.create(
            name="Audited Stock Warehouse",
            location="West",
        )
        create_response = self.client.post(
            reverse("inventory-list"),
            {"product": product.pk, "warehouse": warehouse.pk, "quantity": 0},
            format="json",
        )
        inventory_id = create_response.json()["id"]
        adjust_response = self.client.post(
            reverse("inventory-adjust", args=(inventory_id,)),
            {"quantity_delta": 5, "reason": "Verified physical count"},
            format="json",
        )
        self.assertEqual(adjust_response.status_code, status.HTTP_201_CREATED)
        movement = InventoryMovement.objects.get(pk=adjust_response.json()["id"])
        event = AuditLog.objects.get(
            action=AuditLog.Action.INVENTORY_ADJUSTED,
            target_id=str(inventory_id),
        )
        self.assertEqual(event.metadata, {"movement_id": movement.pk})
        self.assertEqual(movement.quantity_delta, 5)
        self.assertEqual(movement.reason, "Verified physical count")

    def test_order_status_and_idempotent_payment_auditing(self):
        product = Product.objects.create(
            name="Audited Order Product",
            sku="AUDITED-ORDER-001",
            price="20.00",
        )
        warehouse = Warehouse.objects.create(
            name="Audited Order Warehouse",
            location="East",
        )
        Inventory.objects.create(
            product=product,
            warehouse=warehouse,
            quantity=10,
        )
        order_response = self.client.post(
            reverse("order-list"),
            {
                "items": [
                    {"product": product.pk, "warehouse": warehouse.pk, "quantity": 1}
                ]
            },
            format="json",
        )
        self.assertEqual(order_response.status_code, status.HTTP_201_CREATED)
        order_id = order_response.json()["id"]
        order_event = AuditLog.objects.get(
            action=AuditLog.Action.ORDER_CREATED,
            target_id=str(order_id),
        )
        self.assertEqual(order_event.metadata, {"item_count": 1})

        pay_url = reverse("order-pay", args=(order_id,))
        first_payment = self.client.post(pay_url, {}, format="json")
        second_payment = self.client.post(pay_url, {}, format="json")
        self.assertEqual(first_payment.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_payment.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(order_id=order_id)
        payment_events = AuditLog.objects.filter(
            action=AuditLog.Action.PAYMENT_SUCCEEDED,
            target_id=str(order_id),
        )
        self.assertEqual(payment_events.count(), 1)
        self.assertEqual(
            payment_events.get().metadata,
            {"payment_id": payment.pk, "provider": "mock", "amount": "20.00"},
        )
        history = OrderStatusHistory.objects.get(
            order_id=order_id,
            from_status=Order.Status.PENDING,
        )
        status_event = AuditLog.objects.get(
            action=AuditLog.Action.ORDER_STATUS_CHANGED,
            target_id=str(order_id),
        )
        self.assertEqual(status_event.metadata, {"status_history_id": history.pk})
