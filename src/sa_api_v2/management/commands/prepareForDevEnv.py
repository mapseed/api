from __future__ import print_function
from django.core.management.base import BaseCommand
from django.db import transaction

from sa_api_v2.models import (
    DataSet,
    OriginPermission,
    PlaceEmailTemplate
)

from sa_api_v2.cors.models import Origin

import logging
# display our logs to console with StreamHandler:
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger.addHandler(console_handler)


class Command(BaseCommand):
    help = """ For our dev api, update the origin permissions in our datasets and
    origin references to our place email templates"""

    def handle(self, *args, **options):
        datasets = DataSet.objects.all()
        with transaction.atomic():

            # delete all origin references to any place_email_templates:
            for email_template in PlaceEmailTemplate.objects.all():
                logger.info("Deleting origin references to place email template: {}"
                            .format(email_template))
                email_template.origins.clear()

            # add localhost permissions to all datasets, if not already added:
            for dataset in datasets:
                # skip over datasets that already have a localhost origin...
                matches = [origin for origin in dataset.origins.all()
                           if origin is not None and 'localhost:8000' in origin.pattern]
                if len(matches) > 0:
                    logger.info("dataset already has localhost:8000 origin: {}"
                                .format(dataset))
                    continue

                # create a new permission:
                ds_origin = Origin.objects.create(pattern='localhost:8000', dataset=dataset)
                OriginPermission.objects.create(
                    origin=ds_origin,
                    submission_set="places",
                    can_retrieve=True,
                    can_create=True,
                    can_update=True,  # temporary, until we fix https://github.com/jalMogo/mgmt/issues/227
                )
                OriginPermission.objects.create(
                    origin=ds_origin,
                    submission_set="support",
                    can_retrieve=True,
                    can_create=True,
                    can_destroy=True,
                )
                OriginPermission.objects.create(
                    origin=ds_origin,
                    submission_set="comments",
                    can_retrieve=True,
                    can_create=True,
                )

                logger.info("Permissions added to dataset: {}".format(dataset))
