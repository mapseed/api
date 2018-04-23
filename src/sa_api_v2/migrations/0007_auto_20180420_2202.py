# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0006_attachment_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='placeemailtemplate',
            name='bcc_email',
        ),
        migrations.AddField(
            model_name='placeemailtemplate',
            name='bcc_email_1',
            field=models.EmailField(default=None, max_length=75, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='placeemailtemplate',
            name='bcc_email_2',
            field=models.EmailField(default=None, max_length=75, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='placeemailtemplate',
            name='bcc_email_3',
            field=models.EmailField(default=None, max_length=75, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='placeemailtemplate',
            name='bcc_email_4',
            field=models.EmailField(default=None, max_length=75, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='placeemailtemplate',
            name='bcc_email_5',
            field=models.EmailField(default=None, max_length=75, null=True, blank=True),
            preserve_default=True,
        ),
    ]
