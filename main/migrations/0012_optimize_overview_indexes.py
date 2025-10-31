from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0011_delete_coursehighlight"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name="course",
            index=models.Index(
                fields=["created_at"], name="main_course_created_c9f0b6_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(
                fields=["is_active", "created_at"],
                name="main_course_is_acti_9fcc5f_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="outstandinggraduate",
            index=models.Index(
                fields=["created_at"], name="main_outsta_created_f5eafa_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="teacher",
            index=models.Index(
                fields=["-created_at"], name="main_teache_created_260ffb_idx"
            ),
        ),
    ]
