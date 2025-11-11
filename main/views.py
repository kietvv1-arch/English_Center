"""Views powering the public landing pages and a lightweight admin dashboard.

The file is organised into four logical blocks:
    1.  Constants and helper utilities shared across views.
    2.  A context builder dedicated to aggregating home-page data.
    3.  Public-facing views (login, home, fragments).
    4.  Admin helpers used by the custom dashboard.

Each section is kept small and documented so new teammates can trace the
data flow without jumping between modules.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, TypedDict
from functools import cached_property
from threading import Lock, Thread
from time import monotonic

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count, Q, QuerySet, Sum
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
    Student,
    StudentPayment,
    Reason,
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


# Dữ liệu mặc định (hiển thị khi DB trống) — tiếng Việt

DEFAULT_HERO_SETTING: Dict[str, str] = {
    "eyebrow": "Global English",
    "typed_text": "Mở ra thế giới với tiếng Anh",
    "subtitle": (
        "Huấn luyện cá nhân hoá, lớp học tương tác và theo dõi tiến độ "
        "giúp bạn tự tin trong mọi cuộc trò chuyện."
    ),
    "primary_cta_label": "Liên hệ tư vấn",
    "primary_cta_href": "#advisory",
    "secondary_cta_label": "Xem video giới thiệu",
    "secondary_cta_href": "#intro-video",
}

DEFAULT_HERO_HIGHLIGHTS: List[Dict[str, str]] = [
    {
        "icon": "fas fa-graduation-cap",
        "title": "Giảng viên chuyên gia",
        "description": "Học với giáo viên trình độ bản ngữ và cố vấn giàu kinh nghiệm.",
    },
    {
        "icon": "fas fa-chalkboard-teacher",
        "title": "Lớp học tương tác",
        "description": "Mô hình học kết hợp với workshop trực tiếp và phòng thực hành.",
    },
    {
        "icon": "fas fa-certificate",
        "title": "Chứng chỉ toàn cầu",
        "description": "Học theo chuẩn quốc tế, có công cụ theo dõi tiến độ rõ ràng.",
    },
]

DEFAULT_NAV_LINKS: List[NavLink] = [
    {"label": "Về chúng tôi", "href": "#features"},
    {"label": "Khóa học", "href": "#courses"},
    {"label": "Giảng viên", "href": "#teachers"},
    {"label": "Học viên tiêu biểu", "href": "#graduates"},
    {"label": "Thành tựu", "href": "#achievements"},
]

DEFAULT_FOOTER_PROGRAMS: List[NavLink] = [
    {"label": "Giao tiếp", "href": "#courses"},
    {"label": "Tiếng Anh thương mại", "href": "#courses"},
    {"label": "Luyện thi IELTS", "href": "#courses"},
    {"label": "Tiếng Anh thiếu nhi", "href": "#courses"},
]

DEFAULT_FOOTER_ABOUT: List[NavLink] = [
    {"label": "Giới thiệu", "href": "#features"},
    {"label": "Đội ngũ giảng viên", "href": "#teachers"},
    {"label": "Phương pháp giảng dạy", "href": "#features"},
    {"label": "Cơ sở vật chất", "href": "#features"},
]

DEFAULT_COURSE_ICONS: Dict[str, str] = {
    "Beginner": "fas fa-seedling",
    "Intermediate": "fas fa-chart-line",
    "Advanced": "fas fa-rocket",
    "AllLevels": "fas fa-layer-group",
}

DEFAULT_TEACHER_PLACEHOLDER = "public/images/teachers/teacher-placeholder.svg"

DEFAULT_TEACHER_CARDS: List[Dict[str, Any]] = [
    {
        "name": "Nguyen Minh Anh",
        "role": "IELTS Coach",
        "bio": "Huong dan chien luoc thi IELTS cho hoc vien muon vuot band 7.0.",
        "experience_years": 8,
        "avatar_path": "public/images/teachers/teacher-1.svg",
    },
    {
        "name": "Le Quang Khai",
        "role": "Business English Mentor",
        "bio": "Tap trung vao ky nang giao tiep thuong mai va thuyet trinh.",
        "experience_years": 6,
        "avatar_path": "public/images/teachers/teacher-2.svg",
    },
    {
        "name": "Tran Gia Han",
        "role": "Pronunciation Specialist",
        "bio": "Xay dung phat am chuan va trong am tu nhien trong moi buoi hoc.",
        "experience_years": 10,
        "avatar_path": "public/images/teachers/teacher-3.svg",
    },
]

DEFAULT_GRADUATE_PLACEHOLDER = "public/images/graduate/placeholder.svg"

DEFAULT_GRADUATE_CARDS: List[Dict[str, Any]] = [
    {
        "name": "Tran Bao Lam",
        "achievement": "IELTS 7.5 overall",
        "story": "Hoan thanh lo trinh 6 thang va dat muc tieu duoi su huong dan cua trung tam.",
        "photo_path": "public/images/graduate/graduate-1.svg",
        "photo_alt": "Graduate Tran Bao Lam",
    },
    {
        "name": "Pham Thu Trang",
        "achievement": "TOEIC 905",
        "story": "Tang 255 diem sau 12 tuan nho chuong trinh On Luyen Tang Toc.",
        "photo_path": "public/images/graduate/graduate-2.svg",
        "photo_alt": "Graduate Pham Thu Trang",
    },
    {
        "name": "Nguyen Hoang Long",
        "achievement": "Giao tiep tu tin",
        "story": "Tu tin tham gia hoi nghi quoc te sau khi hoan tat lop Business Communication.",
        "photo_path": "public/images/graduate/graduate-3.svg",
        "photo_alt": "Graduate Nguyen Hoang Long",
    },
]


_fallback_cache: Dict[str, Any] = {}
_warmup_lock = Lock()
_warmup_running = False
_warmup_last_run: Dict[str, float] = {}
_WARMUP_COOLDOWN = 60  # seconds

CHART_RANGE_CHOICES: Sequence[Tuple[str, str, int]] = (
    ("1m", "1 tháng", 0),
    ("6m", "6 tháng", 5),
    ("12m", "1 năm", 11),
)
CHART_RANGE_DEFAULT = "6m"
CHART_RANGE_LOOKUP: Dict[str, int] = {
    key: months_back for key, _label, months_back in CHART_RANGE_CHOICES
}
DEFAULT_CHART_MONTHS: Tuple[int, ...] = tuple(
    sorted({choice[2] for choice in CHART_RANGE_CHOICES})
)


def _calculate_experience_years(start_date):
    if not start_date:
        return None
    today = date.today()
    years = today.year - start_date.year
    if (today.month, today.day) < (start_date.month, start_date.day):
        years -= 1
    return max(years, 0)


def _format_course_duration(duration_hours, lesson_count):
    """
    Trả về chuỗi thân thiện bằng tiếng Việt.
    Ví dụ: '12 buổi • 36 giờ', '36 giờ', '12 buổi', hoặc 'Linh hoạt'.
    """

    BULLET = "\u2022"  

    def _normalize(value):
        try:
            number = float(value)
            if number.is_integer():
                return int(number)
            return round(number, 1)
        except (TypeError, ValueError):
            return None

    hours = _normalize(duration_hours)
    lessons = _normalize(lesson_count)

    parts = []
    if lessons is not None and lessons > 0:
        parts.append(f"{lessons} buổi")
    if hours is not None and hours > 0:
        parts.append(f"{hours} giờ")

    if parts:
        return f" {BULLET} ".join(parts)
    return "Linh hoạt"



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
            "stats": list(achievements),
            "courses": self._serialize_courses(),
            "graduates": self._serialize_graduates(),
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
            avatar_url = getattr(teacher, "avatar_url", None)
            if not avatar_url:
                avatar_field = getattr(teacher, "avatar", None)
                avatar_url = getattr(avatar_field, "url", None) if avatar_field else None
            if not avatar_url:
                avatar_url = static(DEFAULT_TEACHER_PLACEHOLDER)
            payload.append(
                {
                    "name": teacher.full_name,
                    "role": teacher.specialization,
                    "bio": teacher.bio,
                    "experience_years": _calculate_experience_years(teacher.start_date),
                    "avatar_url": avatar_url,
                }
            )
        if payload:
            return payload

        return [
            {
                "name": card["name"],
                "role": card["role"],
                "bio": card.get("bio"),
                "experience_years": card.get("experience_years"),
                "avatar_url": static(card["avatar_path"]),
            }
            for card in DEFAULT_TEACHER_CARDS
        ]

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
    
    def _serialize_graduates(self) -> list[dict]:
        items = []
        for g in self._graduate_queryset():  # đảm bảo hàm này trả OutstandingGraduate đã lọc publish/is_active
            photo_url = getattr(g, "photo_url", None)
            if not photo_url:
                photo_url = static(DEFAULT_GRADUATE_PLACEHOLDER)
            items.append(
                {
                    "name": str(getattr(g, "student_name", "")).strip(),
                    "achievement": (getattr(g, "achievement", "") or "").strip(),
                    "story": (getattr(g, "story", "") or "").strip(),
                    "photo_url": photo_url,
                    "photo_alt": getattr(g, "photo_alt", None),
                }
            )
        if items:
            return items

        return [
            {
                "name": card["name"],
                "achievement": card.get("achievement", ""),
                "story": card.get("story", ""),
                "photo_url": static(card.get("photo_path", DEFAULT_GRADUATE_PLACEHOLDER)),
                "photo_alt": card.get("photo_alt"),
            }
            for card in DEFAULT_GRADUATE_CARDS
        ]


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
    def _payment_summary(self) -> Dict[str, Any]:
        start_month = self._month_start(0)
        start_year = datetime(self.now.year, 1, 1, tzinfo=self.tz)
        confirmed = StudentPayment.objects.confirmed().only("amount", "paid_at")
        monthly = confirmed.filter(paid_at__gte=start_month).aggregate(mtd=Sum("amount"))
        yearly = confirmed.filter(paid_at__gte=start_year).aggregate(ytd=Sum("amount"))
        return {
            "mtd": monthly.get("mtd"),
            "ytd": yearly.get("ytd"),
        }

    @cached_property
    def _student_summary(self) -> Dict[str, Any]:
        start_month = self._month_start(0)
        active = Student.objects.filter(status=Student.Status.ENROLLED).only("id").count()
        new_term = (
            Student.objects.filter(
                Q(enrollment_date__gte=start_month)
                | Q(enrollment_date__isnull=True, created_at__gte=start_month)
            )
            .only("id")
            .count()
        )
        return {"active": active, "new_term": new_term}

    @cached_property
    def _teacher_summary(self) -> Dict[str, Any]:
        queryset = Teacher.objects.only("id")
        active = queryset.filter(status="Active").count()
        total = queryset.count()
        return {"active": active, "total": total}

    def _cache_key(self, slug: str) -> str:
        mask_suffix = "masked" if self.mask_finance else "full"
        return f"admin_overview:{slug}:{mask_suffix}"

    def _cache_get(self, key: str):
        try:
            value = cache.get(key)
        except Exception as exc:  # pragma: no cover - cache backend optional
            logger.warning(
                "overview cache get failed",
                extra={"key": key, "error": str(exc)},
            )
            return _fallback_cache.get(key)
        return value if value is not None else _fallback_cache.get(key)

    def _cache_set(self, key: str, value, timeout: int) -> None:
        try:
            cache.set(key, value, timeout)
        except Exception as exc:  # pragma: no cover - cache backend optional
            logger.warning(
                "overview cache set failed",
                extra={"key": key, "error": str(exc)},
            )
        _fallback_cache[key] = value

    def _cache_peek(self, slug: str):
        """Return cached payload for ``slug`` without recomputing when missing."""
        key = self._cache_key(slug)
        return self._cache_get(key)

    def peek_kpis(self) -> Optional[Dict[str, Any]]:
        """Return cached KPI payload if available."""
        payload = self._cache_peek("kpis")
        return payload if payload is not None else None

    def peek_charts(self, months_back: int) -> Optional[Dict[str, Any]]:
        """Return cached chart payload if available."""
        payload = self._cache_peek(f"charts:{months_back}")
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

        payment_stats = self._payment_summary
        student_stats = self._student_summary
        teacher_stats = self._teacher_summary

        active_students = student_stats.get("active") or 0
        new_term_students = student_stats.get("new_term") or 0
        active_teachers = teacher_stats.get("active") or 0
        total_teachers = teacher_stats.get("total") or 0
        mtd_total = Decimal(payment_stats.get("mtd") or 0)
        ytd_total = Decimal(payment_stats.get("ytd") or 0)
        annual_total_display = self._masked_value(self._format_currency(ytd_total))


        cards = [
            {
                "id": "students",
                "title": "Học viên",
                "value": self._format_int(active_students),
                "meta": f"+{self._format_int(new_term_students)} học viên mới trong tháng",
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
                "meta": f"Doanh thu năm: {annual_total_display}",
                "icon": "fa-coins",
                "accent": "violet",
            },
        ]

        data = {"cards": cards, "generated_at": self.now}
        self._cache_set(cache_key, data, self.KPI_CACHE_TIMEOUT)
        return data

    def _get_weekly_chart_payload(self, cache_key: str) -> Dict[str, str]:
        spans: List[Tuple[datetime, datetime]] = []
        end = self.now
        for _ in range(4):
            start = end - timedelta(days=7)
            spans.append((start, end))
            end = start
        spans.reverse()

        range_start = spans[0][0]
        labels: List[str] = []
        revenue_values = [0.0] * len(spans)
        registrations = [0] * len(spans)
        completions = [0] * len(spans)

        for start, end in spans:
            start_local = timezone.localtime(start)
            end_local = timezone.localtime(end - timedelta(seconds=1))
            labels.append(
                f"{start_local.strftime('%d/%m')} - {end_local.strftime('%d/%m')}"
            )

        payments = (
            StudentPayment.objects.confirmed()
            .filter(paid_at__gte=range_start)
            .values_list("paid_at", "amount")
        )
        for paid_at, amount in payments.iterator(chunk_size=512):
            if not paid_at:
                continue
            for idx, (start, end) in enumerate(spans):
                if start <= paid_at < end:
                    revenue_values[idx] += float(amount or 0)
                    break

        registration_qs = (
            Student.objects.filter(created_at__gte=range_start)
            .only("created_at")
            .values_list("created_at", flat=True)
        )
        for created_at in registration_qs.iterator(chunk_size=512):
            if not created_at:
                continue
            for idx, (start, end) in enumerate(spans):
                if start <= created_at < end:
                    registrations[idx] += 1
                    break

        completion_qs = (
            Student.objects.filter(
                status=Student.Status.COMPLETED, updated_at__gte=range_start
            )
            .only("updated_at")
            .values_list("updated_at", flat=True)
        )
        for updated_at in completion_qs.iterator(chunk_size=512):
            if not updated_at:
                continue
            for idx, (start, end) in enumerate(spans):
                if start <= updated_at < end:
                    completions[idx] += 1
                    break

        revenue_values = [round(value, 2) for value in revenue_values]

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
                        "backgroundColor": "rgba(34, 197, 94, 0.25)",
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
                    "y": {
                        "beginAtZero": True,
                        "grid": {"color": "rgba(148, 163, 184, 0.2)"},
                    },
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

    def get_chart_payload(
        self, months_back: int = CHART_RANGE_LOOKUP[CHART_RANGE_DEFAULT]
    ) -> Dict[str, str]:
        cache_key = self._cache_key(f"charts:{months_back}")
        payload = self._cache_get(cache_key)
        if payload is not None:
            return payload

        if months_back == 0:
            return self._get_weekly_chart_payload(cache_key)

        range_start = self._month_start(months_back)

        revenue_map: Dict[str, float] = {}
        payment_iterable = StudentPayment.objects.confirmed().filter(
            paid_at__gte=range_start
        ).values_list("paid_at", "amount")
        for paid_at, amount in payment_iterable.iterator(chunk_size=512):
            if not paid_at:
                continue
            period = datetime(paid_at.year, paid_at.month, 1, tzinfo=paid_at.tzinfo)
            key = period.date().isoformat()
            revenue_map[key] = revenue_map.get(key, 0.0) + float(amount or 0)

        registration_map: Dict[str, int] = {}
        completion_map: Dict[str, int] = {}
        registration_iterable = (
            Student.objects.filter(created_at__gte=range_start)
            .only("created_at")
            .values_list("created_at", flat=True)
        )
        for created_at in registration_iterable.iterator(chunk_size=512):
            if not created_at:
                continue
            period = datetime(created_at.year, created_at.month, 1, tzinfo=created_at.tzinfo)
            key = period.date().isoformat()
            registration_map[key] = registration_map.get(key, 0) + 1

        completion_iterable = (
            Student.objects.filter(
                status=Student.Status.COMPLETED, updated_at__gte=range_start
            )
            .only("updated_at")
            .values_list("updated_at", flat=True)
        )
        for updated_at in completion_iterable.iterator(chunk_size=512):
            if not updated_at:
                continue
            period = datetime(updated_at.year, updated_at.month, 1, tzinfo=updated_at.tzinfo)
            key = period.date().isoformat()
            completion_map[key] = completion_map.get(key, 0) + 1


        labels: List[str] = []
        revenue_values: List[float] = []
        registrations: List[int] = []
        completions: List[int] = []

        for offset in range(months_back, -1, -1):
            start = self._month_start(offset)
            period_date = start.date().isoformat()
            labels.append(start.strftime("%m/%Y"))
            revenue_values.append(round(revenue_map.get(period_date, 0.0), 2))
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
                        "backgroundColor": "rgba(34, 197, 94, 0.25)",
                        "tension": 0.35,
                        "fill": True,
                    }
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

        student_rows = (
            Student.objects.order_by("-created_at")
            .values("id", "full_name", "created_at")[:limit]
        )
        for grad in student_rows:
            created_at = grad.get("created_at")
            events.append(
                {
                    "id": f"student-{grad.get('id')}",
                    "icon": "fa-user-plus",
                    "badge": "Học viên",
                    "title": f"Học viên mới: {grad.get('full_name') or 'Chưa rõ'}",
                    "subtitle": created_at or "Đăng ký mới",
                    "date": created_at or self.now,
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


class _OverviewWarmupUser:
    """Minimal user object to warm cache with full access."""

    is_superuser = True
    is_staff = True

    def has_perm(self, perm: str) -> bool:  # pragma: no cover - trivial
        return True


def warm_admin_overview_cache(
    *, force: bool = False, chart_ranges: Optional[Iterable[int]] = None
) -> None:
    """
    Precompute KPI, chart, and activity payloads in cache.

    When ``force`` is False, the warm-up is guarded by a short-lived cache lock
    to avoid duplicate work triggered by bursty signals.
    """

    ranges = tuple(sorted(set(chart_ranges or DEFAULT_CHART_MONTHS)))
    scope_suffix = ",".join(str(item) for item in ranges) or "default"
    lock_key = f"admin_overview:warm_lock:{scope_suffix}"
    acquired = True
    lock_usable = True
    if not force:
        try:
            acquired = cache.add(lock_key, True, timeout=15)
        except Exception as exc:  # pragma: no cover - cache backend optional
            lock_usable = False
            logger.warning("admin overview warm lock failed", extra={"error": str(exc)})
            acquired = True
    if not acquired:
        return

    try:
        service = AdminOverviewService(_OverviewWarmupUser())
        service.get_kpis()
        for months_back in ranges:
            service.get_chart_payload(months_back=months_back)
        service.get_activity_feed()
    except Exception as exc:  # pragma: no cover - best effort cache warm
        logger.warning("admin overview warm failed", extra={"error": str(exc)})
    finally:
        if not force and lock_usable:
            try:
                cache.delete(lock_key)
            except Exception as exc:  # pragma: no cover - cache backend optional
                logger.warning(
                    "admin overview warm lock release failed",
                    extra={"error": str(exc)},
                )


def trigger_overview_warmup_async(
    *, force: bool = False, chart_ranges: Optional[Iterable[int]] = None
) -> None:
    """Schedule a background warm-up if one is not already running."""

    ranges = tuple(sorted(set(chart_ranges or DEFAULT_CHART_MONTHS)))
    scope_key = ",".join(str(item) for item in ranges) or "default"

    if not force and not _warmup_throttle(scope_key):
        return

    global _warmup_running
    with _warmup_lock:
        if _warmup_running:
            return
        _warmup_running = True

    def _runner():
        try:
            warm_admin_overview_cache(force=force, chart_ranges=ranges)
        finally:
            global _warmup_running
            with _warmup_lock:
                _warmup_running = False

    Thread(
        target=_runner,
        name=f"overview-cache-warmup-{scope_key}",
        daemon=True,
    ).start()


def _warmup_throttle(scope_key: str) -> bool:
    """Return True when a warm-up should proceed, honoring cooldown."""

    global _warmup_last_run
    now = monotonic()
    last_run = _warmup_last_run.get(scope_key, 0.0)
    if now - last_run < _WARMUP_COOLDOWN:
        return False

    cache_key = f"admin_overview:warm_recent:{scope_key}"
    try:
        cached_added = cache.add(cache_key, True, timeout=_WARMUP_COOLDOWN)
    except Exception as exc:  # pragma: no cover - cache backend optional
        logger.warning("overview warm throttle cache failed", extra={"error": str(exc)})
        cached_added = True

    if cached_added is False:
        return False

    _warmup_last_run[scope_key] = now
    return True


@login_required
def admin_overview(request: HttpRequest) -> HttpResponse:
    """Render the overview shell; fragments are delivered via HTMX."""

    service = AdminOverviewService(request.user)
    context = {
        "support_unread_count": 0,
        "notification_unread_count": 0,
        "summary_refresh_interval": service.KPI_CACHE_TIMEOUT,
        "chart_refresh_interval": service.CHART_CACHE_TIMEOUT,
        "activity_refresh_interval": service.ALERT_CACHE_TIMEOUT,
        "summary_cards": None,
        "summary_generated_at": None,
        "charts": None,
        "activity_feed": None,
        "chart_range_selected": CHART_RANGE_DEFAULT,
        "chart_range_options": CHART_RANGE_CHOICES,
    }
    context.update(_get_admin_footer_context())
    return render(request, "admin/overview.html", context)


@login_required
def admin_overview_kpis(request: HttpRequest) -> HttpResponse:
    service = AdminOverviewService(request.user)
    payload = service.peek_kpis()
    if payload is None:
        trigger_overview_warmup_async()
        response = render(request, "admin/partials/overview_kpis_skeleton.html")
        response["HX-Trigger"] = json.dumps(
            {"overview:lazy-reload": {"target": "#overview-summary", "delay": 1200}}
        )
        return response

    context = {
        "cards": payload["cards"],
        "generated_at": payload["generated_at"],
    }
    return render(request, "admin/partials/overview_kpis.html", context)


@login_required
def admin_overview_trends(request: HttpRequest) -> HttpResponse:
    service = AdminOverviewService(request.user)
    range_key = request.GET.get("range", CHART_RANGE_DEFAULT)
    if range_key not in CHART_RANGE_LOOKUP:
        range_key = CHART_RANGE_DEFAULT
    months_back = CHART_RANGE_LOOKUP[range_key]
    payload = service.peek_charts(months_back)
    if payload is None:
        trigger_overview_warmup_async(chart_ranges=(months_back,))
        response = render(request, "admin/partials/overview_trends_skeleton.html")
        response["HX-Trigger"] = json.dumps(
            {
                "overview:update-range": {"range": range_key},
                "overview:lazy-reload": {
                    "target": "#overview-charts",
                    "delay": 1500,
                    "params": {"range": range_key},
                },
            }
        )
        return response
    context = {"charts": payload}
    response = render(request, "admin/partials/overview_trends.html", context)
    response["HX-Trigger"] = json.dumps({"overview:update-range": {"range": range_key}})
    return response


@login_required
def admin_overview_alerts(request: HttpRequest) -> HttpResponse:
    service = AdminOverviewService(request.user)
    payload = service.peek_activity_feed()
    if payload is None:
        trigger_overview_warmup_async()
        response = render(request, "admin/partials/overview_alerts_skeleton.html")
        response["HX-Trigger"] = json.dumps(
            {"overview:lazy-reload": {"target": "#overview-activity", "delay": 1500}}
        )
        return response
    context = {"activities": payload}
    return render(request, "admin/partials/overview_alerts.html", context)


