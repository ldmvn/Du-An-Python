from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0031_productramoption_price_delta'),
    ]

    operations = [
        migrations.AddField(
            model_name='productspecification',
            name='category',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
