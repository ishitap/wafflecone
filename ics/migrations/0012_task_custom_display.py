# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-01-11 16:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0011_auto_20170111_0719'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='custom_display',
            field=models.CharField(blank=True, max_length=25),
        ),
    ]