# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-27 19:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mission_control', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='rover',
            name='local_ip',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]