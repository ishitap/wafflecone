# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-19 18:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0102_auto_20180419_1822'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskingredient',
            name='scaled_amount',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=10),
        ),
    ]