# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-25 20:41
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0104_adjustment_explanation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskingredient',
            name='ingredient',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_ingredients', to='ics.Ingredient'),
        ),
    ]
