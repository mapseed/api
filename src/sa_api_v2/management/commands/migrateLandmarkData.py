from __future__ import print_function
from django.core.management.base import BaseCommand
import sys

from ... import models as sa_models
from ... import forms
# for manually testing with `./manage.py shell` commandline:
# from sa_api_v2 import models as sa_models
# from sa_api_v2 import forms

import datetime
import json
from django.core.files import File
import os

import logging
log = logging.getLogger(__name__)

json_filepathname = sys.argv[2]
DATASET_SLUG = "restoration"
DATASET_ID = "restoration"

# Names of source data objects to insert into a submittedthing's JSON data blob.
# All fields within each target object will be inserted into the data blob.
# EXAMPLE: DATA_BLOB_TARGET_OBJECTS = ["properties"]
DATA_BLOB_TARGET_OBJECTS = ["properties"]

# Names of other top-level fields to add to the JSON data blob.
# List field names either as a string, or as a tuple of two strings.
# If listed as a tuple, the first item in the tuple should be the source
# data field name; the second should be the field name to use in the
# submittedthing's JSON data blob. This is useful for overlapping
# source data field names.
# EXAMPLE: DATA_BLOB_TARGET_FIELDS = ["location_type", ("title", "url-title")]
DATA_BLOB_TARGET_FIELDS = ["location_type", ("title", "url-title")]

# Names of fields to ignore. Fields that conflict with internal shareabouts
# fields (like "id") should be ignored, or remapped to another name.
IGNORED_FIELDS = ["id"]

IS_VISIBLE = True
DEFAULT_USERNAME = "thebestguest"
DEFAULT_EMAIL = ""


class Command(BaseCommand):
    help = 'Import a JSON file of places.'

    def handle(self, *args, **options):
        log.info('Command.handle: starting JSON import (log.info)')
        print('Command.handle: starting JSON import (print)')

        json_data = json.load(open(json_filepathname))
        for item in json_data["features"]:
            self.save_item(item)

    def save_item(self, item):
        # Handle geometry
        # We only support simple points, linestrings, and polygons
        geometry_type = item["geometry"]["type"]
        if (geometry_type == "Point"):
            # format: POINT (lon lat)
            lat = float(item["geometry"]["coordinates"][1])
            lon = float(item["geometry"]["coordinates"][0])
            geometry = "POINT (%f %f)" % (lon, lat)
        elif (geometry_type == "LineString"):
            # format: LINESTRING (lon lat, lon lat)
            # NOTE: For linestrings and polygons, we strip out any coordinates 
            # beyond lon and lat (such as altitude), as these are not supported in the database
            geometry = "LINESTRING (" + ", ".join(" ".join(map(str, coords)[:2]) for coords in item["geometry"]["coordinates"]) + ")"
        elif (geometry_type == "Polygon"):
            # format: POLYGON ((lon lat, lon lat))
            # NOTE: the first and last coordinates of a polygon must be identical.
            # The database will reject polygons otherwise. We don't check the first
            # and last coordinates here, but it might be a good idea to do so.
            geometry = "POLYGON ((" + ", ".join(" ".join(map(str, coords)[:2]) for coords in item["geometry"]["coordinates"][0]) + "))"
        else:
            raise ValueError("Unsupported geometry type: %s" % geometry)

        # Handle submittedthing JSON data blob
        data = {
            "datasetSlug": DATASET_SLUG,
            "datasetId": DATASET_ID
        }
        for target in DATA_BLOB_TARGET_OBJECTS:
            for key, value in item[target].items():
                if key not in IGNORED_FIELDS:
                    data[key] = value

        for target in DATA_BLOB_TARGET_FIELDS:
            if (isinstance(target, basestring) and target not in IGNORED_FIELDS):
                data[target] = item[target]
            elif (isinstance(target, tuple) and target not in IGNORED_FIELDS):
                data[target[1]] = item[target[0]]

        data = json.dumps(data)


        placeForm = forms.PlaceForm({
            "data": data,
            "geometry": geometry,
            "created_datetime": datetime.datetime.now(),
            "updated_datetime": datetime.datetime.now(),
            "visible": IS_VISIBLE
        })
        place = placeForm.save(commit=False)

        place.submitter = sa_models.User.objects.get(
            username=DEFAULT_USERNAME,
            email=DEFAULT_EMAIL
        )

        try:
            dataset = sa_models.DataSet.objects.get(slug=DATASET_SLUG)
        except sa_models.DataSet.DoesNotExist:
            # query for the dataset
            dataset_owner = sa_models.User.objects.get(
                username=DEFAULT_USERNAME,
                email=DEFAULT_EMAIL
            )
            dataset = sa_models.DataSet(
                slug=DATASET_SLUG,
                display_name=DATASET_SLUG,
                owner=dataset_owner
            )
            print("existing dataset does not exist, creating new dataset:",
                  DATASET_SLUG)
            dataset.save()

        place.dataset = dataset

        place.save()


# value must be a string
def validate(value):
    if value == 'NULL' or value.isspace():
        return ''
    else:
        return value
