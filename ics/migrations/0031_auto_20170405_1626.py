# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-04-05 16:26
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ics', '0030_auto_20170330_1824'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='movement',
            name='team',
        ),
        migrations.AddField(
            model_name='movement',
            name='destination',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='intakes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='movement',
            name='origin',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='movement',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='movementitem',
            name='movement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='ics.Movement'),
        ),
    ]
