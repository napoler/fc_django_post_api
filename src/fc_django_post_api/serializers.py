"""
API Serializers for Post CRUD operations.
Uses tbase_post.models.Post from external package.
"""

from rest_framework import serializers


class PostSerializer(serializers.ModelSerializer):
    """
    Serializer for tbase_post Post model.
    Uses ModelSerializer for automatic field mapping.
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
        model = None  # Set dynamically in __init__
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
        # Import Post model dynamically to avoid import errors
        from tbase_post.models import Post

        self.Meta.model = Post

    def to_representation(self, instance):
        """Include tag_names in output."""
        data = super().to_representation(instance)
        try:
            data["tag_names"] = list(instance.tags.values_list("name", flat=True))
        except Exception:
            data["tag_names"] = []
        return data

    def create(self, validated_data):
        """Create post and set tags."""
        tag_names = validated_data.pop("tag_names", [])
        instance = super().create(validated_data)
        self._set_tags(instance, tag_names)
        return instance

    def update(self, instance, validated_data):
        """Update post and set tags."""
        tag_names = validated_data.pop("tag_names", None)
        instance = super().update(instance, validated_data)
        if tag_names is not None:
            self._set_tags(instance, tag_names)
        return instance

    def _set_tags(self, instance, tag_names):
        """Set tags on instance using django-taggit."""
        # Clear existing tags and add new ones
        instance.tags.clear()
        for tag_name in tag_names:
            instance.tags.add(tag_name)

    def get_author_name(self, obj):
        """Get author username."""
        try:
            return obj.author.username if obj.author else None
        except Exception:
            return None


class PostListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for post listing.
    """

    tag_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = None  # Set dynamically in __init__
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
        """Get tag names from taggit."""
        try:
            return list(obj.tags.values_list("name", flat=True))
        except Exception:
            return []
