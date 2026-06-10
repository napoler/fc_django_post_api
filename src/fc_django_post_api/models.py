"""API 领域模型占位。

本包本身**不**定义 Django Model；所有数据模型（包括 ``Post``、``Tag`` 等）
均由外部包 ``django-tbase-post-product`` 提供，通过 ``tbase_post.models`` 引用。
序列化器与 ViewSet 在运行时按需动态导入该模块，
以避免在 Django App 加载顺序中产生循环依赖。
"""

from django.db import models  # noqa: F401  # 显式 re-export 给下游使用