from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0034_productspecification_visible'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='pending_media',
            field=models.BooleanField(default=False, help_text='Đánh dấu sản phẩm đã chọn để thêm media'),
        ),
    ]
