"""Django App 配置。

将包注册为 ``api`` 标签（保持与 Django ``reverse`` 查找、迁移历史兼容），
并于 App 启动时为 ``admin.site`` 注入自定义 URL 与导航菜单。
"""

from django.apps import AppConfig


class FcDjangoPostApiConfig(AppConfig):
    """``fc_django_post_api`` 包的 AppConfig。

    Attributes:
        default_auto_field: 主键类型，``BigAutoField`` 与现代 Django 推荐一致。
        name: Python 包路径。
        label: Django App 标签，固定为 ``"api"``，与外部迁移历史保持兼容。
        verbose_name: 在 admin 侧边栏展示的中文名。
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "fc_django_post_api"
    label = "api"
    verbose_name = "API"

    def ready(self):
        """App 启动钩子：通过 import 副作用注入 admin monkey-patch。

        仅做导入，不调用任何函数；模块顶层即完成对 ``admin.site`` 的扩展。
        """
        # 导入即触发 admin.site 的 monkey-patch
        from fc_django_post_api import admin_site  # noqa: F401
        from . import admin as api_admin  # noqa: F401
