# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-11 19:48
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0067_task_flag_update_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='goal',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2017, 1, 1, 0, 0)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='goal',
            name='is_trashed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='goal',
            name='trashed_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]