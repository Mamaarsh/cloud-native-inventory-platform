from django.urls import path
from .views import (
    AdminUserDetailView,
    AdminUserListView,
    CurrentUserView,
    PasswordChangeView,
    TokenObtainPairAPIView,
    TokenRefreshAPIView,
    UserRegistrationView,
)

app_name = "users"
urlpatterns = [
    path(
        "admin/users/",
        AdminUserListView.as_view(),
        name="admin-user-list",
    ),
    path(
        "admin/users/<int:pk>/",
        AdminUserDetailView.as_view(),
        name="admin-user-detail",
    ),
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("token/", TokenObtainPairAPIView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", TokenRefreshAPIView.as_view(), name="token-refresh"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path(
        "change-password/",
        PasswordChangeView.as_view(),
        name="change-password",
    ),
]
