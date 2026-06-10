"""Django App 配置。

将包注册为 ``api`` 标签（保持与 Django ``reverse`` 查找、迁移历史兼容）。
``admin.site`` 的 monkey-patch 已从 ``ready()`` 移除，改为在 ``urls.py`` 顶部
lazy 触发；这避开了 ``apps.populate()`` 锁内导入 admin 模块导致的
``RuntimeError: populate() isn't reentrant``（阿里云 FC 冷启动路径上必现）。
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
