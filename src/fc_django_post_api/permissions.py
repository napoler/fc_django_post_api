"""API 端点的自定义权限类。

当前仅提供 :class:`IsAuthorOrReadOnly`，用于 ``PostViewSet`` 的对象级权限校验。
"""

from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """对象级权限：仅作者本人可写，其他人仅可读。

    依赖模型实例具有 ``author`` 属性（指向 ``settings.AUTH_USER_MODEL``）。
    """

    def has_object_permission(self, request, view, obj):
        # 读请求（GET / HEAD / OPTIONS）一律放行
        if request.method in permissions.SAFE_METHODS:
            return True

        # 写请求仅允许作者本人；若对象没有 author（孤儿数据），直接拒绝
        if obj.author is None:
            return False
        return obj.author == request.user
