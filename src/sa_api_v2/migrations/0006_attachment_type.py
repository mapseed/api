# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0005_auto_20171211_0042'),
    ]

    operations = [
        migrations.AddField(
            model_name='attachment',
            name='type',
            field=models.CharField(default=b'CO', max_length=2, choices=[(b'CO', b'Cover'), (b'RT', b'Rich Text')]),
            preserve_default=True,
        ),
    ]
