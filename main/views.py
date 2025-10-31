"""Views powering the public landing pages and a lightweight admin dashboard.

The file is organised into four logical blocks:
    1.  Constants and helper utilities shared across views.
    2.  A context builder dedicated to aggregating home-page data.
    3.  Public-facing views (login, home, fragments).
    4.  Admin helpers used by the custom dashboard.

Each section is kept small and documented so new teammates can trace the
data flow without jumping between modules.
"""

from datetime import date, datetime
from decimal import Decimal
import json
import logging
from typing import Any, Dict, List, Optional, Sequence, TypedDict
from functools import cached_property

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Avg, Count, Q, QuerySet, Sum
from django.db.models.functions import TruncMonth
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .models import (
    Achievement,
    Course,
    HeroHighlight,
    HomeSetting,
    NavigationLink,
    OutstandingGraduate,
    Reason,
    SuccessStory,
    Teacher,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared types and constants
# ---------------------------------------------------------------------------


class NavLink(TypedDict):
    label: str
    href: str


class HomeSectionConfig(TypedDict):
    template: str
    keys: List[str]


# Default data is used whenever the database is empty so the landing pages
# still render a sensible baseline layout.
DEFAULT_HERO_SETTING: Dict[str, str] = {
    "eyebrow": "Global English",
    "typed_text": "Unlock the world with English",
    "subtitle": (
        "Personal coaching, interactive classes, and progress tracking "
        "to help you feel confident in every conversation."
    ),
    "primary_cta_label": "Talk to us",
    "primary_cta_href": "#advisory",
    "secondary_cta_label": "Watch intro video",
    "secondary_cta_href": "#intro-video",
}

DEFAULT_HERO_HIGHLIGHTS: List[Dict[str, str]] = [
    {
        "icon": "fas fa-graduation-cap",
        "title": "Expert instructors",
        "description": "Work with native-level teachers and industry mentors.",
    },
    {
        "icon": "fas fa-chalkboard-teacher",
        "title": "Interactive classes",
        "description": "Blended learning with live workshops and practice labs.",
    },
    {
        "icon": "fas fa-certificate",
        "title": "Global certificates",
        "description": "Stay on track with international standards and tracking tools.",
    },
]

DEFAULT_NAV_LINKS: List[NavLink] = [
    {"label": "About", "href": "#features"},
    {"label": "Courses", "href": "#courses"},
    {"label": "Teachers", "href": "#teachers"},
    {"label": "Graduates", "href": "#graduates"},
    {"label": "Testimonials", "href": "#testimonials"},
    {"label": "Achievements", "href": "#achievements"},
]

DEFAULT_FOOTER_PROGRAMS: List[NavLink] = [
    {"label": "Communication English", "href": "#courses"},
    {"label": "Business English", "href": "#courses"},
    {"label": "IELTS coaching", "href": "#courses"},
    {"label": "Young learners", "href": "#courses"},
]

DEFAULT_FOOTER_ABOUT: List[NavLink] = [
    {"label": "About", "href": "#features"},
    {"label": "Our teachers", "href": "#teachers"},
    {"label": "Teaching method", "href": "#features"},
    {"label": "Facilities", "href": "#features"},
]

DEFAULT_COURSE_ICONS: Dict[str, str] = {
    "Beginner": "fas fa-seedling",
    "Intermediate": "fas fa-chart-line",
    "Advanced": "fas fa-rocket",
    "AllLevels": "fas fa-layer-group",
}


def _calculate_experience_years(start_date):
    """Return full years of experience since ``start_date``.

    We guard against ``None`` and negative values so UI code can rely on a
    clean (or null) integer.
    """

    if not start_date:
        return None
    today = date.today()
    years = today.year - start_date.year
    if (today.month, today.day) < (start_date.month, start_date.day):
        years -= 1
    return max(years, 0)


def _format_course_duration(duration_hours, lesson_count):
    """Return a friendly duration string (e.g. '12 lessons Ã¢â‚¬Â¢ 36 hours')."""

    def _normalize(value):
        try:
            number = float(value)
            if number.is_integer():
                return int(number)
            return round(number, 1)
        except (TypeError, ValueError):
            return value

    hours = _normalize(duration_hours)
    lessons = _normalize(lesson_count)

    if hours and lessons:
        return f"{lessons} lessons Ã¢â‚¬Â¢ {hours} hours"
    if hours:
        return f"{hours} hours"
    if lessons:
        return f"{lessons} lessons"
    return "Flexible"


# ---------------------------------------------------------------------------
# Authentication helpers and views
# ---------------------------------------------------------------------------


def _redirect_authenticated_user(user) -> Optional[HttpResponse]:
    """Return a redirect response for an authenticated user, if applicable."""

    if not getattr(user, "is_authenticated", False):
        return None
    target = "main:admin_overview" if (user.is_staff or user.is_superuser) else "main:home"
    return redirect(target)


def _resolve_next_url(request: HttpRequest) -> str:
    """Extract and validate the desired post-login destination."""

    candidate = request.POST.get("next") or request.GET.get("next") or ""
    if not candidate:
        return ""
    if url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ""


def login(request: HttpRequest) -> HttpResponse:
    """Authenticate a public user with optional safe redirects."""

    existing = _redirect_authenticated_user(request.user)
    if existing:
        return existing

    error_message: Optional[str] = None
    username_value = ""
    remember_checked = False
    next_url = _resolve_next_url(request)

    if request.method == "POST":
        username_value = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        remember_checked = request.POST.get("remember") == "on"

        user = authenticate(request, username=username_value, password=password)
        if user is not None:
            auth_login(request, user)
            if not remember_checked:
                # Session expires when the browser closes if "remember" is off.
                request.session.set_expiry(0)

            if user.is_staff or user.is_superuser:
                return redirect("main:admin_overview")

            return redirect(next_url or "main:home")

        error_message = "Ten dang nhap hoac mat khau khong dung. Vui long thu lai."

    context = {
        "error": error_message,
        "username_value": username_value,
        "next": next_url,
        "remember_checked": remember_checked,
    }
    return render(request, "public/login.html", context)


def logout(request: HttpRequest) -> HttpResponse:
    """Terminate the current session and redirect to a safe destination."""

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("main:home")

    auth_logout(request)
    return redirect(next_url)


# ---------------------------------------------------------------------------
# Home page context builder
# ---------------------------------------------------------------------------


class HomePageContextBuilder:
    """Collect and serialise data needed for the public home page."""

    def __init__(self) -> None:
        # Cache ``timezone.now()`` so queries in a single request are consistent.
        self.now = timezone.now()

    # ----- public API -----------------------------------------------------

    def build(self) -> Dict[str, Any]:
        """Return a dictionary ready for rendering the home page template."""

        achievements = self._serialize_achievements()

        context = {
            "nav_links": self._nav_links(
                location=NavigationLink.LOCATION_HEADER, default=DEFAULT_NAV_LINKS
            ),
            "hero_setting": self._hero_setting(),
            "hero_highlights": self._hero_highlights(),
            "reasons": self._active_reasons(),
            "force_visible": False,
            "teachers": self._serialize_teachers(),
            "achievements": achievements,
            # The design expects ``stats`` to mirror achievements; reuse it to avoid
            # recomputing similar structures.
            "stats": list(achievements),
            "courses": self._serialize_courses(),
            "graduates": self._serialize_graduates(),
            "testimonials": self._serialize_testimonials(),
            "footer_programs": self._nav_links(
                location=NavigationLink.LOCATION_FOOTER_PROGRAM,
                default=DEFAULT_FOOTER_PROGRAMS,
            ),
            "footer_about": self._nav_links(
                location=NavigationLink.LOCATION_FOOTER_ABOUT,
                default=DEFAULT_FOOTER_ABOUT,
            ),
        }
        return context

    # ----- query helpers --------------------------------------------------

    def _nav_links(self, *, location: str, default: Sequence[NavLink]) -> List[NavLink]:
        """Fetch navigation links or fall back to a predefined list."""

        links = (
            NavigationLink.objects.filter(location=location, is_active=True)
            .order_by("order", "id")
            .only("label", "href")
        )
        payload = [{"label": link.label, "href": link.href or "#"} for link in links]
        return payload or list(default)

    def _hero_setting(self) -> Dict[str, str]:
        """Merge database hero settings with defaults."""

        setting = dict(DEFAULT_HERO_SETTING)
        hero_obj = (
            HomeSetting.objects.filter(is_active=True).order_by("order", "id").first()
        )
        if not hero_obj:
            return setting

        for key in (
            "eyebrow",
            "typed_text",
            "subtitle",
            "primary_cta_label",
            "primary_cta_href",
            "secondary_cta_label",
            "secondary_cta_href",
        ):
            value = getattr(hero_obj, key, None)
            if value:
                setting[key] = value

        if not setting["secondary_cta_label"]:
            setting["secondary_cta_href"] = "#"
        return setting

    def _hero_highlights(self) -> List[Dict[str, str]]:
        """Return highlight cards for the hero section."""

        highlights = (
            HeroHighlight.objects.filter(is_active=True)
            .order_by("order", "id")
            .only("icon", "title", "description")
        )
        payload = [
            {"icon": card.icon, "title": card.title, "description": card.description}
            for card in highlights
        ]
        return payload or list(DEFAULT_HERO_HIGHLIGHTS)

    def _active_reasons(self) -> QuerySet[Reason]:
        """Return active reasons (why choose us)."""

        return Reason.objects.filter(is_active=True).order_by("order", "id")

    def _teacher_queryset(self) -> QuerySet[Teacher]:
        """Attempt to use ``TeacherQuerySet.featured`` when available."""

        queryset = Teacher.objects.filter(status="Active").order_by("order", "id")
        featured = getattr(Teacher.objects, "featured", None)
        if callable(featured):
            try:
                queryset = featured().order_by("order", "id")
            except Exception:
                # Do not break the page if the custom queryset misbehaves.
                pass
        return queryset.only(
            "full_name", "specialization", "bio", "start_date", "avatar"
        )

    def _course_queryset(self) -> QuerySet[Course]:
        """Return all active courses ordered by creation id."""

        return Course.objects.filter(is_active=True).order_by("id")

    def _graduate_queryset(self) -> QuerySet[OutstandingGraduate]:
        """Filter graduates based on publish window and activity flag."""

        return (
            OutstandingGraduate.objects.filter(is_active=True)
            .filter(
                Q(publish_at__isnull=True) | Q(publish_at__lte=self.now),
                Q(unpublish_at__isnull=True) | Q(unpublish_at__gt=self.now),
            )
            .order_by("order", "id")
        )

    def _testimonial_queryset(self) -> QuerySet[SuccessStory]:
        """Return approved success stories newest first."""

        return SuccessStory.objects.filter(is_approved=True).order_by(
            "order", "-created_at"
        )

    def _achievement_queryset(self) -> QuerySet[Achievement]:
        """Filter achievements that are currently published."""

        return (
            Achievement.objects.filter(is_active=True)
            .filter(
                Q(publish_at__isnull=True) | Q(publish_at__lte=self.now),
                Q(unpublish_at__isnull=True) | Q(unpublish_at__gt=self.now),
            )
            .order_by("order", "id")
        )

    # ----- serializers ----------------------------------------------------

    def _serialize_teachers(self) -> List[Dict[str, Any]]:
        """Render teacher querysets into lightweight dictionaries."""

        payload: List[Dict[str, Any]] = []
        for teacher in self._teacher_queryset():
            payload.append(
                {
                    "name": teacher.full_name,
                    "role": teacher.specialization,
                    "bio": teacher.bio,
                    "experience_years": _calculate_experience_years(teacher.start_date),
                    "avatar_url": getattr(teacher, "avatar_url", None),
                }
            )
        return payload

    def _serialize_courses(self) -> List[Dict[str, Any]]:
        """Return course cards enriched with icon, level label, and duration."""

        level_map = dict(getattr(Course, "LEVEL_CHOICES", []))
        default_icon = "fas fa-book-open"
        payload: List[Dict[str, Any]] = []
        for course in self._course_queryset():
            payload.append(
                {
                    "title": course.title,
                    "description": course.description,
                    "level": level_map.get(course.level, course.level),
                    "icon": getattr(course, "icon", None)
                    or DEFAULT_COURSE_ICONS.get(course.level, default_icon),
                    "duration": getattr(course, "duration", None)
                    or _format_course_duration(
                        getattr(course, "duration_hours", None),
                        getattr(course, "lesson_count", None),
                    ),
                }
            )
        return payload

    def _serialize_graduates(self) -> List[Dict[str, Any]]:
        """Return outstanding graduate cards."""

        payload: List[Dict[str, Any]] = []
        for graduate in self._graduate_queryset():
            payload.append(
                {
                    "name": graduate.student_name,
                    "course": graduate.course_name,
                    "score": getattr(graduate, "score_display", None),
                    "testimonial": graduate.testimonial,
                    "photo_url": getattr(graduate, "photo_url", None)
                    or static("public/images/graduate/placeholder.svg"),
                }
            )
        return payload

    def _serialize_testimonials(self) -> List[Dict[str, Any]]:
        """Return short quotes derived from success stories."""

        payload: List[Dict[str, Any]] = []
        for story in self._testimonial_queryset():
            initials = "".join(
                part[:1] for part in (story.student_name or "").split() if part
            )
            payload.append(
                {
                    "quote": (story.story or "")[:160],
                    "initials": (initials.upper()[:2] or "HV"),
                    "name": story.student_name,
                    "program": story.course_name,
                }
            )
        return payload

    def _serialize_achievements(self) -> List[Dict[str, Any]]:
        """Return achievement cards including optional metric display."""

        payload: List[Dict[str, Any]] = []
        for achievement in self._achievement_queryset():
            payload.append(
                {
                    "title": achievement.title,
                    "subtitle": achievement.subtitle,
                    "description": achievement.description,
                    "kind": achievement.get_kind_display(),
                    "year": achievement.year,
                    "has_metric": achievement.has_metric,
                    "metric_display": achievement.metric_display,
                    "image_url": achievement.image_url,
                    "image_alt": achievement.image_alt,
                    "external_url": achievement.external_url,
                }
            )
        return payload


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------


def _build_home_page_context() -> Dict[str, Any]:
    """Small wrapper to keep the template call sites tidy."""

    return HomePageContextBuilder().build()


def home(request: HttpRequest) -> HttpResponse:
    """Render the public home page populated with aggregated content."""

    context = _build_home_page_context()
    return render(request, "public/home.html", context)


HOME_SECTION_PARTIALS: Dict[str, HomeSectionConfig] = {
    "features": {"template": "public/fragments/features.html", "keys": ["reasons"]},
    "courses": {"template": "public/fragments/courses.html", "keys": ["courses"]},
    "teachers": {"template": "public/fragments/teachers.html", "keys": ["teachers"]},
    "graduates": {"template": "public/fragments/graduates.html", "keys": ["graduates"]},
    "testimonials": {
        "template": "public/fragments/testimonials.html",
        "keys": ["testimonials"],
    },
    "achievements": {
        "template": "public/fragments/achievements.html",
        "keys": ["achievements"],
    },
}


def home_section(request: HttpRequest, section: str) -> HttpResponse:
    """Return only the requested home section (HTMX friendly)."""

    config = HOME_SECTION_PARTIALS.get(section)
    if not config:
        raise Http404("Home section not found.")

    context = _build_home_page_context()
    payload = {key: context.get(key) for key in config["keys"]}
    payload["section"] = section
    # HX requests want the fragment to render immediately even if flagged hidden.
    payload["force_visible"] = request.headers.get("HX-Request") == "true"
    return render(request, config["template"], payload)


# ---------------------------------------------------------------------------
# Admin dashboard helpers
# ---------------------------------------------------------------------------


def _normalize_service_status(value) -> str:
    """Normalise service health indicators to 'up', 'down', or 'unknown'."""

    if value is None:
        return "unknown"
    normalized = str(value).strip().lower()
    if normalized in {"up", "ok", "running", "ready", "healthy", "online"}:
        return "up"
    if normalized in {"down", "error", "failed", "offline", "unhealthy"}:
        return "down"
    return "unknown"


def _get_admin_footer_context() -> Dict[str, Any]:
    """Collect metadata used by the custom admin footer."""

    version = getattr(settings, "APP_VERSION", getattr(settings, "VERSION", "v1.0.0"))
    environment = (
        getattr(settings, "APP_ENVIRONMENT", getattr(settings, "ENVIRONMENT", "PROD"))
        or "PROD"
    )
    brand_name = getattr(settings, "SITE_BRAND_NAME", "Global English")
    build_commit = getattr(
        settings, "BUILD_COMMIT", getattr(settings, "GIT_COMMIT", "abc1234")
    )
    build_timestamp = getattr(settings, "BUILD_TIMESTAMP", None)
    service_status = getattr(settings, "ADMIN_SERVICE_STATUS", {})

    celery_status = _normalize_service_status(service_status.get("celery"))
    redis_status = _normalize_service_status(service_status.get("redis"))
    smtp_status = _normalize_service_status(service_status.get("smtp"))

    if build_timestamp is None:
        formatted_timestamp = timezone.now().strftime("%d/%m/%Y %H:%M")
    elif hasattr(build_timestamp, "strftime"):
        formatted_timestamp = build_timestamp.strftime("%d/%m/%Y %H:%M")
    else:
        formatted_timestamp = str(build_timestamp)

    return {
        "brand_name": brand_name,
        "app_version": version,
        "app_environment": str(environment).upper(),
        "build_commit": str(build_commit)[:7],
        "build_timestamp": formatted_timestamp,
        "celery_status": celery_status,
        "redis_status": redis_status,
        "smtp_status": smtp_status,
        "storage_db_usage": getattr(settings, "ADMIN_STORAGE_DB_USAGE", None) or "--",
        "storage_media_usage": getattr(settings, "ADMIN_STORAGE_MEDIA_USAGE", None)
        or "--",
    }


MASKED_PLACEHOLDER = "****"


class AdminOverviewService:
    """Collect metrics and snapshots for the admin overview."""

    KPI_CACHE_TIMEOUT = 1800  # 30 minutes
    CHART_CACHE_TIMEOUT = 1800
    ALERT_CACHE_TIMEOUT = 1800
    ACTIVITY_DEFAULT_LIMIT = 3

    def __init__(self, user):
        self.user = user
        self.now = timezone.now()
        self.tz = timezone.get_current_timezone()
        self.mask_finance = not (
            user.is_superuser
            or user.has_perm("main.view_finance_metrics")
            or user.has_perm("main.view_finance")
        )

    @cached_property
    def _course_summary(self) -> Dict[str, Any]:
        start_month = self._month_start(0)
        return Course.objects.aggregate(
            mtd=Sum("price", filter=Q(created_at__gte=start_month)),
        )

    @cached_property
    def _graduate_summary(self) -> Dict[str, Any]:
        start_month = self._month_start(0)
        testimonial_filter = Q(testimonial__isnull=False) & ~Q(testimonial="")
        rating_filter = Q(score_value__isnull=False)
        return OutstandingGraduate.objects.aggregate(
            active=Count("id", filter=Q(is_active=True)),
            new_term=Count("id", filter=Q(created_at__gte=start_month)),
            testimonials=Count("id", filter=testimonial_filter),
            avg_rating=Avg("score_value", filter=rating_filter),
        )

    @cached_property
    def _teacher_summary(self) -> Dict[str, Any]:
        return Teacher.objects.aggregate(
            active=Count("id", filter=Q(status="Active")),
            total=Count("id"),
        )

    def _cache_key(self, slug: str) -> str:
        mask_suffix = "masked" if self.mask_finance else "full"
        return f"admin_overview:{slug}:{mask_suffix}"

    def _cache_get(self, key: str):
        try:
            return cache.get(key)
        except Exception as exc:  # pragma: no cover - cache backend optional
            logger.warning(
                "overview cache get failed",
                extra={"key": key, "error": str(exc)},
            )
            return None

    def _cache_set(self, key: str, value, timeout: int) -> None:
        try:
            cache.set(key, value, timeout)
        except Exception as exc:  # pragma: no cover - cache backend optional
            logger.warning(
                "overview cache set failed",
                extra={"key": key, "error": str(exc)},
            )

    def _cache_peek(self, slug: str):
        """Return cached payload for ``slug`` without recomputing when missing."""
        key = self._cache_key(slug)
        return self._cache_get(key)

    def peek_kpis(self) -> Optional[Dict[str, Any]]:
        """Return cached KPI payload if available."""
        payload = self._cache_peek("kpis")
        return payload if payload is not None else None

    def peek_charts(self) -> Optional[Dict[str, Any]]:
        """Return cached chart payload if available."""
        payload = self._cache_peek("charts")
        return payload if payload is not None else None

    def peek_activity_feed(self, limit: int = ACTIVITY_DEFAULT_LIMIT) -> Optional[List[Dict[str, Any]]]:
        """Return cached activity feed if available."""
        payload = self._cache_peek(f"activity:{limit}")
        return payload if payload is not None else None

    def _format_int(self, value: int) -> str:
        return f"{value:,}".replace(",", ".")

    def _format_currency(self, value) -> str:
        amount = Decimal(value or 0)
        quantized = amount.quantize(Decimal("0.01"))
        formatted = f"{quantized:,.2f}"
        formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
        if formatted.endswith(",00"):
            formatted = formatted[:-3]
        return f"{formatted} VND"

    def _format_timestamp(self, moment: Optional[datetime]) -> str:
        if not moment:
            return "Chưa xác định"
        try:
            localized = timezone.localtime(moment)
        except Exception:
            localized = moment
        return localized.strftime("%d/%m/%Y %H:%M")

    def _masked_value(self, value: str) -> str:
        return value if not self.mask_finance else MASKED_PLACEHOLDER

    def _month_start(self, months_back: int) -> datetime:
        month = self.now.month - months_back
        year = self.now.year
        while month <= 0:
            month += 12
            year -= 1
        return datetime(year, month, 1, tzinfo=self.tz)

    def get_kpis(self) -> Dict[str, Any]:
        cache_key = self._cache_key("kpis")
        payload = self._cache_get(cache_key)
        if payload is not None:
            return payload

        course_stats = self._course_summary
        graduate_stats = self._graduate_summary
        teacher_stats = self._teacher_summary

        active_students = graduate_stats.get("active") or 0
        new_term_students = graduate_stats.get("new_term") or 0
        active_teachers = teacher_stats.get("active") or 0
        total_teachers = teacher_stats.get("total") or 0
        mtd_total = Decimal(course_stats.get("mtd") or 0)
        testimonials = graduate_stats.get("testimonials") or 0
        avg_rating = Decimal(graduate_stats.get("avg_rating") or 0)

        cards = [
            {
                "id": "students",
                "title": "Học viên",
                "value": self._format_int(active_students),
                "meta": f"+{self._format_int(new_term_students)} trong tháng",
                "icon": "fa-user-graduate",
                "accent": "emerald",
            },
            {
                "id": "teachers",
                "title": "Giảng viên",
                "value": self._format_int(active_teachers),
                "meta": f"Tổng: {self._format_int(total_teachers)}",
                "icon": "fa-person-chalkboard",
                "accent": "sky",
            },
            {
                "id": "revenue",
                "title": "Doanh thu tháng",
                "value": self._masked_value(self._format_currency(mtd_total)),
                "meta": f"{self._format_int(testimonials)} lời chứng thực mới",
                "icon": "fa-coins",
                "accent": "violet",
            },
        ]

        data = {"cards": cards, "generated_at": self.now}
        self._cache_set(cache_key, data, self.KPI_CACHE_TIMEOUT)
        return data

    def get_chart_payload(self) -> Dict[str, str]:
        cache_key = self._cache_key("charts")
        payload = self._cache_get(cache_key)
        if payload is not None:
            return payload

        months_back = 5
        range_start = self._month_start(months_back)

        revenue_map = {
            entry["period"].date(): float(entry["total"] or 0)
            for entry in (
                Course.objects.filter(created_at__gte=range_start)
                .annotate(period=TruncMonth("created_at"))
                .values("period")
                .annotate(total=Sum("price"))
            )
        }

        registration_map = {
            entry["period"].date(): int(entry["count"])
            for entry in (
                OutstandingGraduate.objects.filter(created_at__gte=range_start)
                .annotate(period=TruncMonth("created_at"))
                .values("period")
                .annotate(count=Count("id"))
            )
        }

        completion_map = {
            entry["period"].date(): int(entry["count"])
            for entry in (
                OutstandingGraduate.objects.filter(
                    publish_at__isnull=False, publish_at__gte=range_start
                )
                .annotate(period=TruncMonth("publish_at"))
                .values("period")
                .annotate(count=Count("id"))
            )
        }

        labels: List[str] = []
        revenue_values: List[float] = []
        registrations: List[int] = []
        completions: List[int] = []

        for offset in range(months_back, -1, -1):
            start = self._month_start(offset)
            period_date = start.date()
            labels.append(start.strftime("%m/%Y"))
            revenue_values.append(round(revenue_map.get(period_date, 0), 2))
            registrations.append(registration_map.get(period_date, 0))
            completions.append(completion_map.get(period_date, 0))

        revenue_chart = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Doanh thu (VND)",
                        "data": revenue_values,
                        "backgroundColor": "rgba(79, 70, 229, 0.85)",
                        "borderRadius": 10,
                    }
                ],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "grid": {"color": "rgba(148, 163, 184, 0.2)"},
                    },
                    "x": {
                        "grid": {"display": False},
                    },
                },
                "plugins": {
                    "legend": {"display": False},
                },
            },
        }

        enrollment_chart = {
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Đăng ký",
                        "data": registrations,
                        "borderColor": "#38bdf8",
                        "backgroundColor": "rgba(56, 189, 248, 0.25)",
                        "tension": 0.35,
                        "fill": True,
                    },
                    {
                        "label": "Hoàn thành",
                        "data": completions,
                        "borderColor": "#22c55e",
                        "backgroundColor": "rgba(34, 197, 94, 0.2)",
                        "tension": 0.35,
                        "fill": True,
                    },
                ],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {"legend": {"position": "bottom"}},
                "scales": {
                    "y": {"beginAtZero": True, "grid": {"color": "rgba(148, 163, 184, 0.2)"}},
                    "x": {"grid": {"display": False}},
                },
            },
        }

        serialized = {
            "revenue": json.dumps(revenue_chart, ensure_ascii=False),
            "enrollment": json.dumps(enrollment_chart, ensure_ascii=False),
        }
        self._cache_set(cache_key, serialized, self.CHART_CACHE_TIMEOUT)
        return serialized

    def get_activity_feed(self, limit: int = ACTIVITY_DEFAULT_LIMIT) -> List[Dict[str, Any]]:
        cache_key = self._cache_key(f"activity:{limit}")
        payload = self._cache_get(cache_key)
        if payload is not None:
            return payload

        limit = max(limit, 1)
        events: List[Dict[str, Any]] = []

        student_rows = list(
            OutstandingGraduate.objects.order_by("-created_at")
            .values("id", "student_name", "course_name", "created_at")[:limit]
        )
        for student in student_rows:
            events.append(
                {
                    "id": f"student-{student['id']}",
                    "icon": "fa-user-plus",
                    "badge": "Học viên",
                    "title": f"Học viên mới: {student.get('student_name') or 'Chưa rõ'}",
                    "subtitle": student.get("course_name") or "Đăng ký mới",
                    "date": student.get("created_at") or self.now,
                }
            )

        completed_rows = list(
            OutstandingGraduate.objects.filter(publish_at__isnull=False)
            .order_by("-publish_at")
            .values("id", "student_name", "course_name", "publish_at", "updated_at")[:limit]
        )
        for completed in completed_rows:
            events.append(
                {
                    "id": f"completed-{completed['id']}",
                    "icon": "fa-graduation-cap",
                    "badge": "Hoàn thành",
                    "title": f"Tốt nghiệp: {completed.get('student_name') or 'Học viên'}",
                    "subtitle": completed.get("course_name") or "Hoàn thành khóa học",
                    "date": completed.get("publish_at") or completed.get("updated_at") or self.now,
                }
            )

        course_rows = list(
            Course.objects.filter(is_active=False)
            .order_by("created_at")
            .values("id", "title", "level", "created_at")[:limit]
        )
        for course in course_rows:
            events.append(
                {
                    "id": f"course-{course['id']}",
                    "icon": "fa-calendar-days",
                    "badge": "Khóa học",
                    "title": f"Lớp sắp khai giảng: {course.get('title')}",
                    "subtitle": course.get("level") or "Đang xếp lịch",
                    "date": course.get("created_at") or self.now,
                }
            )

        teacher_limit = max(limit // 2, 1)
        teacher_rows = list(
            Teacher.objects.order_by("-created_at")
            .values("id", "full_name", "specialization", "created_at")[:teacher_limit]
        )
        for teacher in teacher_rows:
            events.append(
                {
                    "id": f"teacher-{teacher['id']}",
                    "icon": "fa-person-chalkboard",
                    "badge": "Giảng viên",
                    "title": f"Giảng viên mới: {teacher.get('full_name') or 'Chưa rõ'}",
                    "subtitle": teacher.get("specialization") or "Bổ sung vào đội ngũ",
                    "date": teacher.get("created_at") or self.now,
                }
            )

        events.sort(key=lambda item: item["date"] or self.now, reverse=True)
        trimmed = events[:limit]

        feed: List[Dict[str, Any]] = []
        for item in trimmed:
            feed.append(
                {
                    "icon": item["icon"],
                    "badge": item["badge"],
                    "title": item["title"],
                    "subtitle": item["subtitle"],
                    "time": self._format_timestamp(item["date"]),
                }
            )

        self._cache_set(cache_key, feed, self.ALERT_CACHE_TIMEOUT)
        return feed

@login_required
def admin_overview(request: HttpRequest) -> HttpResponse:
    """Render the overview shell; fragments are delivered via HTMX."""

    service = AdminOverviewService(request.user)
    summary_payload = service.peek_kpis()
    chart_payload = service.peek_charts()
    activity_feed = service.peek_activity_feed()

    summary_cards: Optional[List[Dict[str, Any]]]
    summary_generated_at: Optional[datetime]
    if summary_payload is not None:
        summary_cards = summary_payload.get("cards")
        summary_generated_at = summary_payload.get("generated_at")
    else:
        summary_cards = None
        summary_generated_at = None

    charts_payload = chart_payload if chart_payload is not None else None
    activity_feed_payload = activity_feed if activity_feed is not None else None

    context = {
        "support_unread_count": len(activity_feed or []),
        "notification_unread_count": len(activity_feed or []),
        "summary_refresh_interval": service.KPI_CACHE_TIMEOUT,
        "chart_refresh_interval": service.CHART_CACHE_TIMEOUT,
        "activity_refresh_interval": service.ALERT_CACHE_TIMEOUT,
        "summary_cards": summary_cards,
        "summary_generated_at": summary_generated_at,
        "charts": charts_payload,
        "activity_feed": activity_feed_payload,
    }
    context.update(_get_admin_footer_context())
    return render(request, "admin/overview.html", context)


@login_required
def admin_overview_kpis(request: HttpRequest) -> HttpResponse:
    service = AdminOverviewService(request.user)
    payload = service.get_kpis()
    context = {
        "cards": payload["cards"],
        "generated_at": payload["generated_at"],
    }
    return render(request, "admin/partials/overview_kpis.html", context)


@login_required
def admin_overview_trends(request: HttpRequest) -> HttpResponse:
    service = AdminOverviewService(request.user)
    context = {"charts": service.get_chart_payload()}
    return render(request, "admin/partials/overview_trends.html", context)


@login_required
def admin_overview_alerts(request: HttpRequest) -> HttpResponse:
    service = AdminOverviewService(request.user)
    context = {"activities": service.get_activity_feed()}
    return render(request, "admin/partials/overview_alerts.html", context)


