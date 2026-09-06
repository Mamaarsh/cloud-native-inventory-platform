from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import User
from .permissions import IsApplicationAdmin
from .serializers import (
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    PasswordChangeSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


class UserRegistrationView(GenericAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer
    http_method_names = ("post", "options")

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Account created and awaiting administrator approval."},
            status=status.HTTP_201_CREATED,
        )


class CurrentUserView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        return self.request.user


class PasswordChangeView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PasswordChangeSerializer
    http_method_names = ("post", "options")

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="status",
            type=str,
            location=OpenApiParameter.QUERY,
            description=(
                "Filter accounts by activation state: pending or active."
            ),
            enum=("pending", "active"),
        ),
    ],
)
class AdminUserListView(ListAPIView):
    permission_classes = (IsApplicationAdmin,)
    serializer_class = AdminUserSerializer
    http_method_names = ("get", "head", "options")

    def get_queryset(self):
        queryset = User.objects.prefetch_related("groups").order_by(
            "-date_joined",
            "id",
        )
        status_filter = self.request.query_params.get("status")
        if status_filter is None:
            return queryset
        if status_filter == "pending":
            return queryset.filter(is_active=False)
        if status_filter == "active":
            return queryset.filter(is_active=True)
        raise ValidationError(
            {"status": "Status must be either pending or active."}
        )


class AdminUserDetailView(GenericAPIView):
    permission_classes = (IsApplicationAdmin,)
    queryset = User.objects.prefetch_related("groups")
    serializer_class = AdminUserUpdateSerializer
    http_method_names = ("get", "patch", "head", "options")

    @extend_schema(responses=AdminUserSerializer)
    def get(self, request, *args, **kwargs):
        return Response(AdminUserSerializer(self.get_object()).data)

    @extend_schema(
        request=AdminUserUpdateSerializer,
        responses=AdminUserSerializer,
    )
    def patch(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()
        return Response(AdminUserSerializer(updated_user).data)
