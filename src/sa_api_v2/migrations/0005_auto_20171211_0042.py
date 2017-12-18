# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0004_auto_20171027_0547'),
    ]

    operations = [
        migrations.AlterField(
            model_name='placeemailtemplate',
            name='submission_set',
            field=models.CharField(help_text=b'Either the name of a submission set         (e.g., "comments"), or "places". Leave blank to         refer to all things.', max_length=128, blank=True),
            preserve_default=True,
        ),
    ]
