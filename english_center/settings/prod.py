
from .base import *  # noqa

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["example.com"])
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
