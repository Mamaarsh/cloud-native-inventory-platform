from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

ROLE_PERMISSIONS = {
    "Admin": None,
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

class Command(BaseCommand):
    help = "Create or update the inventory authorization groups."
    @transaction.atomic
    def handle(self, *args, **options):
        inventory_permissions = Permission.objects.filter(
            content_type__app_label="inventory"
        )
        permissions_by_codename = {
            permission.codename: permission
            for permission in inventory_permissions
        }
        required_codenames = set().union(
            *(
                codenames
                for codenames in ROLE_PERMISSIONS.values()
                if codenames is not None
            )
        )
        missing_codenames = required_codenames - permissions_by_codename.keys()
        if missing_codenames:
            missing = ", ".join(sorted(missing_codenames))
            raise CommandError(
                f"Missing inventory permissions: {missing}. Run migrations first."
            )
        for group_name, codenames in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if codenames is None:
                permissions = inventory_permissions
            else:
                permissions = [
                    permissions_by_codename[codename]
                    for codename in codenames
                ]
            group.permissions.set(permissions)
            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(f"{action} group: {group_name}")
            )