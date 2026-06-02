"""
Custom admin views for API Help and Token Generation.
Uses monkey-patching to extend the default admin.site without replacing it.
This preserves all existing model registrations from tbase_admin.
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
    """Get JWT token lifetime settings."""
    jwt_settings = getattr(settings, "SIMPLE_JWT", {})
    access_lifetime = jwt_settings.get("ACCESS_TOKEN_LIFETIME")
    refresh_lifetime = jwt_settings.get("REFRESH_TOKEN_LIFETIME")
    return {
        "access_lifetime": access_lifetime,
        "refresh_lifetime": refresh_lifetime,
    }


def api_help_view(request: HttpRequest) -> HttpResponse:
    """
    Display API documentation page in admin.
    """
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    from django.utils import timezone

    base_url = request.build_absolute_uri("/api/")

    # Get current user's tokens
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
    """
    Generate JWT token for the logged-in user and list existing tokens.
    """
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    from django.utils import timezone

    jwt_settings = get_jwt_settings()

    # Get current user's existing tokens
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
            # Generate tokens for the current user
            refresh = RefreshToken.for_user(request.user)
            context["access_token"] = str(refresh.access_token)
            context["refresh_token"] = str(refresh)
            messages.success(request, "✅ 访问令牌已成功生成！")
        except Exception as e:
            messages.error(request, f"❌ 生成令牌失败: {str(e)}")

    return render(request, "admin/api_token.html", context)


def revoke_token_view(request: HttpRequest, token_id: int) -> HttpResponse:
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    from django.shortcuts import get_object_or_404, redirect

    token = get_object_or_404(OutstandingToken, id=token_id)

    # Users can only revoke their own tokens, admins can revoke any
    if request.user != token.user and not request.user.is_superuser:
        messages.error(request, "You can only revoke your own tokens!")
        return redirect("admin:api_help")

    BlacklistedToken.objects.get_or_create(token=token)
    messages.success(request, f"Token #{token_id} has been revoked successfully!")
    return redirect("admin:api_help")


# Monkey-patch admin.site.get_urls() to add custom URLs
_original_get_urls = admin.site.get_urls


def custom_get_urls():
    """Extend admin.site.get_urls() with custom API URLs."""
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


# Apply the monkey-patch
admin.site.get_urls = custom_get_urls


# Monkey-patch admin.site.get_app_list() to add API menu to left navigation
# Django 3.2 AdminSite.get_app_list(self, request)
_original_get_app_list = admin.site.get_app_list.__func__


def custom_get_app_list(self, request):
    """Extend admin.site.get_app_list() to add API menu."""
    app_list = _original_get_app_list(self, request)

    # Add API application to navigation
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

    # Insert after "性能管理" (index 0) or at the end
    if app_list and app_list[0].get("app_label") == "performance":
        app_list.insert(1, api_app)
    else:
        app_list.insert(0, api_app)

    return app_list


# Apply the monkey-patch (bind to admin.site instance)
admin.site.get_app_list = custom_get_app_list.__get__(admin.site, type(admin.site))
