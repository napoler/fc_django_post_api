"""Django admin 中 SimpleJWT 令牌表的管理类。

提供 ``OutstandingToken``（已签发但未过期的 JWT）与
``BlacklistedToken``（已吊销的 JWT）两个模型的管理界面：
- 列表展示、过滤、搜索字段
- 自定义布尔列 ``is_expired`` / ``is_blacklisted``
- 批量动作 ``revoke_tokens``，将选中的令牌加入黑名单
"""

from django.contrib import admin
from django.utils.html import format_html
from datetime import datetime
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

# 先取消 SimpleJWT 自动注册的默认 admin 类，再以本模块的自定义类接管
admin.site.unregister(OutstandingToken)
admin.site.unregister(BlacklistedToken)


@admin.register(OutstandingToken)
class OutstandingTokenAdmin(admin.ModelAdmin):
    """已签发 JWT 令牌的 admin 视图。"""

    list_display = [
        "id",
        "user",
        "created_at",
        "expires_at",
        "is_expired",
        "is_blacklisted",
    ]
    list_filter = ["created_at", "expires_at"]
    search_fields = ["user__username", "token_id"]
    readonly_fields = [
        "id",
        "user",
        "jti",
        "token",
        "created_at",
        "expires_at",
    ]
    actions = ["revoke_tokens"]

    def is_expired(self, obj):
        """判断令牌是否已过期。"""
        return obj.expires_at < datetime.now(obj.expires_at.tzinfo)

    is_expired.boolean = True

    def is_blacklisted(self, obj):
        """判断令牌是否已被加入黑名单。"""
        return BlacklistedToken.objects.filter(token=obj).exists()

    is_blacklisted.boolean = True

    @admin.action(description="Revoke selected tokens")
    def revoke_tokens(self, request, queryset):
        """批量动作：将选中的令牌加入黑名单（吊销）。"""
        for token in queryset:
            BlacklistedToken.objects.get_or_create(token=token)
        self.message_user(request, f"{queryset.count()} token(s) revoked.")

    revoke_tokens.allowed_permissions = ("delete",)


@admin.register(BlacklistedToken)
class BlacklistedTokenAdmin(admin.ModelAdmin):
    """已吊销 JWT 令牌的 admin 视图（只读）。"""

    list_display = ["id", "token", "blacklisted_at"]
    list_filter = ["blacklisted_at"]
    search_fields = ["token__user__username"]
    readonly_fields = ["token", "blacklisted_at"]
