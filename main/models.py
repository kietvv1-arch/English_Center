# models.py
from __future__ import annotations

import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.templatetags.static import static
from django.utils import timezone
from django.utils.text import slugify

# =========================
# Teacher (HR + Public)
# =========================

# Validator cho so dien thoai Viet Nam (0XXXXXXXXX hoac +84XXXXXXXXX)
PHONE_REGEX = RegexValidator(
    regex=r"^(?:(?:\+84)|0)\d{9}$",
    message="Số điện thoại phải bắt đầu bằng 0 hoặc +84 và gồm đúng 10 chữ số.",
)

STUDENT_STATUS_ENROLLED = "enrolled"
STUDENT_STATUS_COMPLETED = "completed"
class StudentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=STUDENT_STATUS_ENROLLED)
class Student(models.Model):
    """Core learner record managed internally."""
    class Status(models.TextChoices):
        ENROLLED = STUDENT_STATUS_ENROLLED, "Đang học"
        COMPLETED = STUDENT_STATUS_COMPLETED, "Đã tốt nghiệp"
        PAUSED = "paused", "Tạm dừng"
        WITHDRAWN = "withdrawn", "Đã rời"
    full_name = models.CharField(max_length=150, verbose_name="Họ tên")
    email = models.EmailField(blank=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Số điện thoại")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Ngày sinh")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=STUDENT_STATUS_ENROLLED,
        verbose_name="Trạng thái",
    )
    primary_course = models.ForeignKey(
        "Course",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="primary_students",
        verbose_name="Khóa học chính",
    )
    courses = models.ManyToManyField(
        "Course",
        blank=True,
        related_name="students",
        verbose_name="Các khóa đang tham gia",
    )
    enrollment_date = models.DateField(null=True, blank=True, verbose_name="Ngày nhập học")
    notes = models.TextField(blank=True, verbose_name="Ghi chú nội bộ")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    objects = StudentQuerySet.as_manager()
    class Meta:
        ordering = ("full_name", "id")
        verbose_name = "Học viên"
        verbose_name_plural = "Học viên"
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["status"]),
        ]
    def __str__(self) -> str:
        return self.full_name


class TeacherQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status="Active")

    def featured(self):
        """
        Chi giao vien hien thi tren Home:
        - Dang Active
        - is_featured=True
        - Nam trong khoang publish_at/unpublish_at (neu dat)
        - Da sap xep
        """
        now = timezone.now()
        return (
            self.active()
            .filter(is_featured=True)
            .filter(
                models.Q(publish_at__isnull=True) | models.Q(publish_at__lte=now),
                models.Q(unpublish_at__isnull=True) | models.Q(unpublish_at__gt=now),
            )
            .order_by("order", "id")
        )

    def public_only_fields(self):
        """
        Khi render public (Home), chi chon cac truong cong khai de giam ro ri du lieu.
        Dung kem voi Proxy model PublicTeacher hoac truc tiep trong view.
        """
        return self.only(
            "id",
            "slug",
            "full_name",
            "bio",
            "avatar",
            "avatar_alt",
            "specialization",
            "start_date",
            "order",
            "is_featured",
        )


class Teacher(models.Model):
    # Quan he (dung AUTH_USER_MODEL de linh hoat)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Thong tin ca nhan
    full_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[("Nam", "Nam"), ("Nữ", "Nữ"), ("Khác", "Khác")],
        blank=True,
    )
    birth_date = models.DateField(null=True, blank=True)

    # Lien he
    email = models.EmailField(max_length=254)
    phone = models.CharField(
        max_length=20, unique=True, validators=[PHONE_REGEX], blank=True, null=True
    )

    # Thong tin chuyen mon
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to="teachers/avatars/", null=True, blank=True)
    avatar_alt = models.CharField(
        max_length=150, blank=True, help_text="Alt text for the avatar (SEO/A11y)."
    )
    specialization = models.CharField(
        max_length=200, blank=True, verbose_name="Chuyên môn"
    )
    start_date = models.DateField(null=True, blank=True)

    # Khac (nhay cam  KHONG render public)
    address = models.TextField(blank=True, null=True)
    salary = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )

    # Quan ly
    STATUS_CHOICES = [
        ("Active", "Đang làm"),
        ("Inactive", "Nghỉ làm"),
        ("OnLeave", "Nghỉ phép"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Active")

    #  Cac truong phuc vu HIEN THI TRANG HOME 
    slug = models.SlugField(max_length=140, blank=True, unique=True, db_index=True)
    is_featured = models.BooleanField(
        default=False, help_text="Bật để hiển thị ở trang Home"
    )
    order = models.PositiveIntegerField(default=0, help_text="Thứ tự hiển thị ở Home")
    publish_at = models.DateTimeField(null=True, blank=True)
    unpublish_at = models.DateTimeField(null=True, blank=True)

    # Tu dong
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = TeacherQuerySet.as_manager()

    class Meta:
        verbose_name = "Giáo viên"
        verbose_name_plural = "Giáo viên"
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["is_featured", "order"]),
            models.Index(fields=["publish_at", "unpublish_at"]),
            models.Index(fields=["-created_at"]),
        ]
        # Unique email case-insensitive (PostgreSQL)
        constraints = [
            models.UniqueConstraint(Lower("email"), name="uniq_teacher_email_ci"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})" if self.email else self.full_name

    # --------- Helpers ----------
    def _split_full_name(self) -> None:
        """Tach first_name/last_name tu full_name (an toan cho ten 1 tu)."""
        if not self.full_name:
            self.first_name = ""
            self.last_name = ""
            return
        parts = self.full_name.strip().split()
        self.first_name = parts[-1] if parts else ""
        self.last_name = " ".join(parts[:-1]) if len(parts) > 1 else ""

    def clean(self) -> None:
        """Validate cross-field constraints at the model level."""
        super().clean()

        if self.phone:
            self.phone = self._normalize_phone_value(self.phone)

        if (
            self.publish_at
            and self.unpublish_at
            and self.publish_at >= self.unpublish_at
        ):
            raise ValidationError(
                {"unpublish_at": "Thoi gian go phai sau thoi gian dang."}
            )

    def save(self, *args, **kwargs) -> None:
        # Chuan hoa ten + email
        self._split_full_name()
        if self.email:
            self.email = self.email.lower().strip()
        if self.phone:
            self.phone = self._normalize_phone_value(self.phone)

        # Slug SEO
        if not self.slug and self.full_name:
            self.slug = slugify(self.full_name)[:140]

        # Neu unpublish_at <= publish_at  bo unpublish (tranh hien thi loi)
        if (
            self.publish_at
            and self.unpublish_at
            and self.publish_at >= self.unpublish_at
        ):
            # khong raise de tranh crash khi import du lieuchi sua mem
            self.unpublish_at = None

        super().save(*args, **kwargs)

    @staticmethod
    def _normalize_phone_value(value: str) -> str:
        """Return a Vietnamese phone number formatted as +84XXXXXXXXX."""
        digits = re.sub(r"\D", "", value or "")
        if digits.startswith("84"):
            national = digits[2:]
        elif digits.startswith("0"):
            national = digits[1:]
        else:
            raise ValidationError(
                {"phone": "So dien thoai phai bat dau bang 0 hoac +84."}
            )

        if len(national) != 9:
            raise ValidationError(
                {"phone": "So dien thoai Viet Nam phai co dung 10 chu so."}
            )

        return f"+84{national}"

    @property
    def avatar_url(self) -> str:
        """
        Tra URL avatar hoac placeholder an toan.
        - Khong nem exception neu file thieu/Storage loi.
        """
        try:
            if self.avatar and getattr(self.avatar, "url", None):
                return self.avatar.url
        except Exception:
            # Neu storage loi/khong co file, luon tra placeholder
            pass
        return static("public/images/teacher/placeholder.svg")

    @property
    def is_currently_published(self) -> bool:
        """Co dang hien thi public (Home) o thoi diem hien tai khong?"""
        if self.status != "Active" or not self.is_featured:
            return False
        now = timezone.now()
        if self.publish_at and self.publish_at > now:
            return False
        if self.unpublish_at and self.unpublish_at <= now:
            return False
        return True

    @property
    def active_classes(self):
        """
        Lay danh sach lop dang day (phu thuoc related_name cua FK o Class).
        Dam bao FK Class.teacher dat related_name='classes_teaching'.
        """
        return getattr(self, "classes_teaching", models.Manager()).filter(
            status="ongoing"
        )


# Proxy model de render PUBLIC an toan (khong lo fields nhay cam)
class PublicTeacher(Teacher):
    """
    Dung trong view trang Home:
        PublicTeacher.objects.public_only_fields().featured()[:6]
    hoac don gian:
        PublicTeacher.objects.featured()[:6]  (van OK, nhung se select nhieu field hon)
    """

    objects = TeacherQuerySet.as_manager()

    class Meta:
        proxy = True
        verbose_name = "Teacher (Public)"
        verbose_name_plural = "Teachers (Public)"


# =========================
# Home supporting content
# =========================


class NavigationLink(models.Model):
    """Navigation items rendered on the home page (header or footer)."""

    LOCATION_HEADER = "header"
    LOCATION_FOOTER_PROGRAM = "footer_program"
    LOCATION_FOOTER_ABOUT = "footer_about"
    LOCATION_CHOICES = (
        (LOCATION_HEADER, "Header"),
        (LOCATION_FOOTER_PROGRAM, "Footer program"),
        (LOCATION_FOOTER_ABOUT, "Footer about"),
    )

    label = models.CharField(max_length=80)
    href = models.CharField(max_length=200, blank=True, help_text="Anchor or URL.")
    location = models.CharField(
        max_length=20, choices=LOCATION_CHOICES, default=LOCATION_HEADER
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        ordering = ("location", "order", "id")
        verbose_name = "Navigation link"
        verbose_name_plural = "Navigation links"
        indexes = [
            models.Index(fields=["location", "is_active", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.location})"


class HomeSetting(models.Model):
    """Editable content for the hero section on the home page."""

    eyebrow = models.CharField(max_length=80, default="Global English")
    typed_text = models.CharField(
        max_length=160, default="Mở ra thế giới với tiếng Anh"
    )
    subtitle = models.TextField(
        blank=True,
        default=(
            "Lộ trình luyện tập cá nhân hóa, lớp học tương tác và hệ thống theo dõi tiến "
            "độ giúp bạn tự tin giao tiếp trong mọi bối cảnh toàn cầu."
        ),
    )
    primary_cta_label = models.CharField(max_length=80, default="Liên hệ tư vấn")
    primary_cta_href = models.CharField(max_length=200, default="#advisory")
    secondary_cta_label = models.CharField(
        max_length=80, blank=True, default="Xem video giới thiệu"
    )
    secondary_cta_href = models.CharField(
        max_length=200, blank=True, default="#intro-video"
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Home setting"
        verbose_name_plural = "Home settings"

    def __str__(self) -> str:
        return self.eyebrow


class HeroHighlight(models.Model):
    """Hero highlight cards displayed beside the hero copy."""

    icon = models.CharField(
        max_length=80, help_text="Font Awesome class, e.g. 'fas fa-graduation-cap'."
    )
    title = models.CharField(max_length=120)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Hero highlight"
        verbose_name_plural = "Hero highlights"
        indexes = [
            models.Index(fields=["is_active", "order"]),
        ]

    def __str__(self) -> str:
        return self.title


class CourseQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def published(self):
        now = timezone.now()
        return self.filter(
            models.Q(publish_at__isnull=True) | models.Q(publish_at__lte=now),
            models.Q(unpublish_at__isnull=True) | models.Q(unpublish_at__gt=now),
        )

    def public_only_fields(self):
        return self.only(
            "id",
            "slug",
            "title",
            "subtitle",
            "short_description",
            "description",
            "level",
            "price",
            "sale_price",
            "thumbnail",
            "thumbnail_alt",
            "duration_hours",
            "lesson_count",
            "rating_avg",
            "rating_count",
            "order",
            "publish_at",
            "unpublish_at",
        )

    # vai scope thuong gap (tuy chon)
    def featured(self):
        return (
            self.filter(is_featured=True)
            if "is_featured" in [f.name for f in self.model._meta.fields]
            else self
        )

    def popular(self):
        return self.order_by("-rating_count", "-rating_avg", "order", "id")

    def cheapest(self):
        return self.order_by(
            models.F("sale_price").asc(nulls_last=True), "price", "order", "id"
        )


class Course(models.Model):
    LEVEL_CHOICES = [
        ("Beginner", "Beginner"),
        ("Intermediate", "Intermediate"),
        ("Advanced", "Advanced"),
        ("AllLevels", "Mọi trình độ"),
    ]
    title = models.CharField(max_length=200, verbose_name="Tên khóa học")
    description = models.TextField(verbose_name="Mô tả")
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES, default="Beginner")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Học phí",
    )
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        verbose_name = "Khóa học"
        verbose_name_plural = "Khóa học"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_active", "created_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def student_count(self):
        return self.students.count()  # nếu bạn có M2M/through ở nơi khác


# =========================
# Reason (Why choose us)
# =========================
class Reason(models.Model):
    """Reason why learners choose the center (shown on Home)."""

    title = models.CharField(max_length=150)
    description = models.TextField()
    image = models.CharField(
        max_length=200,
        blank=True,
        help_text="File name inside static/public/images/reason (e.g. 'team.png').",
    )
    order = models.PositiveIntegerField(default=0, help_text="Display order.")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Reason"
        verbose_name_plural = "Reasons"
        indexes = [
            models.Index(fields=["is_active", "order"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def image_url(self) -> str:
        """
        Return the static URL for the reason image or a placeholder.
        - Khong raise neu thieu file; luon co fallback.
        """
        if self.image:
            return static(f"public/images/reason/{self.image}")
        return static("public/images/reason/placeholder.svg")


class AchievementQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def published(self, *, at=None):
        moment = at or timezone.now()
        return self.filter(
            models.Q(publish_at__isnull=True) | models.Q(publish_at__lte=moment),
            models.Q(unpublish_at__isnull=True) | models.Q(unpublish_at__gt=moment),
        )


class AchievementType(models.TextChoices):
    AWARD = "award", "Giải thưởng"
    MILESTONE = "milestone", "Cột mốc"
    PRESS = "press", "Báo chí/Truyền thông"
    CERTIFICATE = "certificate", "Chứng nhận"
    PARTNERSHIP = "partnership", "Hợp tác"
    OTHER = "other", "Khác"


class Achievement(models.Model):
    """Thanh tuu, giai thuong hoac cot moc phat trien cua trung tam (hien thi tren trang chu)."""

    # Noi dung hien thi
    title = models.CharField(max_length=180, verbose_name="Tiêu đề")
    subtitle = models.CharField(
        max_length=220, blank=True, verbose_name="Phụ đề/ngắn gọn"
    )
    description = models.TextField(blank=True, verbose_name="Mô tả chi tiết")
    kind = models.CharField(
        max_length=20,
        choices=AchievementType.choices,
        default=AchievementType.MILESTONE,
        verbose_name="Loại",
    )
    image = models.ImageField(
        upload_to="achievements/",
        blank=True,
        null=True,
        help_text="Ảnh minh họa tùy chọn.",
    )
    image_alt = models.CharField(
        max_length=150,
        blank=True,
        help_text="Văn bản thay thế cho ảnh (SEO/A11y).",
    )

    # Thong tin phu tro (nam dat duoc, so lieu thong ke...)
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1900), MaxValueValidator(3000)],
        help_text="Năm đạt thành tựu (tùy chọn).",
    )
    metric_value = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Giá trị số (ví dụ: 1000). Để trống nếu không dùng.",
    )
    metric_suffix = models.CharField(
        max_length=10,
        blank=True,
        help_text="Hậu tố hiển thị (ví dụ: '+', 'k', '%').",
    )

    # Lien ket tham khao (bai bao, chung nhan...)
    external_url = models.URLField(blank=True, verbose_name="Liên kết ngoài")

    # Dieu khien hien thi
    order = models.PositiveIntegerField(
        default=0, help_text="Thứ tự hiển thị trên trang chủ."
    )
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    publish_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Thời điểm đăng"
    )
    unpublish_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Thời điểm gỡ"
    )

    # Tu dong ghi nhan thoi gian
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = AchievementQuerySet.as_manager()

    class Meta:
        verbose_name = "Thành tựu"
        verbose_name_plural = "Thành tựu"
        ordering = ("order", "id")
        indexes = [
            models.Index(fields=["is_active", "order"]),
            models.Index(fields=["publish_at", "unpublish_at"]),
            models.Index(fields=["kind"]),
        ]
        constraints = [
            models.UniqueConstraint(
                Lower("title"),
                condition=models.Q(is_active=True),
                name="uniq_achievement_title_active_ci",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.year})" if self.year else self.title

    @property
    def has_metric(self) -> bool:
        return self.metric_value is not None

    @property
    def metric_display(self) -> str:
        if self.metric_value is None:
            return ""
        return f"{self.metric_value}{self.metric_suffix or ''}"

    @property
    def image_url(self) -> str:
        if self.image and getattr(self.image, "url", None):
            return self.image.url
        return static("public/images/achievement/placeholder.svg")

    @property
    def is_currently_published(self) -> bool:
        if not self.is_active:
            return False
        now = timezone.now()
        if self.publish_at and self.publish_at > now:
            return False
        if self.unpublish_at and self.unpublish_at <= now:
            return False
        return True

    def clean(self):
        super().clean()
        if (
            self.publish_at
            and self.unpublish_at
            and self.publish_at >= self.unpublish_at
        ):
            raise ValidationError(
                {"unpublish_at": "Thời điểm gỡ phải sau thời điểm đăng."}
            )


class OutstandingGraduate(models.Model):
    """Hoc vien tot nghiep xuat sac (hien thi o Home)."""

    # Thong tin hien thi
    student_name = models.CharField(max_length=120, verbose_name="Tên học viên")
    achievement = models.CharField(
        max_length=150, blank=True, verbose_name="Thành tựu đạt được"
    )
    story = models.TextField(blank=True, verbose_name="Câu chuyện / chia sẻ chi tiết")
    photo = models.ImageField(upload_to="graduates/", null=True, blank=True)
    photo_alt = models.CharField(max_length=150, blank=True)

    # Dieu khien hien thi
    order = models.PositiveIntegerField(default=0, help_text="Thứ tự hiển thị")
    is_active = models.BooleanField(default=True)
    publish_at = models.DateTimeField(null=True, blank=True)
    unpublish_at = models.DateTimeField(null=True, blank=True)

    # Tu dong
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        verbose_name = "HV tốt nghiệp xuất sắc"
        verbose_name_plural = "HV tốt nghiệp xuất sắc"
        ordering = ("order", "id")
        indexes = [
            models.Index(fields=["is_active", "order"]),
            models.Index(fields=["publish_at", "unpublish_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.student_name} - ({self.achievement})" if self.achievement else self.student_name

    @property
    def photo_url(self):
        if self.photo and getattr(self.photo, "url", None):
            return self.photo.url
        return static("public/images/graduate/placeholder.svg")

    @property
    def is_currently_published(self) -> bool:
        if not self.is_active:
            return False
        now = timezone.now()
        if self.publish_at and self.publish_at > now:
            return False
        if self.unpublish_at and self.unpublish_at <= now:
            return False
        return True
