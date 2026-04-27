from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0032_productspecification_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='spec_category_order',
            field=models.TextField(blank=True, default='', help_text='Danh sách thứ tự cụm thông số, phân tách bằng dấu phẩy'),
        ),
    ]
