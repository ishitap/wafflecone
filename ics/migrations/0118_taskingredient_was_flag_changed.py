# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-02 21:42
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0117_task_remaining_worth'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskingredient',
            name='was_flag_changed',
            field=models.BooleanField(default=False),
        ),
    ]
