from django.urls import path

from . import views


app_name = "main"

urlpatterns = [
    path("", views.home, name="home"),
    path("fragments/home/<slug:section>/", views.home_section, name="home_section"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("admin/learners/", views.admin_learners, name="admin_learners"),
    path("admin/learners/export/", views.admin_learners_export, name="admin_learners_export"),
    path("admin/learners/<int:pk>/delete/", views.admin_learners_delete, name="admin_learners_delete"),
    path("admin/overview/", views.admin_overview, name="admin_overview"),
    path("admin/overview/kpis/", views.admin_overview_kpis, name="admin_overview_kpis"),
    path("admin/overview/trends/", views.admin_overview_trends, name="admin_overview_trends"),
    path("admin/overview/alerts/", views.admin_overview_alerts, name="admin_overview_alerts"),
]
