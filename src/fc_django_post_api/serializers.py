"""Post CRUD 相关的 API 序列化器。

``Post`` 模型来自外部包 ``tbase_post.models.Post``，本模块按需在 ``__init__``
中动态导入，避免 Django App 加载顺序导致的循环导入。
"""

from rest_framework import serializers


class PostSerializer(serializers.ModelSerializer):
    """``Post`` 模型的完整序列化器，用于详情/创建/更新/部分更新动作。

    关键扩展：
    - ``tag_names``：接收/输出标签名列表，封装 django-taggit 写入
    - ``author``：仅读，写入由 ViewSet 通过 ``perform_create`` 注入
    - ``author_name``：从 ``author.username`` 派生的展示字段
    """

    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        allow_empty=True,
        help_text="List of tag names to set on the post",
    )
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = None  # 在 __init__ 中动态注入，避免循环 import
        fields = [
            "id",
            "title",
            "content",
            "publish_status",
            "created_on",
            "updated_on",
            "tag_names",
            "meta_description",
            "meta_keywords",
            "article_img",
            "product_name",
            "product_id",
            "youtube_id",
            "data",
            "author",
            "author_name",
        ]
        read_only_fields = [
            "id",
            "created_on",
            "updated_on",
            "author",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 动态导入 Post 模型，规避 AppConfig 加载顺序导致的循环依赖
        from tbase_post.models import Post

        self.Meta.model = Post

    def to_representation(self, instance):
        """在序列化输出中补全 ``tag_names`` 字段（取自 django-taggit）。"""
        data = super().to_representation(instance)
        try:
            data["tag_names"] = list(instance.tags.values_list("name", flat=True))
        except Exception:
            data["tag_names"] = []
        return data

    def create(self, validated_data):
        """创建 Post 实例并写入标签集合。"""
        tag_names = validated_data.pop("tag_names", [])
        instance = super().create(validated_data)
        self._set_tags(instance, tag_names)
        return instance

    def update(self, instance, validated_data):
        """更新 Post 字段；如传入 ``tag_names`` 则同步替换标签集合。"""
        tag_names = validated_data.pop("tag_names", None)
        instance = super().update(instance, validated_data)
        if tag_names is not None:
            self._set_tags(instance, tag_names)
        return instance

    def _set_tags(self, instance, tag_names):
        """使用 django-taggit 替换实例的全部标签。"""
        # 先清空再追加，确保最终标签集合与请求完全一致
        instance.tags.clear()
        for tag_name in tag_names:
            instance.tags.add(tag_name)

    def get_author_name(self, obj):
        """返回作者用户名；作者为空时返回 ``None``。"""
        try:
            return obj.author.username if obj.author else None
        except Exception:
            return None


class PostListSerializer(serializers.ModelSerializer):
    """``Post`` 列表动作使用的精简序列化器（仅核心字段）。"""

    tag_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = None  # 在 __init__ 中动态注入
        fields = [
            "id",
            "title",
            "publish_status",
            "created_on",
            "updated_on",
            "article_img",
            "tag_names",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from tbase_post.models import Post

        self.Meta.model = Post

    def get_tag_names(self, obj):
        """返回实例关联的标签名列表（取自 django-taggit）。"""
        try:
            return list(obj.tags.values_list("name", flat=True))
        except Exception:
            return []
