# Generated by Django 5.0.2 on 2024-12-23 06:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plotter', '0003_welldata_core_no_alter_welldata_core_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='core',
            name='core_no',
            field=models.IntegerField(),
        ),
    ]
