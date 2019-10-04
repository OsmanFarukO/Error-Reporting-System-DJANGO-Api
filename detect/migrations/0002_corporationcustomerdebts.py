# Generated by Django 2.0 on 2019-07-02 21:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('detect', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CorporationCustomerDebts',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_payed', models.BooleanField(default=False)),
                ('payed_date', models.DateTimeField(blank=True)),
                ('corp', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='corpdebt', to='detect.Corporation')),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='issuedebt', to='detect.CorporationIssues')),
            ],
        ),
    ]
