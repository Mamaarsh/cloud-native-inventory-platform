from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

class CreateRolesCommandTests(TestCase):
    role_names = (
        "Admin",
        "Warehouse Manager",
        "Operator",
        "Auditor",
    )

    def run_command(self):
        output = StringIO()
        call_command("create_roles", stdout=output)
        return output.getvalue()

    def inventory_permission_codenames(self, group_name):
        return set(
            Group.objects.get(name=group_name)
            .permissions.filter(content_type__app_label="inventory")
            .values_list("codename", flat=True)
        )

    def test_command_creates_groups(self):
        output = self.run_command()
        self.assertSetEqual(
            set(
                Group.objects.filter(name__in=self.role_names).values_list(
                    "name",
                    flat=True,
                )
            ),
            set(self.role_names),
        )
        for role_name in self.role_names:
            self.assertIn(f"Created group: {role_name}", output)

    def test_command_assigns_expected_permissions(self):
        self.run_command()
        all_inventory_permissions = set(
            Permission.objects.filter(
                content_type__app_label="inventory"
            ).values_list("codename", flat=True)
        )
        expected_permissions = {
            "Admin": all_inventory_permissions,
            "Warehouse Manager": {
                "view_product",
                "view_inventory",
                "change_inventory",
                "view_order",
                "change_order",
            },
            "Operator": {
                "view_product",
                "view_inventory",
                "add_inventory",
                "view_order",
            },
            "Auditor": {
                "view_product",
                "view_inventory",
                "view_order",
            },
        }
        for role_name, codenames in expected_permissions.items():
            self.assertSetEqual(
                self.inventory_permission_codenames(role_name),
                codenames,
            )

    def test_command_is_idempotent(self):
        self.run_command()
        output = self.run_command()
        self.assertEqual(
            Group.objects.filter(name__in=self.role_names).count(),
            len(self.role_names),
        )
        for role_name in self.role_names:
            self.assertIn(f"Updated group: {role_name}", output)

class AuthenticationAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "test-password-123"
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            email="test@example.com",
            password=cls.password,
            first_name="Test",
            last_name="User",
            is_staff=True,
        )
        group = Group.objects.create(name="inventory-managers")
        cls.user.groups.add(group)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("users:me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_access_me(self):
        access_token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        response = self.client.get(reverse("users:me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "username": "testuser",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "groups": ["inventory-managers"],
                "is_staff": True,
            },
        )

    def test_token_endpoint_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            reverse("users:token-obtain-pair"),
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())