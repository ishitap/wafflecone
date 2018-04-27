# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-27 20:07
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0104_adjustment_explanation'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='recipe',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='ics.Recipe'),
        ),
    ]