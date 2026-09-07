from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from inventory.models import AuditLog
from inventory.services.audit import record_audit_event
from .permissions import APPLICATION_ROLES
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    def save_model(self, request, obj, form, change):
        previous = User.objects.filter(pk=obj.pk).first() if change else None
        previous_roles = (
            list(
                previous.groups.filter(name__in=APPLICATION_ROLES)
                .order_by("name")
                .values_list("name", flat=True)
            )
            if previous
            else []
        )
        previous_password = previous.password if previous else None
        previous_is_active = previous.is_active if previous else None
        request._audit_previous_user_roles = previous_roles

        super().save_model(request, obj, form, change)

        if not change:
            record_audit_event(
                actor=request.user,
                action=AuditLog.Action.USER_CREATED,
                target_type=AuditLog.TargetType.USER,
                target_id=obj.pk,
                target_label=obj.username,
            )
            return

        if previous_is_active != obj.is_active:
            record_audit_event(
                actor=request.user,
                action=(
                    AuditLog.Action.USER_ACTIVATED
                    if obj.is_active
                    else AuditLog.Action.USER_DEACTIVATED
                ),
                target_type=AuditLog.TargetType.USER,
                target_id=obj.pk,
                target_label=obj.username,
            )
        if previous_password != obj.password:
            record_audit_event(
                actor=request.user,
                action=AuditLog.Action.USER_PASSWORD_CHANGED,
                target_type=AuditLog.TargetType.USER,
                target_id=obj.pk,
                target_label=obj.username,
            )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if not change:
            return
        previous_roles = getattr(request, "_audit_previous_user_roles", [])
        current_roles = list(
            form.instance.groups.filter(name__in=APPLICATION_ROLES)
            .order_by("name")
            .values_list("name", flat=True)
        )
        if previous_roles == current_roles:
            return
        record_audit_event(
            actor=request.user,
            action=AuditLog.Action.USER_ROLE_CHANGED,
            target_type=AuditLog.TargetType.USER,
            target_id=form.instance.pk,
            target_label=form.instance.username,
            metadata={
                "old_role": ", ".join(previous_roles) or None,
                "new_role": ", ".join(current_roles) or None,
            },
        )
