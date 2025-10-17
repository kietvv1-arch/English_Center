"""Expose a concrete settings module for the default Django entrypoints.

The project scaffolding (manage.py, wsgi.py, asgi.py) references
`english_center.settings`. Without re-exporting a module here Django ends up
loading an empty settings object, which later crashes because required values
like `DATABASES["default"]["ENGINE"]` are missing. Importing the dev settings
keeps the default environment working out of the box, while still allowing
`DJANGO_SETTINGS_MODULE` to point elsewhere when needed."""

from .dev import *  # noqa: F401,F403
