try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:  # pragma: no cover
    from importlib_metadata import version, PackageNotFoundError  # type: ignore

try:
    __version__ = version("fc-django-post-api")
except PackageNotFoundError:  # 源码 checkout 场景
    __version__ = "2026.6.0"