"""API 帮助页与令牌签发相关的 admin 视图。

通过 monkey-patch 扩展默认的 ``admin.site`` 而非整体替换，
从而保留 ``tbase_admin`` 中已注册的全部模型。

``token_blacklist`` app 已从 ``INSTALLED_APPS`` 移除（迁移 0001 删除
``OutstandingToken`` / ``BlacklistedToken`` 表），因此本页不再查询持久化
历史令牌。GET 时 ``active_tokens`` 为空列表；POST 签发后仅把刚签发的
令牌以 ``id="just-issued"`` 追加到列表供用户复制。``revoke_token_view``
收到 ``token_id=0``（占位）时直接重定向到 api-help 页。
"""

from django.contrib import admin
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.urls import path, reverse
from django.conf import settings
from django.utils import timezone

from rest_framework_simplejwt.tokens import RefreshToken


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
    """渲染 admin 中的 API 文档页。

    ``active_tokens`` 永远为空（历史 token 表已删除），但保留字段以便
    模板可统一遍历。
    """
    base_url = request.build_absolute_uri("/api/")

    context = {
        "title": "API Token Management",
        "base_url": base_url,
        "active_tokens": [],
        **admin.site.each_context(request),
    }
    return render(request, "admin/api_help.html", context)


def api_token_view(request: HttpRequest) -> HttpResponse:
    """为当前登录用户签发 JWT 令牌对。

    GET: 渲染表单页 + 空历史令牌列表。
    POST: 调用 :func:`RefreshToken.for_user` 签发新令牌，并以
        ``id="just-issued"`` 写入 ``active_tokens`` 头部供模板展示。
    """
    jwt_settings = get_jwt_settings()
    active_tokens: list[dict] = []

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
            refresh = RefreshToken.for_user(request.user)
            now = timezone.now()
            access_lifetime = jwt_settings["access_lifetime"] or timezone.timedelta(hours=1)
            access_token_str = str(refresh.access_token)
            refresh_token_str = str(refresh)
            context["access_token"] = access_token_str
            context["refresh_token"] = refresh_token_str
            active_tokens.append(
                {
                    "id": "just-issued",
                    "created_at": now,
                    "expires_at": now + access_lifetime,
                    "is_expired": False,
                    "is_blacklisted": False,
                    "access_token": access_token_str,
                    "refresh_token": refresh_token_str,
                }
            )
            messages.success(request, "✅ 访问令牌已成功生成！")
        except Exception as e:
            messages.error(request, f"❌ 生成令牌失败: {str(e)}")

    return render(request, "admin/api_token.html", context)


def revoke_token_view(request: HttpRequest, token_id: int) -> HttpResponse:
    """占位路由：旧版依赖 ``OutstandingToken`` 表，删除后改为 no-op 重定向。

    客户端无法再引用持久化的 token id（0 是约定占位），所以直接跳到
    api-help 并提示用户重新签发。
    """
    messages.info(
        request,
        "历史令牌记录已被清理，请重新签发新令牌。",
    )
    return redirect("admin:api_help")


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


admin.site.get_urls = custom_get_urls


_original_get_app_list = admin.site.get_app_list.__func__


def custom_get_app_list(self, request):
    """扩展 ``admin.site.get_app_list()``，在 admin 左侧导航注入 API 菜单项。"""
    app_list = _original_get_app_list(self, request)

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

    if app_list and app_list[0].get("app_label") == "performance":
        app_list.insert(1, api_app)
    else:
        app_list.insert(0, api_app)

    return app_list


admin.site.get_app_list = custom_get_app_list.__get__(admin.site, type(admin.site))
