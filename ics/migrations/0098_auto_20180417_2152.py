# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-17 21:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0097_recipe_is_trashed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='instructions',
            field=models.TextField(null=True),
        ),
    ]
