# Generated by Django 2.0 on 2019-07-09 22:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('detect', '0008_auto_20190709_1132'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usedmaterials',
            name='payed',
        ),
    ]