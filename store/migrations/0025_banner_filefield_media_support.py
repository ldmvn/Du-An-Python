from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0024_banner_imagefield_only'),
    ]

    operations = [
        migrations.AlterField(
            model_name='banner',
            name='image',
            field=models.FileField(help_text='Banner image or video', upload_to='banner/'),
        ),
    ]