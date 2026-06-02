"""
Custom permissions for API endpoints.
"""

from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow authors of an object to edit it.
    Assumes the model instance has an 'author' attribute.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for the author
        # If obj.author is None, deny write access
        if obj.author is None:
            return False
        return obj.author == request.user
