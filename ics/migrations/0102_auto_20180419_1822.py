# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-19 18:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0101_auto_20180418_2056'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskingredient',
            name='actual_amount',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=10),
        ),
    ]