# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-03-13 18:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0085_auto_20180306_2344'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='flag_update_time',
            field=models.DateTimeField(default='2017-01-01 23:25:26.835087+00:00'),
        ),
    ]
