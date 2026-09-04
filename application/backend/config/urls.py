"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView, 
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from inventory.views import health_dependencies, health_live, health_ready

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/live/", health_live, name="health-live"),
    path("api/health/ready/", health_ready, name="health-ready"),
    path(
        "api/health/dependencies/",
        health_dependencies,
        name="health-dependencies",
    ),

    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema"
        ),
        name="swagger-ui",
    ),

    path(
        "api/redoc/",
        SpectacularRedocView.as_view(
            url_name="schema"
        ),
        name="redoc",
    ),

    path(
        "api/v1/",
        include("inventory.api.v1.urls")
    ),

    path(
        "api/auth/",
        include("users.urls")
    ),
]