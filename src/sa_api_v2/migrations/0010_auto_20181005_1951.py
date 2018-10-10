# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0009_auto_20180810_2129'),
    ]

    operations = [
        migrations.AlterField(
            model_name='origin',
            name='logged_ip',
            field=models.GenericIPAddressField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='placeemailtemplate',
            name='submission_set',
            field=models.CharField(help_text=b'The name of a submission set         (e.g., "comments", "places", "support"). Leave blank to         refer to all submission sets.', max_length=128, blank=True),
        ),
    ]
