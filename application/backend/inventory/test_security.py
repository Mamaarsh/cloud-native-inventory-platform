from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    AuditLog,
    Inventory,
    Notification,
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    Product,
    Warehouse,
)


class DjangoAdminWorkflowSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(
            username="security-superuser",
            email="security-superuser@example.com",
            password="Admin-security-password-4821!",
        )
        cls.product = Product.objects.create(
            name="Admin Security Product",
            sku="ADMIN-SECURITY-001",
            price="10.00",
        )
        cls.other_product = Product.objects.create(
            name="Other Admin Security Product",
            sku="ADMIN-SECURITY-002",
            price="12.00",
        )
        cls.warehouse = Warehouse.objects.create(
            name="Admin Security Warehouse",
            location="North",
        )
        cls.other_warehouse = Warehouse.objects.create(
            name="Other Admin Security Warehouse",
            location="South",
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_admin_inventory_creation_cannot_set_unaudited_stock(self):
        response = self.client.post(
            reverse("admin:inventory_inventory_add"),
            {
                "product": self.product.pk,
                "warehouse": self.warehouse.pk,
                "quantity": 500,
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        inventory = Inventory.objects.get(
            product=self.product,
            warehouse=self.warehouse,
        )
        self.assertEqual(inventory.quantity, 0)

    def test_admin_inventory_change_cannot_replace_identity_or_quantity(self):
        inventory = Inventory.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=7,
        )

        response = self.client.post(
            reverse("admin:inventory_inventory_change", args=(inventory.pk,)),
            {
                "product": self.other_product.pk,
                "warehouse": self.other_warehouse.pk,
                "quantity": 999,
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        inventory.refresh_from_db()
        self.assertEqual(inventory.product, self.product)
        self.assertEqual(inventory.warehouse, self.warehouse)
        self.assertEqual(inventory.quantity, 7)

    def test_admin_inventory_delete_is_disabled(self):
        inventory = Inventory.objects.create(
            product=self.product,
            warehouse=self.warehouse,
        )

        response = self.client.post(
            reverse("admin:inventory_inventory_delete", args=(inventory.pk,)),
            {"post": "yes"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Inventory.objects.filter(pk=inventory.pk).exists())

    def test_admin_cannot_delete_product_or_warehouse_with_inventory(self):
        inventory = Inventory.objects.create(
            product=self.product,
            warehouse=self.warehouse,
        )

        product_response = self.client.post(
            reverse("admin:inventory_product_delete", args=(self.product.pk,)),
            {"post": "yes"},
        )
        warehouse_response = self.client.post(
            reverse(
                "admin:inventory_warehouse_delete",
                args=(self.warehouse.pk,),
            ),
            {"post": "yes"},
        )

        self.assertEqual(
            product_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            warehouse_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.assertTrue(
            Warehouse.objects.filter(pk=self.warehouse.pk).exists()
        )
        self.assertTrue(Inventory.objects.filter(pk=inventory.pk).exists())

    def test_admin_can_still_delete_unused_product_with_audit_event(self):
        unused_product = Product.objects.create(
            name="Unused Admin Product",
            sku="ADMIN-SECURITY-UNUSED",
            price="4.00",
        )

        response = self.client.post(
            reverse(
                "admin:inventory_product_delete",
                args=(unused_product.pk,),
            ),
            {"post": "yes"},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertFalse(
            Product.objects.filter(pk=unused_product.pk).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.PRODUCT_DELETED,
                target_id=str(unused_product.pk),
            ).exists()
        )

    def test_server_generated_admin_models_are_read_only(self):
        request_factory = RequestFactory()
        get_request = request_factory.get("/admin/")
        get_request.user = self.superuser
        post_request = request_factory.post("/admin/")
        post_request.user = self.superuser

        for model in (OrderItem, Payment, Notification):
            with self.subTest(model=model.__name__):
                model_admin = django_admin.site._registry[model]
                self.assertFalse(model_admin.has_add_permission(post_request))
                self.assertFalse(
                    model_admin.has_change_permission(post_request)
                )
                self.assertFalse(
                    model_admin.has_delete_permission(post_request)
                )
                self.assertTrue(model_admin.has_change_permission(get_request))

    def test_existing_order_owner_and_status_are_read_only_in_admin(self):
        order = Order.objects.create(user=self.superuser)
        order_admin = django_admin.site._registry[Order]
        request = RequestFactory().get("/admin/inventory/order/")
        request.user = self.superuser

        inspection_response = self.client.get(
            reverse("admin:inventory_order_change", args=(order.pk,))
        )

        self.assertEqual(inspection_response.status_code, status.HTTP_200_OK)
        self.assertSetEqual(
            set(order_admin.get_readonly_fields(request, order)),
            {"user", "status", "created_at", "updated_at"},
        )
        self.assertFalse(order_admin.has_delete_permission(request, order))

    def test_admin_order_creation_is_disabled(self):
        order_admin = django_admin.site._registry[Order]
        request = RequestFactory().get("/admin/inventory/order/add/")
        request.user = self.superuser

        get_response = self.client.get(reverse("admin:inventory_order_add"))
        post_response = self.client.post(
            reverse("admin:inventory_order_add"),
            {"user": self.superuser.pk, "_save": "Save"},
        )

        self.assertFalse(order_admin.has_add_permission(request))
        self.assertEqual(get_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(post_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Order.objects.exists())


class AuthoritativeOrderCreationAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name="Admin")
        cls.user = get_user_model().objects.create_user(
            username="authoritative-order-admin",
        )
        cls.user.groups.add(admin_group)
        cls.product = Product.objects.create(
            name="Authoritative Order Product",
            sku="AUTHORITATIVE-ORDER-001",
            price="15.00",
        )
        cls.warehouse = Warehouse.objects.create(
            name="Authoritative Order Warehouse",
            location="Central",
        )

    def setUp(self):
        self.client.force_authenticate(self.user)
        self.inventory = Inventory.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=5,
        )

    def test_normal_api_order_creation_remains_unaffected(self):
        response = self.client.post(
            reverse("order-list"),
            {
                "items": [
                    {
                        "product": self.product.pk,
                        "warehouse": self.warehouse.pk,
                        "quantity": 2,
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(pk=response.json()["id"])
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.items.count(), 1)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 3)
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                from_status__isnull=True,
                to_status=Order.Status.PENDING,
            ).exists()
        )


class DeterministicOrderPaginationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name="Admin")
        cls.user = get_user_model().objects.create_user(
            username="ordered-api-admin",
        )
        cls.user.groups.add(admin_group)
        cls.first_order = Order.objects.create(user=cls.user)
        cls.second_order = Order.objects.create(user=cls.user)

    def test_default_order_list_is_newest_first_and_deterministic(self):
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(reverse("order-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [order["id"] for order in response.json()["results"]],
            [self.second_order.pk, self.first_order.pk],
        )
