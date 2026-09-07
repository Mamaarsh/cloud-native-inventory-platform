from django.test import Client, SimpleTestCase
from django.urls import reverse


class OpenAPISchemaTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client()
        response = cls.client.get(
            reverse("schema"),
            HTTP_ACCEPT="application/vnd.oai.openapi+json",
        )
        if response.status_code != 200:
            raise AssertionError(
                f"Schema endpoint returned HTTP {response.status_code}."
            )
        cls.schema = response.data

    def test_documentation_endpoints_load(self):
        for url_name in ("swagger-ui", "redoc"):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_schema_metadata_and_single_jwt_security_scheme(self):
        self.assertEqual(
            self.schema["info"]["title"],
            "Cloud Native Inventory Platform API",
        )
        security_schemes = self.schema["components"]["securitySchemes"]
        self.assertSetEqual(set(security_schemes), {"jwtAuth"})
        self.assertEqual(
            security_schemes["jwtAuth"],
            {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        )
        self.assertEqual(
            self.schema["paths"]["/api/auth/register/"]["post"]["security"],
            [{}],
        )

    def test_health_responses_are_explicitly_documented(self):
        paths = self.schema["paths"]
        liveness = paths["/api/health/live/"]["get"]
        readiness = paths["/api/health/ready/"]["get"]
        dependencies = paths["/api/health/dependencies/"]["get"]

        self.assertEqual(liveness["tags"], ["Health"])
        self.assertIn("LivenessResponse", str(liveness["responses"]["200"]))
        self.assertSetEqual(set(readiness["responses"]), {"200", "503"})
        self.assertIn(
            "ReadinessResponse",
            str(readiness["responses"]["503"]),
        )
        self.assertSetEqual(set(dependencies["responses"]), {"200", "503"})
        self.assertIn(
            "DependencyHealthResponse",
            str(dependencies["responses"]["200"]),
        )

    def test_custom_action_request_response_and_pagination_are_accurate(self):
        paths = self.schema["paths"]
        adjustment = paths["/api/v1/inventory/{id}/adjust/"]["post"]
        movements = paths["/api/v1/inventory/{id}/movements/"]["get"]
        status_history = paths["/api/v1/orders/{id}/history/"]["get"]
        payment = paths["/api/v1/orders/{id}/pay/"]["post"]

        self.assertIn(
            "InventoryAdjustmentRequest",
            str(adjustment["requestBody"]),
        )
        self.assertIn("InventoryMovement", str(adjustment["responses"]["201"]))
        self.assertIn(
            "PaginatedInventoryMovementList",
            str(movements["responses"]["200"]),
        )
        self.assertSetEqual(
            {parameter["name"] for parameter in movements["parameters"]},
            {"id", "page"},
        )
        history_schema = status_history["responses"]["200"]["content"]
        history_schema = history_schema["application/json"]["schema"]
        self.assertEqual(history_schema["type"], "array")
        self.assertSetEqual(
            {parameter["name"] for parameter in status_history["parameters"]},
            {"id"},
        )
        payment_request = payment["requestBody"]["content"]
        payment_request = payment_request["application/json"]["schema"]
        self.assertFalse(payment_request["additionalProperties"])
        self.assertEqual(payment_request["maxProperties"], 0)
        self.assertSetEqual(
            {"200", "201"}.intersection(payment["responses"]),
            {"200", "201"},
        )

    def test_business_errors_and_audit_endpoint_are_documented(self):
        paths = self.schema["paths"]
        self.assertIn("409", paths["/api/v1/products/{id}/"]["delete"]["responses"])
        self.assertIn(
            "409",
            paths["/api/v1/warehouses/{id}/"]["delete"]["responses"],
        )
        self.assertIn(
            "400",
            paths["/api/v1/orders/{id}/change-status/"]["post"]["responses"],
        )
        audit_collection = paths["/api/v1/audit-logs/"]
        self.assertSetEqual(set(audit_collection), {"get"})
        self.assertEqual(audit_collection["get"]["tags"], ["Audit"])
        self.assertIn(
            "PaginatedAuditLogList",
            str(audit_collection["get"]["responses"]["200"]),
        )

    def test_list_filter_parameters_match_supported_configuration(self):
        expected_parameters = {
            "/api/v1/products/": {"ordering", "page", "search", "sku"},
            "/api/v1/warehouses/": {
                "location",
                "ordering",
                "page",
                "search",
            },
            "/api/v1/inventory/": {
                "ordering",
                "page",
                "product",
                "search",
                "warehouse",
            },
            "/api/v1/orders/": {
                "ordering",
                "page",
                "search",
                "status",
                "user",
            },
            "/api/v1/audit-logs/": {
                "action",
                "actor",
                "ordering",
                "page",
                "search",
                "target_type",
            },
        }
        for path, expected in expected_parameters.items():
            with self.subTest(path=path):
                operation = self.schema["paths"][path]["get"]
                self.assertSetEqual(
                    {parameter["name"] for parameter in operation["parameters"]},
                    expected,
                )

    def test_product_upload_documents_multipart_binary_image(self):
        operation = self.schema["paths"]["/api/v1/products/"]["post"]
        self.assertIn("multipart/form-data", operation["requestBody"]["content"])
        product_request = self.schema["components"]["schemas"]["ProductRequest"]
        self.assertEqual(
            product_request["properties"]["image"],
            {"type": "string", "format": "binary"},
        )
