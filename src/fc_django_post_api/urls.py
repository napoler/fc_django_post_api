"""API URL 配置。

挂载到项目根 URL 时通常以 ``/api/`` 为前缀：

    path("api/", include("fc_django_post_api.urls"))

URL 分布：
- ``/api/health/`` —— 健康检查（匿名）
- ``/api/me/`` —— 当前登录用户信息（JWT 鉴权）
- ``/api/posts/`` —— Post 资源路由（DRF DefaultRouter）
- ``/api/auth/`` —— JWT 令牌的获取 / 刷新 / 校验
- ``/api/users/`` —— Djoser 用户管理端点
- ``/api/docs/`` —— OpenAPI Schema 浏览端点
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

# 默认 DRF 路由器，将 ViewSet 注册为标准 REST 路由
router = DefaultRouter()
router.register(r"posts", PostViewSet, basename="post")

# JWT 鉴权端点（基于 SimpleJWT）
jwt_urls = [
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

# 用户管理端点（Djoser）：注册、激活、密码重置等
user_urls = [
    path("users/", include("djoser.urls")),
    path("users/", include("djoser.urls.jwt")),
]

# OpenAPI Schema 浏览端点
schema_view = get_schema_view(
    title="C-Life API",
    description="C-Life Blog API Documentation",
    version="1.0",
    public=True,
)

urlpatterns = [
    # 健康检查（无需鉴权）
    path("health/", HealthView.as_view(), name="api-health"),
    # 当前登录用户信息
    path("me/", MeView.as_view(), name="api-me"),
    # Post 资源根路由（list / create / retrieve / update / destroy / my_posts / publish / archive）
    path("", include(router.urls)),
    # JWT 鉴权（token 签发与刷新）
    path("auth/", include(jwt_urls)),
    # 用户管理（Djoser）
    path("", include(user_urls)),
    # OpenAPI Schema
    path("docs/", schema_view, name="api-docs"),
]
