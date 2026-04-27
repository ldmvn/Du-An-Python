from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0030_productramoption_productstorageoption'),
    ]

    operations = [
        migrations.AddField(
            model_name='productramoption',
            name='price_delta',
            field=models.IntegerField(default=0),
        ),
    ]
