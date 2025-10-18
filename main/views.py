from datetime import date

from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.templatetags.static import static  # <-- thêm import này

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
from main import models


def _calculate_experience_years(start_date):
    if not start_date:
        return None
    today = date.today()
    years = today.year - start_date.year - (
        (today.month, today.day) < (start_date.month, start_date.day)
    )
    return max(years, 0)


def home(request):
    now = timezone.now()

    # Reasons
    reasons = Reason.objects.filter(is_active=True).order_by("order", "id")

    # Hero settings
    hero_setting_obj = HomeSetting.objects.filter(is_active=True).order_by("order", "id").first()
    hero_setting = {
        "eyebrow": "Global English",
        "typed_text": "Mở ra thế giới với tiếng Anh",
        "subtitle": (
            "Lộ trình luyện tập cá nhân hóa, lớp học tương tác và hệ thống theo dõi tiến độ "
            "giúp bạn tự tin giao tiếp trong mọi bối cảnh toàn cầu."
        ),
        "primary_cta_label": "Liên hệ tư vấn",
        "primary_cta_href": "#advisory",
        "secondary_cta_label": "Xem video giới thiệu",
        "secondary_cta_href": "#intro-video",
    }
    if hero_setting_obj:
        hero_setting.update(
            {
                "eyebrow": hero_setting_obj.eyebrow or hero_setting["eyebrow"],
                "typed_text": hero_setting_obj.typed_text or hero_setting["typed_text"],
                "subtitle": hero_setting_obj.subtitle or hero_setting["subtitle"],
                "primary_cta_label": hero_setting_obj.primary_cta_label or hero_setting["primary_cta_label"],
                "primary_cta_href": hero_setting_obj.primary_cta_href or hero_setting["primary_cta_href"],
                "secondary_cta_label": hero_setting_obj.secondary_cta_label or "",
                "secondary_cta_href": hero_setting_obj.secondary_cta_href or "#",
            }
        )

    # Hero highlights
    hero_highlight_cards = HeroHighlight.objects.filter(is_active=True).order_by("order", "id")
    hero_highlights = [
        {"icon": card.icon, "title": card.title, "description": card.description}
        for card in hero_highlight_cards
    ]
    if not hero_highlights:
        hero_highlights = [
            {"icon": "fas fa-graduation-cap", "title": "Giảng viên bản ngữ", "description": "Đội ngũ chuyên gia sở hữu chứng chỉ sư phạm quốc tế, luôn đồng hành cùng bạn."},
            {"icon": "fas fa-chalkboard", "title": "Lớp học tương tác", "description": "Ứng dụng công nghệ hiện đại và phương pháp đào tạo chú trọng thực hành."},
            {"icon": "fas fa-certificate", "title": "Chứng chỉ toàn cầu", "description": "Cam kết thành tích với hệ thống kiểm tra chuẩn quốc tế và giám sát tiến độ liên tục."},
        ]

    # Nav links
    header_links = NavigationLink.objects.filter(
        location=NavigationLink.LOCATION_HEADER, is_active=True
    ).order_by("order", "id")
    nav_links = [{"label": link.label, "href": link.href or "#"} for link in header_links] or [
        {"label": "Giới thiệu", "href": "#features"},
        {"label": "Giảng viên", "href": "#teachers"},
        {"label": "Thành tựu", "href": "#stats"},
        {"label": "Khóa học", "href": "#courses"},
        {"label": "Học viên xuất sắc", "href": "#graduates"},
        {"label": "Cảm nhận", "href": "#testimonials"},
    ]

    footer_programs = [
        {"label": link.label, "href": link.href or "#"}
        for link in NavigationLink.objects.filter(
            location=NavigationLink.LOCATION_FOOTER_PROGRAM, is_active=True
        ).order_by("order", "id")
    ] or [
        {"label": "Tiếng Anh giao tiếp", "href": "#courses"},
        {"label": "Tiếng Anh thương mại", "href": "#courses"},
        {"label": "Luyện thi IELTS", "href": "#courses"},
        {"label": "Tiếng Anh trẻ em", "href": "#courses"},
    ]

    footer_about = [
        {"label": link.label, "href": link.href or "#"}
        for link in NavigationLink.objects.filter(
            location=NavigationLink.LOCATION_FOOTER_ABOUT, is_active=True
        ).order_by("order", "id")
    ] or [
        {"label": "Giới thiệu", "href": "#features"},
        {"label": "Đội ngũ giảng viên", "href": "#teachers"},
        {"label": "Phương pháp đào tạo", "href": "#features"},
        {"label": "Cơ sở vật chất", "href": "#features"},
    ]

    # TEACHERS (an toàn nếu không có custom manager)
    teachers_qs = Teacher.objects.filter(status="Active").order_by("order", "id")
    if hasattr(Teacher.objects, "featured"):
        try:
            teachers_qs = Teacher.objects.featured()
        except Exception:
            pass
    teachers = [
        {
            "name": t.full_name,
            "role": t.specialization,
            "bio": t.bio,
            "experience_years": _calculate_experience_years(t.start_date),
            "avatar_url": getattr(t, "avatar_url", None),
        }
        for t in teachers_qs
    ]

    # STATS (achievements) – đặt tên 'stats' cho khớp template cũ
    achievements_qs = (
        Achievement.objects.filter(is_active=True)
        .filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=now),
            Q(unpublish_at__isnull=True) | Q(unpublish_at__gt=now),
        )
        .order_by("order", "id")
    )
    stats = []
    for idx, a in enumerate(achievements_qs):
        value = getattr(a, "metric_value", None)
        if value is None:
            continue
        step = max(value / 50, 1)
        stats.append(
            {
                "value": value,
                "suffix": getattr(a, "metric_suffix", "") or "",
                "label": a.title,
                "delay": 250 * idx,
                "step": step,
            }
        )

    # COURSES – bỏ created_at để tránh FieldError nếu không có field này
    courses_qs = Course.objects.filter(is_active=True).only("id", "title", "description", "level").order_by("id")
    level_map = dict(getattr(Course, "LEVEL_CHOICES", []))
    courses = [
        {
            "title": c.title,
            "description": c.description,
            "level": level_map.get(c.level, c.level),
        }
        for c in courses_qs
    ]

    # OUTSTANDING GRADUATES – đặt key là 'graduates' cho khớp template
    graduates_qs = (
        OutstandingGraduate.objects.filter(is_active=True)
        .filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=now),
            Q(unpublish_at__isnull=True) | Q(unpublish_at__gt=now),
        )
        .order_by("order", "id")
    )
    graduates = []
    for g in graduates_qs:
        graduates.append(
            {
                "name": g.student_name,
                "course": g.course_name,
                "score": getattr(g, "score_display", None),
                "testimonial": g.testimonial,
                "photo_url": getattr(g, "photo_url", None) or static("public/images/graduate/placeholder.svg"),
            }
        )

    # SUCCESS STORIES (nếu cần)
    stories_qs = SuccessStory.objects.filter(is_approved=True).order_by("order", "-created_at")
    testimonials = [
        {
            "quote": (s.story or "")[:160],
            "initials": "".join(p[:1] for p in (s.student_name or "").split() if p).upper()[:2] or "HV",
            "name": s.student_name,
            "program": s.course_name,
        }
        for s in stories_qs
    ]

    context = {
        "nav_links": nav_links,
        "hero_setting": hero_setting,
        "hero_highlights": hero_highlights,
        "reasons": reasons,
        "teachers": teachers,
        "stats": stats,                  # ← khớp template counter
        "courses": courses,
        "graduates": graduates,          # ← khớp template graduates
        "testimonials": testimonials,
        "footer_programs": footer_programs,
        "footer_about": footer_about,
    }
    return render(request, "public/home.html", context)


def login(request):
    return render(request, "public/login.html")
