# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-30 20:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0005_channel_rules'),
    ]

    operations = [
        migrations.AddField(
            model_name='preference',
            name='contact_method',
            field=models.IntegerField(choices=[(0, 'email'), (1, 'text'), (2, 'email and text')], default=0),
        ),
        migrations.AlterField(
            model_name='rule',
            name='action',
            field=models.IntegerField(choices=[(0, 'send email/text alert'), (1, 'display gui alert'), (2, 'send email/text and gui alert')]),
        ),
    ]