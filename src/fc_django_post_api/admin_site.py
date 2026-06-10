"""API 帮助页与令牌签发相关的 admin 视图。

通过 monkey-patch 扩展默认的 ``admin.site`` 而非整体替换，
从而保留 ``tbase_admin`` 中已注册的全部模型。
"""

from django.contrib import admin
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.urls import path, reverse
from django.conf import settings

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken


def get_jwt_settings():
    """从 ``settings.SIMPLE_JWT`` 中读取 access / refresh 令牌的过期时间。"""
    jwt_settings = getattr(settings, "SIMPLE_JWT", {})
    access_lifetime = jwt_settings.get("ACCESS_TOKEN_LIFETIME")
    refresh_lifetime = jwt_settings.get("REFRESH_TOKEN_LIFETIME")
    return {
        "access_lifetime": access_lifetime,
        "refresh_lifetime": refresh_lifetime,
    }


def api_help_view(request: HttpRequest) -> HttpResponse:
    """渲染 admin 中的 API 文档与当前用户令牌列表页。"""
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    from django.utils import timezone

    base_url = request.build_absolute_uri("/api/")

    # 拉取当前用户的所有未过期 JWT，并标注每条是否已被吊销
    user_tokens = OutstandingToken.objects.filter(user=request.user)
    active_tokens = []
    for token in user_tokens:
        is_expired = token.expires_at < timezone.now()
        is_blacklisted = BlacklistedToken.objects.filter(token=token).exists()
        active_tokens.append(
            {
                "id": token.id,
                "created_at": token.created_at,
                "expires_at": token.expires_at,
                "is_expired": is_expired,
                "is_blacklisted": is_blacklisted,
            }
        )

    context = {
        "title": "API Token Management",
        "base_url": base_url,
        "active_tokens": active_tokens,
        **admin.site.each_context(request),
    }
    return render(request, "admin/api_help.html", context)


def api_token_view(request: HttpRequest) -> HttpResponse:
    """为当前登录用户签发 JWT 令牌对，并展示其历史令牌列表。

    GET: 渲染表单页 + 历史令牌列表（按签发时间倒序）。
    POST: 调用 :func:`RefreshToken.for_user` 签发新令牌，写回模板。
    """
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    from django.utils import timezone

    jwt_settings = get_jwt_settings()

    # 历史令牌列表（按签发时间倒序）
    user_tokens = OutstandingToken.objects.filter(user=request.user).order_by("-created_at")
    active_tokens = []
    for token in user_tokens:
        is_expired = token.expires_at < timezone.now()
        is_blacklisted = BlacklistedToken.objects.filter(token=token).exists()
        active_tokens.append(
            {
                "id": token.id,
                "created_at": token.created_at,
                "expires_at": token.expires_at,
                "is_expired": is_expired,
                "is_blacklisted": is_blacklisted,
            }
        )

    context = {
        "title": "获取访问令牌",
        "user": request.user,
        "access_token": None,
        "refresh_token": None,
        "access_lifetime": jwt_settings["access_lifetime"],
        "refresh_lifetime": jwt_settings["refresh_lifetime"],
        "active_tokens": active_tokens,
        **admin.site.each_context(request),
    }

    if request.method == "POST":
        try:
            # 为当前用户签发新的 access / refresh 令牌对
            refresh = RefreshToken.for_user(request.user)
            context["access_token"] = str(refresh.access_token)
            context["refresh_token"] = str(refresh)
            messages.success(request, "✅ 访问令牌已成功生成！")
        except Exception as e:
            messages.error(request, f"❌ 生成令牌失败: {str(e)}")

    return render(request, "admin/api_token.html", context)


def revoke_token_view(request: HttpRequest, token_id: int) -> HttpResponse:
    """吊销指定 JWT：将 ``OutstandingToken`` 标记进 ``BlacklistedToken`` 表。

    权限约束：普通用户只能吊销自己的令牌，超级用户可吊销任意令牌。
    """
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    from django.shortcuts import get_object_or_404, redirect

    token = get_object_or_404(OutstandingToken, id=token_id)

    # 权限校验：仅本人或超级用户可吊销
    if request.user != token.user and not request.user.is_superuser:
        messages.error(request, "You can only revoke your own tokens!")
        return redirect("admin:api_help")

    BlacklistedToken.objects.get_or_create(token=token)
    messages.success(request, f"Token #{token_id} has been revoked successfully!")
    return redirect("admin:api_help")


# 通过 monkey-patch 扩展 admin.site.get_urls()，注入自定义 URL
_original_get_urls = admin.site.get_urls


def custom_get_urls():
    """在 ``admin.site.get_urls()`` 返回的 URL 列表前插入 API 相关路由。"""
    urls = _original_get_urls()
    custom_urls = [
        path("api-help/", admin.site.admin_view(api_help_view), name="api_help"),
        path("api-token/", admin.site.admin_view(api_token_view), name="api_token"),
        path(
            "api-token/<int:token_id>/revoke/",
            admin.site.admin_view(revoke_token_view),
            name="api_token_revoke",
        ),
    ]
    return custom_urls + urls


# 应用 monkey-patch
admin.site.get_urls = custom_get_urls


# 通过 monkey-patch 扩展 admin.site.get_app_list()，在左侧导航添加 API 菜单
# Django 3.2 AdminSite.get_app_list(self, request)
_original_get_app_list = admin.site.get_app_list.__func__


def custom_get_app_list(self, request):
    """扩展 ``admin.site.get_app_list()``，在 admin 左侧导航注入 API 菜单项。"""
    app_list = _original_get_app_list(self, request)

    # 在 admin 导航中新增 API 应用入口
    api_app = {
        "name": "API",
        "app_label": "api",
        "app_url": reverse("admin:api_help"),
        "has_module_perms": True,
        "models": [
            {
                "name": "API 使用帮助",
                "object_name": "api_help",
                "admin_url": reverse("admin:api_help"),
                "view_only": True,
            },
            {
                "name": "获取访问令牌",
                "object_name": "api_token",
                "admin_url": reverse("admin:api_token"),
                "view_only": True,
            },
        ],
    }

    # 优先插入到"性能管理"之后（保持原"性能管理"在第一位），否则插到最前
    if app_list and app_list[0].get("app_label") == "performance":
        app_list.insert(1, api_app)
    else:
        app_list.insert(0, api_app)

    return app_list


# 应用 monkey-patch（绑定到 admin.site 实例）
admin.site.get_app_list = custom_get_app_list.__get__(admin.site, type(admin.site))
