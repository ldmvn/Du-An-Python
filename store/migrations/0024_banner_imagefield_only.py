from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0023_banner_filefield_video_support'),
    ]

    operations = [
        migrations.AlterField(
            model_name='banner',
            name='image',
            field=models.ImageField(help_text='Banner image', upload_to='banner/'),
        ),
    ]