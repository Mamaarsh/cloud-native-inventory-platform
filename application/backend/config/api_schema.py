from rest_framework import serializers


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)


class JWTErrorResponseSerializer(DetailResponseSerializer):
    code = serializers.CharField(read_only=True)


class LivenessResponseSerializer(serializers.Serializer):
    status = serializers.CharField(
        read_only=True,
        help_text="Always `ok` when the application process can respond.",
    )


class DatabaseChecksSerializer(serializers.Serializer):
    database = serializers.CharField(
        read_only=True,
        help_text="`ok` or `unavailable`.",
    )


class ReadinessResponseSerializer(serializers.Serializer):
    status = serializers.CharField(
        read_only=True,
        help_text="`ready` or `not_ready`.",
    )
    checks = DatabaseChecksSerializer(read_only=True)


class DependencyChecksSerializer(DatabaseChecksSerializer):
    redis = serializers.CharField(
        read_only=True,
        help_text="`ok` or `unavailable`.",
    )


class DependencyHealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField(
        read_only=True,
        help_text="`healthy`, `degraded`, or `unhealthy`.",
    )
    checks = DependencyChecksSerializer(read_only=True)


VALIDATION_ERROR_SCHEMA = {
    "type": "object",
    "additionalProperties": {
        "oneOf": (
            {"type": "string"},
            {"type": "array", "items": {"type": "string"}},
            {"type": "object"},
        ),
    },
}

EMPTY_OBJECT_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
    "maxProperties": 0,
}
