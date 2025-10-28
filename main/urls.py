from django.urls import path

from . import views


app_name = "main"

urlpatterns = [
    path("", views.home, name="home"),
    path("fragments/home/<slug:section>/", views.home_section, name="home_section"),
    path("login/", views.login, name="login"),
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
]
