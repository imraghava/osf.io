# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-12-13 18:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('addons_forward', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nodesettings',
            name='url',
            field=models.URLField(blank=True, max_length=255, null=True),
        ),
    ]