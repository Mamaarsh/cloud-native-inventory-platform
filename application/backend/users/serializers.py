from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from .models import User
from .permissions import ADMIN, APPLICATION_ROLES


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "groups",
            "is_staff",
        )
        read_only_fields = (
            "username",
            "groups",
            "is_staff",
        )


class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, allow_blank=False)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    protected_fields = frozenset(
        {
            "groups",
            "role",
            "is_staff",
            "is_superuser",
            "is_active",
            "permissions",
            "user_permissions",
        }
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        )
        extra_kwargs = {
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        submitted_protected_fields = self.protected_fields.intersection(
            self.initial_data
        )
        if submitted_protected_fields:
            raise serializers.ValidationError(
                {
                    field: "This field cannot be set during registration."
                    for field in sorted(submitted_protected_fields)
                }
            )

        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        candidate_user = User(
            username=attrs["username"],
            email=attrs["email"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"password": list(exc.messages)}
            ) from exc

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(
            **validated_data,
            password=password,
            is_active=False,
            is_staff=False,
            is_superuser=False,
        )


class AdminUserSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "groups",
            "date_joined",
            "is_staff",
        )
        read_only_fields = fields


class AdminUserUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    role = serializers.ChoiceField(
        choices=APPLICATION_ROLES,
        required=False,
    )

    allowed_fields = frozenset({"is_active", "role"})

    def validate(self, attrs):
        unsupported_fields = set(self.initial_data).difference(
            self.allowed_fields
        )
        if unsupported_fields:
            raise serializers.ValidationError(
                {
                    field: "This field cannot be changed through this endpoint."
                    for field in sorted(unsupported_fields)
                }
            )
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        user = User.objects.select_for_update().get(pk=instance.pk)
        requesting_user = self.context["request"].user

        if user.is_superuser:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "Django superuser accounts cannot be managed through "
                        "this endpoint."
                    )
                }
            )

        if user.pk == requesting_user.pk:
            if validated_data.get("is_active") is False:
                raise serializers.ValidationError(
                    {"is_active": "You cannot deactivate your own account."}
                )
            if (
                "role" in validated_data
                and validated_data["role"] != ADMIN
            ):
                raise serializers.ValidationError(
                    {"role": "You cannot remove your own Admin role."}
                )

        if "is_active" in validated_data:
            user.is_active = validated_data["is_active"]
            user.save(update_fields=("is_active",))

        role_name = validated_data.get("role")
        if role_name is not None:
            try:
                role_group = Group.objects.get(name=role_name)
            except Group.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {
                        "role": (
                            "This application role is not configured. Run "
                            "create_roles first."
                        )
                    }
                ) from exc

            current_role_groups = user.groups.filter(
                name__in=APPLICATION_ROLES
            )
            user.groups.remove(*current_role_groups)
            user.groups.add(role_group)

        return user

    def create(self, validated_data):
        raise NotImplementedError


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )

        try:
            validate_password(
                attrs["new_password"],
                user=self.context["request"].user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": list(exc.messages)}
            ) from exc

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=("password",))
        return user
