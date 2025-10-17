from django.shortcuts import render


def home(request):
    """Render the public landing page."""

    return render(request, "public/home.html")


def login(request):
    """Render the login page for public users."""

    return render(request, "public/login.html")
