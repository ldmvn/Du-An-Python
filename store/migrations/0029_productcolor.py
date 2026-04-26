from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0028_product_feature_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductColor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('image', models.ImageField(blank=True, null=True, upload_to='Sanpham/colors/')),
                ('hex', models.CharField(default='#d1d5db', max_length=7)),
                ('price_delta', models.IntegerField(default=0)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='colors', to='store.product')),
            ],
            options={
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
