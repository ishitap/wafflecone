# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-12 18:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0095_auto_20180412_1819'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='was_flag_changed',
            field=models.BooleanField(default=False),
        ),
    ]
