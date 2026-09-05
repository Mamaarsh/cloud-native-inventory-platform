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

    def authenticate(self):
        access_token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("users:me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_access_me(self):
        self.authenticate()
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

    def test_authenticated_user_can_update_profile(self):
        self.authenticate()

        response = self.client.patch(
            reverse("users:me"),
            {
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["first_name"], "Updated")
        self.assertEqual(response.json()["last_name"], "Name")
        self.assertEqual(response.json()["email"], "updated@example.com")

    def test_profile_update_persists_in_database(self):
        self.authenticate()

        response = self.client.patch(
            reverse("users:me"),
            {"first_name": "Persistent"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Persistent")

    def test_profile_update_requires_authentication(self):
        response = self.client.patch(
            reverse("users:me"),
            {"first_name": "Unauthorized"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_update_cannot_change_groups(self):
        self.authenticate()
        original_group_ids = set(self.user.groups.values_list("id", flat=True))

        response = self.client.patch(
            reverse("users:me"),
            {"groups": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertSetEqual(
            set(self.user.groups.values_list("id", flat=True)),
            original_group_ids,
        )

    def test_profile_update_cannot_change_staff_status(self):
        self.authenticate()

        response = self.client.patch(
            reverse("users:me"),
            {"is_staff": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_staff)

    def test_profile_update_accepts_persian_names(self):
        self.authenticate()

        response = self.client.patch(
            reverse("users:me"),
            {
                "first_name": "مریم",
                "last_name": "احمدی",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["first_name"], "مریم")
        self.assertEqual(response.json()["last_name"], "احمدی")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "مریم")
        self.assertEqual(self.user.last_name, "احمدی")

    def test_profile_update_rejects_invalid_email(self):
        self.authenticate()

        response = self.client.patch(
            reverse("users:me"),
            {"email": "not-an-email"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json())

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


class PasswordChangeAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.current_password = "Current-secure-password-123!"
        cls.new_password = "Violet-Cascade-8462!"
        cls.user = get_user_model().objects.create_user(
            username="password-user",
            email="password-user@example.com",
            password=cls.current_password,
            is_staff=True,
        )
        cls.group = Group.objects.create(name="Password Test Group")
        cls.user.groups.add(cls.group)

    def authenticate(self):
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}",
        )
        return refresh_token

    def change_password(self, **overrides):
        payload = {
            "current_password": self.current_password,
            "new_password": self.new_password,
            "new_password_confirm": self.new_password,
        }
        payload.update(overrides)
        return self.client.post(
            reverse("users:change-password"),
            payload,
            format="json",
        )

    def test_authenticated_user_can_change_password(self):
        self.authenticate()

        response = self.change_password()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {"detail": "Password changed successfully."},
        )

    def test_new_password_is_persisted_with_django_password_hashing(self):
        self.authenticate()

        response = self.change_password()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertNotEqual(self.user.password, self.new_password)

    def test_old_password_no_longer_authenticates(self):
        self.authenticate()
        self.change_password()
        self.client.credentials()

        response = self.client.post(
            reverse("users:token-obtain-pair"),
            {
                "username": self.user.username,
                "password": self.current_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_new_password_authenticates(self):
        self.authenticate()
        self.change_password()
        self.client.credentials()

        response = self.client.post(
            reverse("users:token-obtain-pair"),
            {
                "username": self.user.username,
                "password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())

    def test_wrong_current_password_is_rejected(self):
        self.authenticate()

        response = self.change_password(current_password="wrong-password")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["current_password"],
            ["Current password is incorrect."],
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.current_password))

    def test_mismatched_confirmation_is_rejected(self):
        self.authenticate()

        response = self.change_password(
            new_password_confirm="Different-secure-password-789!",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["new_password_confirm"],
            ["New passwords do not match."],
        )

    def test_weak_password_is_rejected_by_django_validators(self):
        self.authenticate()

        response = self.change_password(
            new_password="password",
            new_password_confirm="password",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.json())
        self.assertGreater(len(response.json()["new_password"]), 0)

    def test_unauthenticated_password_change_is_rejected(self):
        response = self.change_password()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_change_another_users_password(self):
        other_password = "Other-secure-password-123!"
        other_user = get_user_model().objects.create_user(
            username="other-password-user",
            password=other_password,
        )
        self.authenticate()

        response = self.change_password(user_id=other_user.pk)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        other_user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertTrue(other_user.check_password(other_password))

    def test_password_change_preserves_rbac_and_staff_status(self):
        original_group_ids = set(self.user.groups.values_list("id", flat=True))
        self.authenticate()

        response = self.change_password(
            groups=[],
            is_staff=False,
            is_superuser=True,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertSetEqual(
            set(self.user.groups.values_list("id", flat=True)),
            original_group_ids,
        )
        self.assertTrue(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_existing_access_and_refresh_tokens_remain_usable(self):
        refresh_token = self.authenticate()

        response = self.change_password()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(reverse("users:me")).status_code,
            status.HTTP_200_OK,
        )
        self.client.credentials()
        refresh_response = self.client.post(
            reverse("users:token-refresh"),
            {"refresh": str(refresh_token)},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.json())
