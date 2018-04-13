# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-06 17:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0089_auto_20180406_0131'),
    ]

    operations = [
        migrations.RenameField(
            model_name='taskingredient',
            old_name='amount',
            new_name='actual_amount',
        ),
        migrations.AddField(
            model_name='taskingredient',
            name='scaled_amount',
            field=models.DecimalField(decimal_places=3, default=1, max_digits=10),
        ),
    ]