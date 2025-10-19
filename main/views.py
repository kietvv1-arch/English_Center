from datetime import date
from typing import Iterable, List, Sequence

from django.db.models import Q, QuerySet
from django.contrib.auth import authenticate, login as auth_login
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.utils import timezone
from django.urls import reverse
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


DEFAULT_HERO_SETTING = {
    "eyebrow": "Global English",
    "typed_text": "Mở ra thế giới với tiếng Anh",
    "subtitle": (
        "Lộ trình luyện tập cá nhân hóa, lớp học tương tác và hệ thống theo dõi tiến độ"
        " giúp bạn tự tin giao tiếp trong mọi bối cảnh toàn cầu."
    ),
    "primary_cta_label": "Liên hệ tư vấn",
    "primary_cta_href": "#advisory",
    "secondary_cta_label": "Xem video giới thiệu",
    "secondary_cta_href": "#intro-video",
}

DEFAULT_HERO_HIGHLIGHTS = [
    {
        "icon": "fas fa-graduation-cap",
        "title": "Giảng viên bản ngữ",
        "description": (
            "Đội ngũ chuyên gia sở hữu chứng chỉ sư phạm quốc tế, đồng hành cùng bạn."
        ),
    },
    {
        "icon": "fas fa-chalkboard",
        "title": "Lớp học tương tác",
        "description": (
            "Ứng dụng công nghệ hiện đại và phương pháp đào tạo chú trọng thực hành."
        ),
    },
    {
        "icon": "fas fa-certificate",
        "title": "Chứng chỉ toàn cầu",
        "description": (
            "Cam kết thành tích với hệ thống kiểm tra chuẩn quốc tế và giám sát tiến độ."
        ),
    },
]

DEFAULT_NAV_LINKS = [
    {"label": "Giới thiệu", "href": "#features"},
    {"label": "Khóa học", "href": "#courses"},
    {"label": "Giảng viên", "href": "#teachers"},
    {"label": "Học viên xuất sắc", "href": "#graduates"},
    {"label": "Cảm nhận", "href": "#testimonials"},
    {"label": "Thành tựu", "href": "#achievements"},
]

DEFAULT_FOOTER_PROGRAMS = [
    {"label": "Tiếng Anh giao tiếp", "href": "#courses"},
    {"label": "Tiếng Anh thương mại", "href": "#courses"},
    {"label": "Luyện thi IELTS", "href": "#courses"},
    {"label": "Tiếng Anh trẻ em", "href": "#courses"},
]

DEFAULT_FOOTER_ABOUT = [
    {"label": "Giới thiệu", "href": "#features"},
    {"label": "Đội ngũ giảng viên", "href": "#teachers"},
    {"label": "Phương pháp đào tạo", "href": "#features"},
    {"label": "Cơ sở vật chất", "href": "#features"},
]

def _calculate_experience_years(start_date):
    if not start_date:
        return None
    today = date.today()
    years = today.year - start_date.year - (
        (today.month, today.day) < (start_date.month, start_date.day)
    )
    return max(years, 0)


def _get_active_reasons() -> QuerySet[Reason]:
    return Reason.objects.filter(is_active=True).order_by("order", "id")


def _get_hero_setting() -> dict:
    hero_setting = DEFAULT_HERO_SETTING.copy()
    hero_obj = (
        HomeSetting.objects.filter(is_active=True).order_by("order", "id").first()
    )
    if not hero_obj:
        return hero_setting

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
            hero_setting[key] = value

    if not hero_setting["secondary_cta_label"]:
        hero_setting["secondary_cta_href"] = "#"
    return hero_setting


def _serialize_highlights(cards: Sequence[HeroHighlight]) -> List[dict]:
    highlights = [
        {"icon": card.icon, "title": card.title, "description": card.description}
        for card in cards
    ]
    return highlights or list(DEFAULT_HERO_HIGHLIGHTS)


def _build_nav_links(*, location: str, default: Sequence[dict]) -> List[dict]:
    links = NavigationLink.objects.filter(
        location=location, is_active=True
    ).order_by("order", "id")
    serialized = [{"label": link.label, "href": link.href or "#"} for link in links]
    return serialized or list(default)


def _get_teacher_queryset() -> QuerySet[Teacher]:
    queryset = Teacher.objects.filter(status="Active").order_by("order", "id")
    featured = getattr(Teacher.objects, "featured", None)
    if callable(featured):
        try:
            queryset = featured().order_by("order", "id")
        except Exception:
            pass
    return queryset


def _serialize_teachers(teachers_qs: Iterable[Teacher]) -> List[dict]:
    serialized = []
    for teacher in teachers_qs:
        serialized.append(
            {
                "name": teacher.full_name,
                "role": teacher.specialization,
                "bio": teacher.bio,
                "experience_years": _calculate_experience_years(teacher.start_date),
                "avatar_url": getattr(teacher, "avatar_url", None),
            }
        )
    return serialized


def _serialize_achievements(
    achievements: Iterable[Achievement],
) -> List[dict]:
    cards: List[dict] = []
    for achievement in achievements:
        cards.append(
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
    return cards 


def _serialize_courses(courses_qs: Iterable[Course]) -> List[dict]:
    level_map = dict(getattr(Course, "LEVEL_CHOICES", []))
    return [
        {
            "title": course.title,
            "description": course.description,
            "level": level_map.get(course.level, course.level),
        }
        for course in courses_qs
    ]


def _serialize_graduates(
    graduates_qs: Iterable[OutstandingGraduate],
) -> List[dict]:
    serialized = []
    for graduate in graduates_qs:
        serialized.append(
            {
                "name": graduate.student_name,
                "course": graduate.course_name,
                "score": getattr(graduate, "score_display", None),
                "testimonial": graduate.testimonial,
                "photo_url": getattr(graduate, "photo_url", None)
                or static("public/images/graduate/placeholder.svg"),
            }
        )
    return serialized


def _serialize_testimonials(stories_qs: Iterable[SuccessStory]) -> List[dict]:
    testimonials = []
    for story in stories_qs:
        initials = "".join(
            part[:1] for part in (story.student_name or "").split() if part
        )
        testimonials.append(
            {
                "quote": (story.story or "")[:160],
                "initials": initials.upper()[:2] or "HV",
                "name": story.student_name,
                "program": story.course_name,
            }
        )
    return testimonials


def home(request):
    now = timezone.now()

    hero_highlights_qs = HeroHighlight.objects.filter(is_active=True).order_by(
        "order", "id"
    )
    teacher_queryset = _get_teacher_queryset().only(
        "full_name", "specialization", "bio", "start_date", "avatar"
    )
    courses_qs = (
        Course.objects.filter(is_active=True)
        .only("id", "title", "description", "level")
        .order_by("id")
    )
    graduates_qs = (
        OutstandingGraduate.objects.filter(is_active=True)
        .filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=now),
            Q(unpublish_at__isnull=True) | Q(unpublish_at__gt=now),
        )
        .order_by("order", "id")
    )
    stories_qs = SuccessStory.objects.filter(is_approved=True).order_by(
        "order", "-created_at"
    )

    achievements_qs = (
        Achievement.objects.filter(is_active=True)
        .filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=now),
            Q(unpublish_at__isnull=True) | Q(unpublish_at__gt=now),
        )
        .order_by("order", "id")
    )

    context = {
        "nav_links": _build_nav_links(
            location=NavigationLink.LOCATION_HEADER, default=DEFAULT_NAV_LINKS
        ),
        "hero_setting": _get_hero_setting(),
        "hero_highlights": _serialize_highlights(hero_highlights_qs),
        "reasons": _get_active_reasons(),
        "teachers": _serialize_teachers(teacher_queryset),
        "achievements": _serialize_achievements(achievements_qs),
        "stats": _serialize_achievements(achievements_qs),
        "courses": _serialize_courses(courses_qs),
        "graduates": _serialize_graduates(graduates_qs),
        "testimonials": _serialize_testimonials(stories_qs),
        "footer_programs": _build_nav_links(
            location=NavigationLink.LOCATION_FOOTER_PROGRAM,
            default=DEFAULT_FOOTER_PROGRAMS,
        ),
        "footer_about": _build_nav_links(
            location=NavigationLink.LOCATION_FOOTER_ABOUT,
            default=DEFAULT_FOOTER_ABOUT,
        ),
    }
    return render(request, "public/home.html", context)


def login(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect("admin:index")
        return redirect("main:home")

    error_message = None
    username_value = ""
    remember_checked = False
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if next_url and not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = ""

    if request.method == "POST":
        username_value = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        remember_checked = request.POST.get("remember") == "on"

        user = authenticate(request, username=username_value, password=password)
        if user is not None:
            auth_login(request, user)
            if not remember_checked:
                request.session.set_expiry(0)

            admin_index = reverse("admin:index")
            if user.is_staff or user.is_superuser:
                return redirect(admin_index)

            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("main:home")

        error_message = "Tên đăng nhập hoặc mật khẩu không đúng. Vui lòng thử lại."

    context = {
        "error": error_message,
        "username_value": username_value,
        "next": next_url,
        "remember_checked": remember_checked,
    }
    return render(request, "public/login.html", context)
