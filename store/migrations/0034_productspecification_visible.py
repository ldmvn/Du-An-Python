from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0033_product_spec_category_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='productspecification',
            name='visible',
            field=models.BooleanField(default=True),
        ),
    ]
