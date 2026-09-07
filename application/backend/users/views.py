from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from config.api_schema import (
    DetailResponseSerializer,
    JWTErrorResponseSerializer,
    VALIDATION_ERROR_SCHEMA,
)
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


@extend_schema(tags=("Authentication",))
class TokenObtainPairAPIView(TokenObtainPairView):
    @extend_schema(
        summary="Obtain JWT token pair",
        responses={
            status.HTTP_200_OK: TokenObtainPairSerializer,
            status.HTTP_401_UNAUTHORIZED: JWTErrorResponseSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=("Authentication",))
class TokenRefreshAPIView(TokenRefreshView):
    @extend_schema(
        summary="Refresh JWT access token",
        responses={
            status.HTTP_200_OK: TokenRefreshSerializer,
            status.HTTP_401_UNAUTHORIZED: JWTErrorResponseSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=("Authentication",))
class UserRegistrationView(GenericAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer
    http_method_names = ("post", "options")

    @extend_schema(
        description=(
            "Creates an inactive account awaiting administrator approval. "
            "No role or JWT is issued."
        ),
        responses={
            status.HTTP_201_CREATED: DetailResponseSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=VALIDATION_ERROR_SCHEMA,
                description="Registration data failed validation.",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Account created and awaiting administrator approval."},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=("Authentication",),
    description="Retrieves or updates the authenticated user's safe profile fields.",
)
class CurrentUserView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        return self.request.user


@extend_schema(tags=("Authentication",))
class PasswordChangeView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PasswordChangeSerializer
    http_method_names = ("post", "options")

    @extend_schema(
        description=(
            "Changes the authenticated user's password after validating the "
            "current password and Django password policy."
        ),
        responses={
            status.HTTP_200_OK: DetailResponseSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=VALIDATION_ERROR_SCHEMA,
                description="Password validation failed.",
            ),
            status.HTTP_401_UNAUTHORIZED: DetailResponseSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=("Users",),
    description="Lists accounts for application administrators.",
    filters=False,
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
        OpenApiParameter(
            name="ordering",
            type=str,
            location=OpenApiParameter.QUERY,
            description=(
                "Order by a response field; prefix with `-` for descending "
                "order."
            ),
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

    @extend_schema(
        tags=("Users",),
        description="Retrieves an account for application access review.",
        responses={
            status.HTTP_200_OK: AdminUserSerializer,
            status.HTTP_401_UNAUTHORIZED: DetailResponseSerializer,
            status.HTTP_403_FORBIDDEN: DetailResponseSerializer,
            status.HTTP_404_NOT_FOUND: DetailResponseSerializer,
        },
    )
    def get(self, request, *args, **kwargs):
        return Response(AdminUserSerializer(self.get_object()).data)

    @extend_schema(
        tags=("Users",),
        description=(
            "Activates or deactivates an account and assigns its application "
            "role."
        ),
        request=AdminUserUpdateSerializer,
        responses={
            status.HTTP_200_OK: AdminUserSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=VALIDATION_ERROR_SCHEMA,
                description="The requested access change failed validation.",
            ),
            status.HTTP_401_UNAUTHORIZED: DetailResponseSerializer,
            status.HTTP_403_FORBIDDEN: DetailResponseSerializer,
            status.HTTP_404_NOT_FOUND: DetailResponseSerializer,
        },
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
