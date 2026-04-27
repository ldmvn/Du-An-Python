from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0029_productcolor'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductRamOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=20)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('product', models.ForeignKey(on_delete=models.CASCADE, related_name='ram_options', to='store.product')),
            ],
            options={
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='ProductStorageOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('capacity', models.CharField(max_length=20)),
                ('price_delta', models.IntegerField(default=0)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('product', models.ForeignKey(on_delete=models.CASCADE, related_name='storage_options', to='store.product')),
            ],
            options={
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
