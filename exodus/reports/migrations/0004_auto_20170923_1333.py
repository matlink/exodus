# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-09-23 13:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_auto_20170923_1325'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='creation_date',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]