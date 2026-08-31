from unittest.mock import patch

from django.db import OperationalError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

class HealthCheckTests(APITestCase):
    def test_liveness_returns_ok_without_database_query(self):
        with self.assertNumQueries(0):
            response = self.client.get(reverse("health-live"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_returns_ready_when_database_is_available(self):
        response = self.client.get(reverse("health-ready"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "status": "ready",
                "database": "ok",
            },
        )

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
                "database": "unavailable",
            },
        )
        mocked_cursor.assert_called_once_with()
