# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-12-13 21:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0008_auto_20161213_1931'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='label',
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name='task',
            name='label_index',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
