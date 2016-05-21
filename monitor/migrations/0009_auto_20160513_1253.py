# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-13 12:53
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0008_reading_is_valid'),
    ]

    operations = [
        migrations.AddField(
            model_name='channel',
            name='last_alert',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='channel_last_alert', to='monitor.Alert'),
        ),
        migrations.AlterField(
            model_name='channel',
            name='last_reading',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='channel_last_reading', to='monitor.Reading'),
        ),
    ]