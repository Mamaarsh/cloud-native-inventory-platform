from rest_framework.permissions import BasePermission, SAFE_METHODS

ADMIN = "Admin"
WAREHOUSE_MANAGER = "Warehouse Manager"
OPERATOR = "Operator"
AUDITOR = "Auditor"

APPLICATION_ROLES = (
    ADMIN,
    WAREHOUSE_MANAGER,
    OPERATOR,
    AUDITOR,
)


def _has_any_role(user, *role_names, allow_superuser=True):
    if not user or not user.is_authenticated:
        return False
    if allow_superuser and user.is_superuser:
        return True
    return user.groups.filter(name__in=role_names).exists()


class _IsRole(BasePermission):
    role_name = None
    allow_superuser = True

    def has_permission(self, request, view):
        return _has_any_role(
            request.user,
            self.role_name,
            allow_superuser=self.allow_superuser,
        )


class IsAdmin(_IsRole):
    role_name = ADMIN


class IsApplicationAdmin(_IsRole):
    role_name = ADMIN
    allow_superuser = False


class IsWarehouseManager(_IsRole):
    role_name = WAREHOUSE_MANAGER

class IsOperator(_IsRole):
    role_name = OPERATOR

class IsAuditor(_IsRole):
    role_name = AUDITOR

class ProductPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _has_any_role(request.user, ADMIN)

class WarehousePermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return _has_any_role(
                request.user,
                ADMIN,
                WAREHOUSE_MANAGER,
                OPERATOR,
                AUDITOR,
            )
        return _has_any_role(request.user, ADMIN)

class InventoryPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return _has_any_role(
                request.user,
                ADMIN,
                WAREHOUSE_MANAGER,
                OPERATOR,
                AUDITOR,
            )
        if request.method == "POST":
            return _has_any_role(
                request.user,
                ADMIN,
                WAREHOUSE_MANAGER,
                OPERATOR,
            )
        if request.method in {"PUT", "PATCH"}:
            return _has_any_role(request.user, ADMIN, WAREHOUSE_MANAGER)
        if request.method == "DELETE":
            return _has_any_role(request.user, ADMIN)
        return False

class OrderPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return _has_any_role(
                request.user,
                ADMIN,
                WAREHOUSE_MANAGER,
                OPERATOR,
                AUDITOR,
            )
        if request.method in {"PUT", "PATCH"}:
            return _has_any_role(request.user, ADMIN, WAREHOUSE_MANAGER)
        if request.method in {"POST", "DELETE"}:
            return _has_any_role(request.user, ADMIN)
        return False

class OrderStatusPermission(BasePermission):
    warehouse_manager_transitions = {
        ("pending", "processing"),
        ("processing", "shipped"),
    }

    def has_permission(self, request, view):
        return _has_any_role(request.user, ADMIN, WAREHOUSE_MANAGER)

    def has_object_permission(self, request, view, obj):
        if _has_any_role(request.user, ADMIN):
            return True
        return (
            obj.status,
            request.data.get("status"),
        ) in self.warehouse_manager_transitions
