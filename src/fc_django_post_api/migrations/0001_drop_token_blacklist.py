"""
删除 SimpleJWT token_blacklist 相关数据表。

``token_blacklist`` app 已于 2026-06-03 从 ``INSTALLED_APPS`` 中移除，
并同步将 ``BLACKLIST_AFTER_ROTATION`` 设为 ``False``。这些数据表已无任何
代码路径在查询，属于历史遗留。本迁移将其删除以保持 schema 整洁。

``reverse`` 操作为空操作：若要重新创建这些表，需先把 ``token_blacklist`` app
加回 ``INSTALLED_APPS`` 并应用其自带迁移。

本迁移未声明任何父依赖：``token_blacklist`` 已不在 ``INSTALLED_APPS`` 中，
若引用其迁移会在 Django 迁移图中产生孤立节点。``DROP TABLE`` 使用了
``IF EXISTS`` 守卫，在全新数据库上重复执行是安全的 no-op。

本项目使用的 PyMySQL 驱动默认未启用 ``CLIENT_MULTI_STATEMENTS``，因此语句
需逐条在同一 cursor 上执行。``FOREIGN_KEY_CHECKS`` 用于临时绕过两张 blacklist
表之间的外键约束。
"""

from django.db import migrations


def drop_blacklist_tables(apps, schema_editor):
    """正向下：关闭 FK 检查后按顺序删除两张 blacklist 表，再恢复 FK 检查。"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("DROP TABLE IF EXISTS token_blacklist_blacklistedtoken")
        cursor.execute("DROP TABLE IF EXISTS token_blacklist_outstandingtoken")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def noop_reverse(apps, schema_editor):
    """反向下：no-op，不重建 blacklist 表（详见模块 docstring）。"""
    pass


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.RunPython(drop_blacklist_tables, reverse_code=noop_reverse),
    ]
