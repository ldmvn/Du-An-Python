from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0027_productmedia_delete_voucher'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='feature_content',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='product',
            name='feature_image',
            field=models.ImageField(blank=True, null=True, upload_to='Sanpham/features/'),
        ),
    ]
