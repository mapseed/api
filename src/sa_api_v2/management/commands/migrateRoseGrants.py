# Usage: manage.py migrateRoseGrants.py <username> <email>

from __future__ import print_function
from django.core.management.base import BaseCommand
import sys
import re
import requests

#from ... import models as sa_models
#from ... import forms
# for manually testing with `./manage.py shell` commandline:
from sa_api_v2 import models as sa_models
from sa_api_v2 import forms

import datetime
import json
from django.core.files import File
import os

import logging
log = logging.getLogger(__name__)

DEFAULT_USERNAME = sys.argv[2]
DEFAULT_EMAIL = sys.argv[3]

DATASET_SLUG = "pugetsoundrose"
DATASET_ID = "pugetsoundrose"
LOCATION_TYPE = "rose-grants"

json_data = requests.get('https://raw.githubusercontent.com/mapseed/data/master/Rose-Foundation-Grants-since-Fall-2013.geojson').json()

# Set to False to hide the metadata section of the place detail view.
SHOW_METADATA = False

# Names of source data objects to insert into a submittedthing's JSON data blob.
# All fields within each target object will be inserted into the data blob.
# EXAMPLE: DATA_BLOB_TARGET_OBJECTS = ["properties"]
DATA_BLOB_TARGET_OBJECTS = ["properties"]

# Properties to add under a dedicated "style" object in the JSON blob. The value
# associated with each key below will be saved. This is useful for converting source
# data style names to the styles names expected by Leaflet.
STYLE_PROPERTIES = {
    # "marker-color": "marker-color",
    # "marker-symbol": "marker-symbol",
    # "marker-size": "marker-size",
    # "stroke-width": "weight",
    # "stroke-opacity": "opacity",
    # "fill-opacity": "fillOpacity",
    # "stroke": "color",
    # "fill": "fillColor"
}

# An optional pattern to search for and remove in the description field of each
# data object.
# Strip out titles found in leading <hx></hx> or <b></b> tags:
#STRIP_PATTERN = re.compile("(^\s*<(h[0-9]|b)>.+<(\/h[0-9]|\/b)>)\n*")

# Strip leading img tags
#STRIP_PATTERN = re.compile("^<img.+?>")

# Names of other top-level fields to add to the JSON data blob. List field names 
# as a tuple of two strings. The first item in the tuple should be the source
# data field name; the second should be the field name to use in the
# submittedthing's JSON data blob.
# EXAMPLE: DATA_BLOB_TARGET_FIELDS = [("location_type", "location_type"), ("title", "url-title")]
DATA_BLOB_TARGET_FIELDS = [
   # ("title", "url-title")
]

# Names of fields to ignore. Fields that conflict with internal shareabouts
# fields (like "id") should be ignored, or remapped to another name.
IGNORED_FIELDS = ["id", "Description", "Title", "marker-symbol"]

IS_VISIBLE = True

class Command(BaseCommand):
    help = 'Import a JSON file of places.'

    def handle(self, *args, **options):
        log.info('Command.handle: starting JSON import (log.info)')
        print('Command.handle: starting JSON import (print)')
        
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
            "datasetId": DATASET_ID,
            "style": {},
            "showMetadata": SHOW_METADATA,
            "location_type": LOCATION_TYPE
        }
        for target in DATA_BLOB_TARGET_OBJECTS:
            for key, value in item[target].items():
                # apply strip pattern
                #if key == "description" and STRIP_PATTERN:
                #    value = STRIP_PATTERN.sub("", value)
                # skip ignored fields and style object fields
                if key not in IGNORED_FIELDS:
                    if key in STYLE_PROPERTIES:
                        if value != "":
                            data["style"][STYLE_PROPERTIES[key]] = value
                    else:
                        data[key] = value

        for target in DATA_BLOB_TARGET_FIELDS:
            if target not in IGNORED_FIELDS:
                data[target[1]] = item["properties"][target[0]]   

        data["url-title"] = data["title"].lower()
        data["url-title"] = re.sub('[^A-Za-z0-9]', '-', data["url-title"])
        data["url-title"] = data["url-title"].rstrip("-")

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
