# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-09-24 22:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis_query', '0003_auto_20170924_2157'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysisrequest',
            name='apk',
            field=models.FileField(upload_to='apks/f1614c6e-8f5e-4ccd-8ca0-8f8cbbde82d6'),
        ),
        migrations.AlterField(
            model_name='analysisrequest',
            name='storage_path',
            field=models.TextField(default='apks/f1614c6e-8f5e-4ccd-8ca0-8f8cbbde82d6'),
        ),
    ]