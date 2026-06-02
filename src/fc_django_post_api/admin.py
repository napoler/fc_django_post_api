from django.contrib import admin
from django.utils.html import format_html
from datetime import datetime
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

# Unregister the default admin classes first
admin.site.unregister(OutstandingToken)
admin.site.unregister(BlacklistedToken)


@admin.register(OutstandingToken)
class OutstandingTokenAdmin(admin.ModelAdmin):
    """Admin interface for viewing and managing JWT tokens."""

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
        """Check if token is expired."""
        return obj.expires_at < datetime.now(obj.expires_at.tzinfo)

    is_expired.boolean = True

    def is_blacklisted(self, obj):
        """Check if token is blacklisted."""
        return BlacklistedToken.objects.filter(token=obj).exists()

    is_blacklisted.boolean = True

    @admin.action(description="Revoke selected tokens")
    def revoke_tokens(self, request, queryset):
        """Revoke selected OutstandingTokens by blacklisting them."""
        for token in queryset:
            BlacklistedToken.objects.get_or_create(token=token)
        self.message_user(request, f"{queryset.count()} token(s) revoked.")

    revoke_tokens.allowed_permissions = ("delete",)


@admin.register(BlacklistedToken)
class BlacklistedTokenAdmin(admin.ModelAdmin):
    """Admin interface for viewing blacklisted tokens."""

    list_display = ["id", "token", "blacklisted_at"]
    list_filter = ["blacklisted_at"]
    search_fields = ["token__user__username"]
    readonly_fields = ["token", "blacklisted_at"]
