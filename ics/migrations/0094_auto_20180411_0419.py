# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-11 04:19
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0093_processtype_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ingredient',
            name='recipe',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='recipes', to='ics.Recipe'),
        ),
    ]
