"""Post CRUD 相关的 API 视图。

``Post`` 模型来自外部包 ``tbase_post.models.Post``，在运行时按需动态导入。
"""

from datetime import datetime

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db import OperationalError, connection
from django.utils import timezone

from .serializers import PostSerializer, PostListSerializer
from .permissions import IsAuthorOrReadOnly

API_VERSION = "1.0"


class PostViewSet(viewsets.ModelViewSet):
    """Post 资源的 ViewSet 入口。

    标准动作（继承自 ``ModelViewSet``）：
    - ``list``：分页列出文章
    - ``create``：登录用户创建文章（自动注入 ``author=request.user``）
    - ``retrieve``：按 ID 拉取单篇文章
    - ``update`` / ``partial_update``：作者本人更新文章
    - ``destroy``：作者本人删除文章

    自定义动作（``@action``）：
    - ``my_posts``：列出当前登录用户的所有文章（需登录）
    - ``publish``：作者将文章标记为已发布
    - ``archive``：作者将文章移入回收站

    过滤 / 搜索 / 排序：
    - ``?publish_status=`` 按发布状态过滤
    - ``?search=`` 全文搜索 title/content/data
    - ``?ordering=`` 按 created_on/updated_on 排序
    """

    permission_classes = [IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["publish_status"]
    search_fields = ["title", "content", "data"]
    ordering_fields = ["created_on", "updated_on"]
    ordering = ["-created_on"]

    def get_queryset(self):
        """根据用户登录态返回不同范围的 Post queryset。

        - 已认证用户：全部 Post（含草稿/回收站）
        - 匿名用户：仅返回 ``publish_status="published"`` 的 Post

        预取 ``tags`` 与 ``hit_count_generic`` 以减少列表查询的 N+1。
        """
        from tbase_post.models import Post

        user = self.request.user
        if user.is_authenticated:
            return Post.objects.all().prefetch_related("tags", "hit_count_generic")
        else:
            return Post.objects.filter(publish_status="published").prefetch_related(
                "tags", "hit_count_generic"
            )

    def get_serializer_class(self):
        """``list`` 动作使用精简版 ``PostListSerializer``，其余动作使用完整版。"""
        if self.action == "list":
            return PostListSerializer
        return PostSerializer

    def retrieve(self, request, *args, **kwargs):
        """详情接口：直接复用基类实现，显式声明便于子类扩展。"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """创建时自动注入当前登录用户为作者。"""
        serializer.save(author=self.request.user)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def my_posts(self, request):
        """``GET /api/posts/my_posts/`` —— 返回当前登录用户的所有文章（需登录）。"""
        from tbase_post.models import Post

        posts = Post.objects.filter(author=request.user)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def publish(self, request, pk=None):
        """``POST /api/posts/{id}/publish/`` —— 作者将指定文章标记为已发布。

        非作者操作返回 403。
        """
        post = self.get_object()
        if post.author != request.user:
            return Response(
                {"error": "You can only publish your own posts"}, status=status.HTTP_403_FORBIDDEN
            )
        post.publish_status = "published"
        post.save()

        serializer = self.get_serializer(post)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def archive(self, request, pk=None):
        """``POST /api/posts/{id}/archive/`` —— 作者将指定文章移入回收站。

        非作者操作返回 403。
        """
        post = self.get_object()
        if post.author != request.user:
            return Response(
                {"error": "You can only archive your own posts"}, status=status.HTTP_403_FORBIDDEN
            )
        post.publish_status = "trash"
        post.save()

        serializer = self.get_serializer(post)
        return Response(serializer.data)


class HealthView(APIView):
    """匿名可访问的存活探针 + 数据库连通性探测端点。

    数据库不可达时返回 ``503`` 与 ``status="degraded"``，便于上游负载均衡
    判别本实例是否应继续接流量。
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """返回 API 版本、DB 状态及时间戳；DB 不可用时返回 503。

        响应头 ``Cache-Control: no-store``，禁止任何中间层缓存健康检查结果。
        """
        from django import get_version

        db_status = "ok"
        http_status = 200
        try:
            connection.ensure_connection()
        except OperationalError:
            db_status, http_status = "error", 503
        resp = Response(
            {
                "version": API_VERSION,
                "status": "ok" if db_status == "ok" else "degraded",
                "db": db_status,
                "django_version": get_version(),
                "timestamp": timezone.now().isoformat(),
            },
            status=http_status,
        )
        resp["Cache-Control"] = "no-store"
        return resp


class MeView(APIView):
    """登录态身份信息 + 访问令牌过期时间端点。

    无 throttling，故响应中不含 ``throttle_bypass`` 字段。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """返回当前登录用户基本信息与 access token 的 ISO-8601 过期时间。"""
        user = request.user
        token_exp = None
        auth = request.auth
        if isinstance(auth, dict) and "exp" in auth:
            token_exp = datetime.fromtimestamp(auth["exp"], tz=timezone.utc).isoformat()
        return Response(
            {
                "version": API_VERSION,
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_staff": user.is_staff,
                "token_exp": token_exp,
            }
        )
