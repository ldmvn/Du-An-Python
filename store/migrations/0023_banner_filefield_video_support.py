from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0022_delete_voucher_alter_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='banner',
            name='image',
            field=models.FileField(help_text='Banner image or video', upload_to='banner/'),
        ),
    ]