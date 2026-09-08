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
                "view_auditlog",
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


class UserRegistrationAPITests(APITestCase):
    def setUp(self):
        self.url = reverse("users:register")
        self.password = "Cedar-Harbor-4821!"
        self.payload = {
            "username": "newuser",
            "email": "user@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": self.password,
            "password_confirm": self.password,
        }

    def register(self, **overrides):
        payload = {**self.payload, **overrides}
        return self.client.post(self.url, payload, format="json")

    def test_valid_registration_returns_created(self):
        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {
                "detail": (
                    "Account created and awaiting administrator approval."
                )
            },
        )

    def test_registration_persists_user(self):
        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(username="newuser")
        self.assertEqual(user.email, "user@example.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")

    def test_registration_hashes_password(self):
        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(username="newuser")
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))

    def test_registered_user_is_inactive_and_not_privileged(self):
        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(username="newuser")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_registered_user_has_no_groups_or_direct_permissions(self):
        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(username="newuser")
        self.assertFalse(user.groups.exists())
        self.assertFalse(user.user_permissions.exists())

    def test_password_mismatch_is_rejected(self):
        response = self.register(password_confirm="Different-password-4821!")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.json())
        self.assertFalse(
            get_user_model().objects.filter(username="newuser").exists()
        )

    def test_weak_password_is_rejected_by_django_validators(self):
        response = self.register(
            password="password",
            password_confirm="password",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.json())
        self.assertGreater(len(response.json()["password"]), 0)

    def test_duplicate_username_is_rejected(self):
        get_user_model().objects.create_user(
            username="newuser",
            password="Existing-user-password-4281!",
        )

        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.json())

    def test_invalid_email_is_rejected(self):
        response = self.register(email="not-an-email")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json())
        self.assertFalse(
            get_user_model().objects.filter(username="newuser").exists()
        )

    def test_persian_names_are_preserved(self):
        response = self.register(
            first_name="محمد",
            last_name="جعفری",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(username="newuser")
        self.assertEqual(user.first_name, "محمد")
        self.assertEqual(user.last_name, "جعفری")

    def test_group_assignment_attempt_is_rejected(self):
        admin_group = Group.objects.create(name="Admin")

        response = self.register(groups=[admin_group.pk])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("groups", response.json())
        self.assertFalse(
            get_user_model().objects.filter(username="newuser").exists()
        )
        self.assertFalse(admin_group.user_set.exists())

    def test_privileged_account_fields_are_rejected(self):
        response = self.register(
            is_active=True,
            is_staff=True,
            is_superuser=True,
            role="Admin",
            permissions=["inventory.change_order"],
            user_permissions=["inventory.change_user"],
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in (
            "is_active",
            "is_staff",
            "is_superuser",
            "role",
            "permissions",
            "user_permissions",
        ):
            self.assertIn(field, response.json())
        self.assertFalse(
            get_user_model().objects.filter(username="newuser").exists()
        )

    def test_inactive_registered_user_cannot_obtain_tokens(self):
        registration_response = self.register()
        self.assertEqual(
            registration_response.status_code,
            status.HTTP_201_CREATED,
        )

        response = self.client.post(
            reverse("users:token-obtain-pair"),
            {
                "username": self.payload["username"],
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.json())
        self.assertNotIn("refresh", response.json())


class AdminUserManagementAPITests(APITestCase):
    role_names = (
        "Admin",
        "Warehouse Manager",
        "Operator",
        "Auditor",
    )

    @classmethod
    def setUpTestData(cls):
        cls.groups = {
            role_name: Group.objects.create(name=role_name)
            for role_name in cls.role_names
        }
        cls.admin_password = "Admin-access-password-4821!"
        cls.admin = get_user_model().objects.create_user(
            username="application-admin",
            email="admin@example.com",
            password=cls.admin_password,
        )
        cls.admin.groups.add(cls.groups["Admin"])
        cls.pending_password = "Pending-user-password-4821!"
        cls.pending_user = get_user_model().objects.create_user(
            username="pending-user",
            email="pending@example.com",
            password=cls.pending_password,
            is_active=False,
        )
        cls.active_user = get_user_model().objects.create_user(
            username="active-user",
            email="active@example.com",
            password="Active-user-password-4821!",
        )

    def authenticate(self, user=None):
        authenticated_user = user or self.admin
        access_token = RefreshToken.for_user(
            authenticated_user
        ).access_token
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

    def detail_url(self, user):
        return reverse(
            "users:admin-user-detail",
            kwargs={"pk": user.pk},
        )

    def assign_role(self, role_name, user=None):
        managed_user = user or self.active_user
        self.authenticate()
        return self.client.patch(
            self.detail_url(managed_user),
            {"role": role_name},
            format="json",
        )

    def test_admin_can_list_users(self):
        self.authenticate()

        response = self.client.get(reverse("users:admin-user-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.json())
        usernames = {
            item["username"] for item in response.json()["results"]
        }
        self.assertIn(self.admin.username, usernames)
        self.assertIn(self.pending_user.username, usernames)
        pending_result = next(
            item
            for item in response.json()["results"]
            if item["username"] == self.pending_user.username
        )
        self.assertSetEqual(
            set(pending_result),
            {
                "id",
                "username",
                "email",
                "first_name",
                "last_name",
                "is_active",
                "groups",
                "date_joined",
                "is_staff",
            },
        )

    def test_admin_can_filter_pending_users(self):
        self.authenticate()

        response = self.client.get(
            reverse("users:admin-user-list"),
            {"status": "pending"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertGreater(len(results), 0)
        self.assertTrue(all(not item["is_active"] for item in results))
        self.assertNotIn(
            self.active_user.username,
            {item["username"] for item in results},
        )

    def test_registered_account_appears_in_pending_results(self):
        registration_response = self.client.post(
            reverse("users:register"),
            {
                "username": "awaiting-approval",
                "email": "awaiting@example.com",
                "first_name": "Awaiting",
                "last_name": "Approval",
                "password": "Awaiting-approval-password-4821!",
                "password_confirm": "Awaiting-approval-password-4821!",
            },
            format="json",
        )
        self.assertEqual(
            registration_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.authenticate()

        response = self.client.get(
            reverse("users:admin-user-list"),
            {"status": "pending"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            "awaiting-approval",
            {item["username"] for item in response.json()["results"]},
        )

    def test_admin_can_activate_pending_account(self):
        self.authenticate()

        response = self.client.patch(
            self.detail_url(self.pending_user),
            {"is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["is_active"])
        self.pending_user.refresh_from_db()
        self.assertTrue(self.pending_user.is_active)
        self.assertFalse(self.pending_user.groups.exists())

    def test_activated_account_can_obtain_jwt_credentials(self):
        self.authenticate()
        activation_response = self.client.patch(
            self.detail_url(self.pending_user),
            {"is_active": True},
            format="json",
        )
        self.assertEqual(
            activation_response.status_code,
            status.HTTP_200_OK,
        )
        self.client.credentials()

        response = self.client.post(
            reverse("users:token-obtain-pair"),
            {
                "username": self.pending_user.username,
                "password": self.pending_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())

    def test_admin_can_assign_operator(self):
        response = self.assign_role("Operator")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["groups"], ["Operator"])

    def test_admin_can_assign_warehouse_manager(self):
        response = self.assign_role("Warehouse Manager")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["groups"],
            ["Warehouse Manager"],
        )

    def test_admin_can_assign_auditor(self):
        response = self.assign_role("Auditor")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["groups"], ["Auditor"])

    def test_admin_can_assign_admin(self):
        response = self.assign_role("Admin")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["groups"], ["Admin"])

    def test_unknown_role_is_rejected(self):
        response = self.assign_role("Owner")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.json())
        self.active_user.refresh_from_db()
        self.assertFalse(self.active_user.groups.exists())

    def test_role_assignment_reuses_groups_and_replaces_existing_role(self):
        operator_group = self.groups["Operator"]
        original_group_count = Group.objects.count()
        self.active_user.groups.add(self.groups["Warehouse Manager"])

        response = self.assign_role("Operator")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Group.objects.count(), original_group_count)
        self.assertTrue(
            self.active_user.groups.filter(pk=operator_group.pk).exists()
        )
        self.assertSetEqual(
            set(
                self.active_user.groups.filter(
                    name__in=self.role_names
                ).values_list("name", flat=True)
            ),
            {"Operator"},
        )

    def test_combined_approval_and_role_assignment_is_atomic(self):
        self.authenticate()

        response = self.client.patch(
            self.detail_url(self.pending_user),
            {"is_active": True, "role": "Operator"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending_user.refresh_from_db()
        self.assertTrue(self.pending_user.is_active)
        self.assertSetEqual(
            set(self.pending_user.groups.values_list("name", flat=True)),
            {"Operator"},
        )

    def test_combined_update_rolls_back_if_role_is_not_configured(self):
        self.groups["Operator"].delete()
        self.authenticate()

        response = self.client.patch(
            self.detail_url(self.pending_user),
            {"is_active": True, "role": "Operator"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.json())
        self.pending_user.refresh_from_db()
        self.assertFalse(self.pending_user.is_active)
        self.assertFalse(self.pending_user.groups.exists())

    def test_non_admin_roles_are_forbidden(self):
        for role_name in ("Warehouse Manager", "Operator", "Auditor"):
            with self.subTest(role=role_name):
                user = get_user_model().objects.create_user(
                    username=f"non-admin-{role_name}",
                    password="Non-admin-password-4821!",
                )
                user.groups.add(self.groups[role_name])
                self.authenticate(user)

                response = self.client.get(
                    reverse("users:admin-user-list")
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_anonymous_request_is_rejected(self):
        response = self.client.get(reverse("users:admin-user-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_superuser_without_admin_group_is_forbidden(self):
        superuser = get_user_model().objects.create_superuser(
            username="unassigned-superuser",
            email="unassigned-superuser@example.com",
            password="Superuser-password-4821!",
        )
        self.authenticate(superuser)

        response = self.client.get(reverse("users:admin-user-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_protected_privilege_fields_are_rejected(self):
        self.authenticate()

        response = self.client.patch(
            self.detail_url(self.active_user),
            {"is_staff": True, "is_superuser": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_staff", response.json())
        self.assertIn("is_superuser", response.json())
        self.active_user.refresh_from_db()
        self.assertFalse(self.active_user.is_staff)
        self.assertFalse(self.active_user.is_superuser)

    def test_arbitrary_groups_cannot_be_injected(self):
        arbitrary_group = Group.objects.create(name="Untrusted Group")
        self.authenticate()

        response = self.client.patch(
            self.detail_url(self.active_user),
            {"groups": [arbitrary_group.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("groups", response.json())
        self.assertFalse(self.active_user.groups.exists())

    def test_superuser_account_management_is_rejected(self):
        superuser = get_user_model().objects.create_superuser(
            username="django-superuser",
            email="superuser@example.com",
            password="Superuser-password-4821!",
        )
        self.authenticate()

        response = self.client.patch(
            self.detail_url(superuser),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        superuser.refresh_from_db()
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_superuser)

    def test_admin_cannot_deactivate_own_account(self):
        self.authenticate()

        response = self.client.patch(
            self.detail_url(self.admin),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_cannot_remove_own_admin_role(self):
        self.authenticate()

        response = self.client.patch(
            self.detail_url(self.admin),
            {"role": "Operator"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(self.admin.groups.filter(name="Admin").exists())
        self.assertFalse(self.admin.groups.filter(name="Operator").exists())


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

    def test_deactivated_user_cannot_refresh_or_use_existing_tokens(self):
        refresh_token = RefreshToken.for_user(self.user)
        self.user.is_active = False
        self.user.save(update_fields=("is_active",))

        refresh_response = self.client.post(
            reverse("users:token-refresh"),
            {"refresh": str(refresh_token)},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}",
        )
        authenticated_response = self.client.get(reverse("users:me"))

        self.assertEqual(
            refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertNotIn("access", refresh_response.json())
        self.assertEqual(
            authenticated_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


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
