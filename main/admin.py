from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Achievement,
    Course,
    HeroHighlight,
    HomeSetting,
    NavigationLink,
    OutstandingGraduate,
    Reason,
    Student,
    Teacher,
)


@admin.register(Reason)
class ReasonAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active", "updated_at")
    list_editable = ("order", "is_active")
    search_fields = ("title", "description")
    ordering = ("order", "id")


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "avatar_thumb",
        "full_name",
        "email",
        "specialization",
        "status",
        "is_featured",
        "order",
        "publish_at",
        "unpublish_at",
        "updated_at",
    )
    list_display_links = ("avatar_thumb", "full_name")
    list_editable = ("status", "is_featured", "order", "publish_at", "unpublish_at")
    search_fields = ("full_name", "email", "specialization", "first_name", "last_name")
    list_filter = ("status", "is_featured", ("publish_at", admin.DateFieldListFilter))
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "avatar_preview")
    prepopulated_fields = {"slug": ("full_name",)}

    fieldsets = (
        (
            "Hiển thị công khai",
            {
                "fields": (
                    ("full_name", "slug"),
                    ("specialization", "status"),
                    ("is_featured", "order"),
                    ("publish_at", "unpublish_at"),
                    "bio",
                )
            },
        ),
        (
            "Ảnh đại diện",
            {"fields": ("avatar", "avatar_alt", "avatar_preview")},
        ),
        (
            "Cá nhân & Liên hệ",
            {
                "classes": ("collapse",),
                "fields": (
                    ("first_name", "last_name"),
                    ("gender", "birth_date"),
                    ("email", "phone"),
                    "address",
                ),
            },
        ),
        (
            "Khác",
            {
                "classes": ("collapse",),
                "fields": ("salary", "created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description="Ảnh")
    def avatar_thumb(self, obj):
        return format_html(
            '<img src="{}" style="height:32px;width:32px;border-radius:50%;object-fit:cover;" />',
            obj.avatar_url,
        )

    @admin.display(description="Xem trước")
    def avatar_preview(self, obj):
        return format_html(
            '<img src="{}" style="height:120px;border-radius:8px;" />', obj.avatar_url
        )


@admin.register(HeroHighlight)
class HeroHighlightAdmin(admin.ModelAdmin):
    list_display = ("title", "icon", "order", "is_active", "updated_at")
    list_editable = ("icon", "order", "is_active")
    search_fields = ("title", "description")
    ordering = ("order", "id")


@admin.register(HomeSetting)
class HomeSettingAdmin(admin.ModelAdmin):
    list_display = ("eyebrow", "primary_cta_label", "order", "is_active", "updated_at")
    list_editable = ("order", "is_active")
    ordering = ("order", "id")


@admin.register(NavigationLink)
class NavigationLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "location", "href", "order", "is_active", "updated_at")
    list_editable = ("location", "href", "order", "is_active")
    ordering = ("location", "order", "id")
    list_filter = ("location", "is_active")
    search_fields = ("label", "href")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "level_display", "price", "is_active", "updated_at")
    list_filter = ("level", "is_active")
    search_fields = ("title", "description")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Trình độ")
    def level_display(self, obj):
        return obj.get_level_display()


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "kind",
        "year",
        "metric_display",
        "order",
        "is_active",
        "updated_at",
    )
    list_filter = ("kind", "is_active")
    search_fields = ("title", "subtitle", "description")
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "phone",
        "status",
        "primary_course",
        "updated_at",
    )
    list_filter = ("status", "primary_course")
    search_fields = ("full_name", "email", "phone")
    autocomplete_fields = ("primary_course", "courses")
    filter_horizontal = ("courses",)
    ordering = ("full_name", "id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(OutstandingGraduate)
class OutstandingGraduateAdmin(admin.ModelAdmin):
    list_display = (
        "student_name",
        "achievement",
        "order",
        "is_active",
        "publish_at",
        "unpublish_at",
        "updated_at",
    )
    list_filter = ("is_active", ("publish_at", admin.DateFieldListFilter))
    search_fields = ("student_name", "course_name", "achievement", "story")
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Thông tin học viên",
            {
                "fields": (
                    ("student_name", "course_name"),
                    "achievement",
                    "story",
                )
            },
        ),
        (
            "Điểm số & hình ảnh",
            {
                "classes": ("collapse",),
                "fields": (
                    ("score_label", "score_value", "score_suffix"),
                    ("photo", "photo_alt"),
                ),
            },
        ),
        (
            "Hiển thị",
            {
                "classes": ("collapse",),
                "fields": (
                    "order",
                    "is_active",
                    "publish_at",
                    "unpublish_at",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )
