# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-02-03 20:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0020_recommendedinputs'),
    ]

    operations = [
        migrations.AddField(
            model_name='processtype',
            name='unit',
            field=models.CharField(default='item', max_length=20),
        ),
    ]
