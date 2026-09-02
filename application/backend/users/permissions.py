from rest_framework.permissions import BasePermission, SAFE_METHODS

ADMIN = "Admin"
WAREHOUSE_MANAGER = "Warehouse Manager"
OPERATOR = "Operator"
AUDITOR = "Auditor"

def _has_any_role(user, *role_names):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=role_names).exists()

class _IsRole(BasePermission):
    role_name = None

    def has_permission(self, request, view):
        return _has_any_role(request.user, self.role_name)

class IsAdmin(_IsRole):
    role_name = ADMIN

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