"""
API URL configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from djoser.views import UserViewSet
from rest_framework.schemas import get_schema_view

from .views import HealthView, MeView, PostViewSet

# Create a router and register viewsets
router = DefaultRouter()
router.register(r"posts", PostViewSet, basename="post")

# JWT Authentication endpoints
jwt_urls = [
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

# User management endpoints (Djoser)
user_urls = [
    path("users/", include("djoser.urls")),
    path("users/", include("djoser.urls.jwt")),
]

# API Schema / Docs
schema_view = get_schema_view(
    title="C-Life API",
    description="C-Life Blog API Documentation",
    version="1.0",
    public=True,
)

urlpatterns = [
    # Health check
    path("health/", HealthView.as_view(), name="api-health"),
    path("me/", MeView.as_view(), name="api-me"),
    # API root
    path("", include(router.urls)),
    # Authentication
    path("auth/", include(jwt_urls)),
    # User management
    path("", include(user_urls)),
    # API Docs
    path("docs/", schema_view, name="api-docs"),
]
