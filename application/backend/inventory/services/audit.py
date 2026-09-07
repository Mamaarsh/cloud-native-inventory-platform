import json
from django.core.exceptions import ValidationError
from inventory.models import AuditLog

MAX_METADATA_BYTES = 8_192

ALLOWED_METADATA_FIELDS = {
    AuditLog.Action.USER_CREATED: set(),
    AuditLog.Action.USER_REGISTERED: set(),
    AuditLog.Action.USER_ACTIVATED: set(),
    AuditLog.Action.USER_DEACTIVATED: set(),
    AuditLog.Action.USER_ROLE_CHANGED: {"old_role", "new_role"},
    AuditLog.Action.USER_PASSWORD_CHANGED: set(),
    AuditLog.Action.PRODUCT_CREATED: set(),
    AuditLog.Action.PRODUCT_UPDATED: {"changes", "image_changed"},
    AuditLog.Action.PRODUCT_ACTIVATED: {"changes", "image_changed"},
    AuditLog.Action.PRODUCT_DEACTIVATED: {"changes", "image_changed"},
    AuditLog.Action.PRODUCT_DELETED: set(),
    AuditLog.Action.WAREHOUSE_CREATED: set(),
    AuditLog.Action.WAREHOUSE_UPDATED: {"changes"},
    AuditLog.Action.WAREHOUSE_DELETED: set(),
    AuditLog.Action.INVENTORY_CREATED: set(),
    AuditLog.Action.INVENTORY_ADJUSTED: {"movement_id"},
    AuditLog.Action.INVENTORY_DELETED: set(),
    AuditLog.Action.ORDER_CREATED: {"item_count"},
    AuditLog.Action.ORDER_STATUS_CHANGED: {"status_history_id"},
    AuditLog.Action.PAYMENT_SUCCEEDED: {
        "payment_id",
        "provider",
        "amount",
    },
}

SENSITIVE_KEY_PARTS = {
    "authorization",
    "credential",
    "jwt",
    "password",
    "secret",
    "session",
    "token",
}

ALLOWED_CHANGE_FIELDS = {
    AuditLog.Action.PRODUCT_UPDATED: {"name", "sku", "price", "is_active"},
    AuditLog.Action.PRODUCT_ACTIVATED: {"name", "sku", "price", "is_active"},
    AuditLog.Action.PRODUCT_DEACTIVATED: {"name", "sku", "price", "is_active"},
    AuditLog.Action.WAREHOUSE_UPDATED: {"name", "location"},
}

def _contains_sensitive_key(value):
    if isinstance(value, dict):
        for key, nested_value in value.items():
            normalized_key = str(key).lower()
            if any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
                return True
            if _contains_sensitive_key(nested_value):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_sensitive_key(item) for item in value)
    return False

def _validate_metadata(action, metadata):
    if not isinstance(metadata, dict):
        raise ValidationError("Audit metadata must be a JSON object.")
    allowed_fields = ALLOWED_METADATA_FIELDS[action]
    unsupported_fields = set(metadata).difference(allowed_fields)
    if unsupported_fields:
        raise ValidationError(
            "Unsupported audit metadata fields: "
            + ", ".join(sorted(unsupported_fields))
        )
    if _contains_sensitive_key(metadata):
        raise ValidationError("Sensitive values cannot be stored in audit metadata.")
    changes = metadata.get("changes")
    if changes is not None:
        if not isinstance(changes, dict):
            raise ValidationError("Audit changes must be a JSON object.")
        allowed_change_fields = ALLOWED_CHANGE_FIELDS.get(action, set())
        unsupported_change_fields = set(changes).difference(
            allowed_change_fields
        )
        if unsupported_change_fields:
            raise ValidationError(
                "Unsupported audited change fields: "
                + ", ".join(sorted(unsupported_change_fields))
            )
        for field, values in changes.items():
            if not isinstance(values, dict) or set(values) != {
                "before",
                "after",
            }:
                raise ValidationError(
                    f"Audit change for '{field}' must contain before and after."
                )
    if "image_changed" in metadata and metadata["image_changed"] is not True:
        raise ValidationError("image_changed must be true when present.")
    try:
        serialized = json.dumps(metadata, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Audit metadata must be JSON serializable.") from exc
    if len(serialized.encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValidationError("Audit metadata is too large.")

def record_audit_event(
    *,
    actor,
    action,
    target_type,
    target_id,
    target_label,
    metadata=None,
):
    valid_actions = {value for value, _ in AuditLog.Action.choices}
    valid_target_types = {value for value, _ in AuditLog.TargetType.choices}
    if action not in valid_actions:
        raise ValidationError("Unsupported audit action.")
    if target_type not in valid_target_types:
        raise ValidationError("Unsupported audit target type.")
    normalized_target_id = str(target_id)
    normalized_target_label = str(target_label).strip()
    if not normalized_target_id or len(normalized_target_id) > 100:
        raise ValidationError("Audit target ID is invalid.")
    if not normalized_target_label or len(normalized_target_label) > 255:
        raise ValidationError("Audit target label is invalid.")
    safe_metadata = {} if metadata is None else metadata
    _validate_metadata(action, safe_metadata)
    normalized_actor = (
        actor if actor is not None and actor.is_authenticated else None
    )
    return AuditLog.objects.create(
        actor=normalized_actor,
        action=action,
        target_type=target_type,
        target_id=normalized_target_id,
        target_label=normalized_target_label,
        metadata=safe_metadata,
    )