"""
API Views for Post CRUD operations.
Uses tbase_post.models.Post from external package.
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
    """
    API endpoint for Post CRUD operations.

    list: Get all posts (paginated)
    create: Create a new post (requires authentication)
    retrieve: Get a single post by ID
    update: Update a post
    partial_update: Partially update a post
    destroy: Delete a post
    """

    permission_classes = [IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["publish_status"]
    search_fields = ["title", "content", "data"]
    ordering_fields = ["created_on", "updated_on"]
    ordering = ["-created_on"]

    def get_queryset(self):
        """
        Return posts based on user authentication status.
        - Authenticated users can see all posts
        - Unauthenticated users can only see published posts
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
        """
        Use different serializers for list and detail views.
        """
        if self.action == "list":
            return PostListSerializer
        return PostSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def my_posts(self, request):
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
    """Anonymous liveness + DB ping endpoint. No auth required."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
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
    """Authenticated identity + token expiry. No throttle_bypass (no throttling)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
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
