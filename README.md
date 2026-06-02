# fc-django-post-api

[![PyPI version](https://badge.fury.io/py/fc-django-post-api.svg)](https://pypi.org/project/fc-django-post-api/)

Django REST API package extracted from [fc_django_crazypowertools](https://github.com/napoler/fc_django_crazypowertools).

> **Status:** experimental — first PyPI release (2026.6.0).

## Install

```bash
pip install fc-django-post-api
```

## Configure

Add to `INSTALLED_APPS` in your Django settings:

```python
INSTALLED_APPS = [
    ...,
    "fc_django_post_api",
]
```

The `AppConfig` declares `label = "api"`, so the Django app label remains `api` even though the Python import is `fc_django_post_api`. Database tables, migrations, and `reverse()` lookups are unaffected.

## Mount URLs

```python
# urls.py
urlpatterns = [
    path("api/", include("fc_django_post_api.urls")),
    ...,
]
```

## Endpoints

- `GET /api/posts/` — PostViewSet (DRF)
- `GET /api/health/` — HealthView
- `GET /api/me/` — MeView
- `POST /api/auth/token/` — JWT obtain
- `POST /api/auth/token/refresh/` — JWT refresh

## License

MIT — see `LICENSE`.
