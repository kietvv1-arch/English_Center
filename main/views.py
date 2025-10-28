from datetime import date
from typing import Iterable, List, Sequence

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.db.models import Q, QuerySet
from django.http import Http404
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

# ================= Login =================#

def login(request):
    """Xử lý đăng nhập người dùng cho trang công khai.

    - Chuyển hướng nhân viên/superuser đến trang admin khi đã xác thực.
    - Hỗ trợ tham số `next` an toàn bằng url_has_allowed_host_and_scheme.
    - Nếu không chọn "remember", phiên làm việc sẽ hết hạn khi đóng trình duyệt.

    Đầu vào:
        request: Django HttpRequest
    Đầu ra:
        HttpResponse chuyển hướng đến trang thích hợp hoặc hiển thị giao diện đăng nhập.
    """
    # If user already logged in, send them to appropriate page
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect("admin:index")
        return redirect("main:home")

    error_message = None
    username_value = ""
    remember_checked = False

    # `next` may come from either POST or GET
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    # Ensure the `next` target is safe
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
            # If user didn't choose remember, expire session on browser close
            if not remember_checked:
                request.session.set_expiry(0)

            admin_index = reverse("admin:")
            if user.is_staff or user.is_superuser:
                return redirect(admin_index)

            # Redirect to safe `next` or homepage
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("main:home")

        # Provide a friendly message in Vietnamese
        error_message = "Tên đăng nhập hoặc mật khẩu không đúng. Vui lòng thử lại."

    context = {
        "error": error_message,
        "username_value": username_value,
        "next": next_url,
        "remember_checked": remember_checked,
    }
    return render(request, "public/login.html", context)


#================= Home =================#

# Cài đặt mặc định cho phần hero khi không có HomeSetting nào đang hoạt động
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

# Thẻ dự phòng cho điểm nổi bật hero khi không có trong CSDL
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

# Liên kết điều hướng và footer mặc định dùng làm dự phòng
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

DEFAULT_COURSE_ICONS = {
    "Beginner": "fas fa-seedling",
    "Intermediate": "fas fa-chart-line",
    "Advanced": "fas fa-rocket",
    "AllLevels": "fas fa-layer-group",
}


#================= Helper Functions =================#

def _calculate_experience_years(start_date):
    """Tính số năm kinh nghiệm đầy đủ kể từ `start_date`.

    Trả về None khi start_date không hợp lệ. Đảm bảo kết quả không âm.
    """
    if not start_date:
        return None
    today = date.today()
    years = today.year - start_date.year - (
        (today.month, today.day) < (start_date.month, start_date.day)
    )
    return max(years, 0)


def _get_active_reasons() -> QuerySet[Reason]:
    """Trả về danh sách `Reason` đang hoạt động, sắp xếp theo `order` rồi đến `id`.

    Đây là các thẻ lý do/tính năng nhỏ được hiển thị trên trang chủ.
    """
    return Reason.objects.filter(is_active=True).order_by("order", "id")


def _get_hero_setting() -> dict:
    """Xây dựng dữ liệu phần hero từ HomeSetting đang hoạt động hoặc sử dụng giá trị mặc định.

    Kết hợp các giá trị đã lưu (nếu có) vào DEFAULT_HERO_SETTING.
    """
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

    # Ensure href is safe even when secondary label absent
    if not hero_setting["secondary_cta_label"]:
        hero_setting["secondary_cta_href"] = "#"
    return hero_setting


def _serialize_highlights(cards: Sequence[HeroHighlight]) -> List[dict]:
    """Chuyển đổi danh sách HeroHighlight thành list các dict cho template.

    Trả về highlights mặc định khi danh sách trống.
    """
    highlights = [
        {"icon": card.icon, "title": card.title, "description": card.description}
        for card in cards
    ]
    return highlights or list(DEFAULT_HERO_HIGHLIGHTS)


def _build_nav_links(*, location: str, default: Sequence[dict]) -> List[dict]:
    """Trả về các NavigationLink đang hoạt động cho vị trí được chỉ định.

    `location` phải khớp với các giá trị được định nghĩa trong model NavigationLink.
    Sử dụng `default` khi không có liên kết nào được cấu hình trong DB.
    """
    links = NavigationLink.objects.filter(
        location=location, is_active=True
    ).order_by("order", "id")
    serialized = [{"label": link.label, "href": link.href or "#"} for link in links]
    return serialized or list(default)


def _get_teacher_queryset() -> QuerySet[Teacher]:
    """Trả về danh sách giáo viên để hiển thị công khai.

    Sử dụng phương thức `featured()` nếu có; nếu không sẽ trả về 
    giáo viên có trạng thái "Active".
    """
    queryset = Teacher.objects.filter(status="Active").order_by("order", "id")
    featured = getattr(Teacher.objects, "featured", None)
    if callable(featured):
        try:
            queryset = featured().order_by("order", "id")
        except Exception:
            # If featured() fails for any reason, silently fall back to default
            pass
    return queryset


def _serialize_teachers(teachers_qs: Iterable[Teacher]) -> List[dict]:
    """Chuyển đổi đối tượng giáo viên thành dict đơn giản cho frontend.

    Mỗi giáo viên sau chuyển đổi gồm: name, role, bio, experience_years, avatar_url
    """
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
    """Chuyển đổi thành tích thành các thẻ để hiển thị trên trang chủ hoặc admin.

    Giữ nguyên các helper hiển thị (ví dụ: get_kind_display) và các trường hình ảnh/số liệu.
    """
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


def _format_course_duration(duration_hours, lesson_count):
    """TAo chuoi thoi luong hien thi du tren so gio hoac so buoi neu co."""
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
        return f"{lessons} buổi • {hours} giờ"
    if hours:
        return f"{hours} giờ"
    if lessons:
        return f"{lessons} buổi"
    return "Linh hoạt"


def _serialize_courses(courses_qs: Iterable[Course]) -> List[dict]:
    """Chuyen doi danh sach khoa hoc thanh dict don gian.

    Anh xa `level` sang nhan de doc bang Course.LEVEL_CHOICES neu co.
    """
    level_map = dict(getattr(Course, "LEVEL_CHOICES", []))
    default_icon = "fas fa-book-open"
    serialized: List[dict] = []
    for course in courses_qs:
        serialized.append(
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
    return serialized


def _serialize_graduates(
    graduates_qs: Iterable[OutstandingGraduate],
) -> List[dict]:
    """Chuyen doi thong tin hoc vien xuat sac thanh cac the hien thi."""
    serialized: List[dict] = []
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
    """Tao danh sach trich dan ngan gon tu cau chuyen thanh cong."""
    testimonials: List[dict] = []
    for story in stories_qs:
        initials = "".join(part[:1] for part in (story.student_name or "").split() if part)
        testimonials.append(
            {
                "quote": (story.story or "")[:160],
                "initials": (initials.upper()[:2] or "HV"),
                "name": story.student_name,
                "program": story.course_name,
            }
        )
    return testimonials


def _build_home_page_context() -> dict:
    """Tap hop du lieu hien thi trang chu cong khai."""
    now = timezone.now()

    hero_highlights_qs = HeroHighlight.objects.filter(is_active=True).order_by("order", "id")
    teacher_queryset = _get_teacher_queryset().only("full_name", "specialization", "bio", "start_date", "avatar")
    courses_qs = Course.objects.filter(is_active=True).order_by("id")
    graduates_qs = (
        OutstandingGraduate.objects.filter(is_active=True)
        .filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=now),
            Q(unpublish_at__isnull=True) | Q(unpublish_at__gt=now),
        )
        .order_by("order", "id")
    )
    stories_qs = SuccessStory.objects.filter(is_approved=True).order_by("order", "-created_at")
    achievements_qs = (
        Achievement.objects.filter(is_active=True)
        .filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=now),
            Q(unpublish_at__isnull=True) | Q(unpublish_at__gt=now),
        )
        .order_by("order", "id")
    )

    achievements = _serialize_achievements(achievements_qs)

    context = {
        "nav_links": _build_nav_links(location=NavigationLink.LOCATION_HEADER, default=DEFAULT_NAV_LINKS),
        "hero_setting": _get_hero_setting(),
        "hero_highlights": _serialize_highlights(hero_highlights_qs),
        "reasons": _get_active_reasons(),
        "force_visible": False,
        "teachers": _serialize_teachers(teacher_queryset),
        "achievements": achievements,
        "stats": list(achievements),
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
    return context


def home(request):
    """Hien thi trang chu cong khai voi toan bo du lieu context can thiet."""
    context = _build_home_page_context()
    return render(request, "public/home.html", context)


HOME_SECTION_PARTIALS = {
    "features": {"template": "public/fragments/features.html", "keys": ["reasons"]},
    "courses": {"template": "public/fragments/courses.html", "keys": ["courses"]},
    "teachers": {"template": "public/fragments/teachers.html", "keys": ["teachers"]},
    "graduates": {"template": "public/fragments/graduates.html", "keys": ["graduates"]},
    "testimonials": {"template": "public/fragments/testimonials.html", "keys": ["testimonials"]},
    "achievements": {"template": "public/fragments/achievements.html", "keys": ["achievements"]},
}


def home_section(request, section: str):
    """Tra ve fragment HTML phan trang chu phuc vu htmx."""
    config = HOME_SECTION_PARTIALS.get(section)
    if not config:
        raise Http404("Không tìm thấy phần trang chủ.")

    context = _build_home_page_context()
    payload = {key: context.get(key) for key in config["keys"]}
    payload["section"] = section
    if request.headers.get("HX-Request") == "true":
        payload["force_visible"] = True
    else:
        payload["force_visible"] = False
    return render(request, config["template"], payload)


def _normalize_service_status(value):
    """Chuan hoa gia tri trang thai dich vu ve 'up', 'down' hoac 'unknown'."""
    if value is None:
        return "unknown"
    normalized = str(value).strip().lower()
    if normalized in {"up", "ok", "running", "ready", "healthy", "online"}:
        return "up"
    if normalized in {"down", "error", "failed", "offline", "unhealthy"}:
        return "down"
    return "unknown"


def _get_admin_footer_context():
    """Thu thap metadata hien thi trong footer admin (phien ban, trang thai dich vu, dung luong)."""
    version = getattr(settings, "APP_VERSION", getattr(settings, "VERSION", "v1.0.0"))
    environment = getattr(settings, "APP_ENVIRONMENT", getattr(settings, "ENVIRONMENT", "PROD")) or "PROD"
    brand_name = getattr(settings, "SITE_BRAND_NAME", "Global English")
    build_commit = getattr(settings, "BUILD_COMMIT", getattr(settings, "GIT_COMMIT", "abc1234"))
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

    storage_db_usage = getattr(settings, "ADMIN_STORAGE_DB_USAGE", None) or "--"
    storage_media_usage = getattr(settings, "ADMIN_STORAGE_MEDIA_USAGE", None) or "--"

    return {
        "brand_name": brand_name,
        "app_version": version,
        "app_environment": str(environment).upper(),
        "build_commit": str(build_commit)[:7],
        "build_timestamp": formatted_timestamp,
        "celery_status": celery_status,
        "redis_status": redis_status,
        "smtp_status": smtp_status,
        "storage_db_usage": storage_db_usage,
        "storage_media_usage": storage_media_usage,
    }


@login_required
def admin_dashboard(request):
    footer_context = _get_admin_footer_context()

    tasks_pending = [
        {
            "title": "Duyet don dang ky #ENR-1045",
            "subtitle": "Enrollment cho duyet",
            "href": "#",
        },
        {
            "title": "Xu ly hoan tien #REF-232",
            "subtitle": "Finance can xac nhan",
            "href": "#",
        },
        {
            "title": "Phan hoi ticket #TCK-481",
            "subtitle": "Support con 4 gio SLA",
            "href": "#",
        },
    ]

    context = {
        "support_unread_count": 2,
        "notification_unread_count": 4,
        "tasks_pending": tasks_pending,
        "tasks_pending_count": len(tasks_pending),
    }
    context.update(footer_context)
    return render(request, "admin/dashboard.html", context)


# ================= Additional Public Views =================#

def about(request):
    """Trang "Giới thiệu" đơn giản cho trang công khai.

    Thu thập một bộ nội dung ngắn gọn: hero, liên kết điều hướng và lý do đang hoạt động.
    Được thiết kế đơn giản có chủ đích — trang chủ vẫn là nguồn chính của nội dung động.
    """
    context = {
        "nav_links": _build_nav_links(
            location=NavigationLink.LOCATION_HEADER, default=DEFAULT_NAV_LINKS
        ),
        "hero_setting": _get_hero_setting(),
        "reasons": _get_active_reasons(),
        "footer_about": _build_nav_links(
            location=NavigationLink.LOCATION_FOOTER_ABOUT,
            default=DEFAULT_FOOTER_ABOUT,
        ),
    }
    return render(request, "public/about.html", context)


