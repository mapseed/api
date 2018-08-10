# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0007_auto_20180420_2202'),
    ]

    operations = [
        migrations.AddField(
            model_name='attachment',
            name='visible',
            field=models.BooleanField(default=True, db_index=True),
            preserve_default=True,
        ),
    ]
