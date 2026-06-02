from django.apps import AppConfig


class FcDjangoPostApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fc_django_post_api"
    label = "api"
    verbose_name = "API"

    def ready(self):
        """
        Apply monkey-patch to admin.site when app is ready.
        This adds custom API help and token generation views to Django admin.
        """
        # Import applies the monkey-patch to admin.site
        from fc_django_post_api import admin_site  # noqa: F401
        from . import admin as api_admin  # noqa: F401
