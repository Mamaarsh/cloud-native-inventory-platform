from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

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