# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-06-26 23:32
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ics', '0111_merge_20180625_1850'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.CharField(max_length=100, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ics.Task')),
            ],
        ),
    ]
