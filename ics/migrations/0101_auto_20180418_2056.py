# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-18 20:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0100_auto_20180418_2012'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='is_trashed',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
