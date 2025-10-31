
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", include("main.urls", namespace="main")),
    path("admin/", admin.site.urls),
]
