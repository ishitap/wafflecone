# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-11 03:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0066_auto_20171207_0230'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='flag_update_time',
            field=models.DateTimeField(auto_now_add=True, default='2017-01-01 00:00:00'),
            preserve_default=False,
        ),
    ]