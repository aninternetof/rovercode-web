# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-11 20:07
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0005_abusereport'),
    ]

    operations = [
        migrations.AddField(
            model_name='abusereport',
            name='creation_time',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='abusereport',
            name='accused_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='accused_user', to=settings.AUTH_USER_MODEL),
        ),
    ]