from __future__ import print_function
from django.core.management.base import BaseCommand
from django.db import transaction
import pandas as pd
import math

from sa_api_v2.models import (
    Tag,
    PlaceTag,
    Place,
    DataSet
)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


TAG_MAPPINGS = {
    "Remove-above cost": "above costs",
    "Removed-cost above": "above costs",
    "Removed-Cost above": "above costs",
    "Remove- above cost": "above costs",
    "Vetted": "Vetted",
    "Vettted": "Vetted",
    "vetted": "Vetted",
    "Remove-illegal": "illegal",
    "Remove-programmatic": "programmatic",
    "Remove- programmatic": "programmatic",
    "Remove-separate process": "programmatic",
    "Remove-incomplete": "incomplete",
    "Remove-county function": "county function",
    "Remove-private": "private",
}

# 1. Create the tags on our pbdurham dataset
TAGS = [
    {
        "name": "Removed",
        "is_enabled": False,
        "children": [
            {
                "name": "above costs",
                "color": "#c9302c"
            },
            {
                "name": "illegal",
                "color": "#c9302c"
            },
            {
                "name": "programmatic",
                "color": "#c9302c"
            },
            {
                "name": "separate process",
                "color": "#c9302c"
            },
            {
                "name": "incomplete",
                "color": "#c9302c"
            },
            {
                "name": "county function",
                "color": "#c9302c"
            },
            {
                "name": "private",
                "color": "#c9302c"
            },
            {
                "name": "not in durham",
                "color": "#c9302c"
            },
        ]
    },
    {
        "name": "Vetted",
        "color": "#449d44"
    }
]


# 2. parse the csv
FILEPATH = "./prevet-tags.csv"

# 3. get the tag name from the "Pre-Vetting Status" column
#    find the tag using the tag name and TAG_MAPPINGS
# 4. get the place id from the "Mapseed ID" column
# 5. create a PlaceTag, Tag to the Place model


def create_tags():
    dataset = DataSet.objects.get(display_name="pbdurham")

    def create_tag(tag, parent):
        is_enabled = False if tag.get("is_enabled") is False else True
        color = tag.get("color", None)
        tagModel = Tag.objects.create(
            name=tag["name"],
            color=color,
            parent=parent,
            is_enabled=is_enabled,
            dataset=dataset
        )
        logger.info("creating tag: {}".format(tagModel))
        for child in [tag for tag in tag.get('children', [])]:
            create_tag(child, tagModel)
    for tag in TAGS:
        create_tag(tag, None)


def create_place_tags():
    df = pd.read_csv(FILEPATH)
    ideas_not_vetted = []
    for index, row in df.iterrows():
        # get the relevant place:
        if math.isnan(row['Mapseed ID']):
            logger.info("row had invalid id: {}".format(row))
            continue
        mapseed_id = int(row['Mapseed ID'])
        logger.info("parsing mapseed id: {}".format(mapseed_id))
        if mapseed_id is None:
            import ipdb
            ipdb.set_trace()
        if type(row['Pre-Vetting Status ']) == float and math.isnan(row['Pre-Vetting Status ']):
            logger.info("row has invalid prevet status: {}".format(row))
            ideas_not_vetted.append(mapseed_id)
            continue
        status = row['Pre-Vetting Status '].strip()
        tag_name = TAG_MAPPINGS.get(status, None)
        logger.info("tag name: {}".format(tag_name))
        if tag_name is None:
            logger.info("no tag name for place id: {}".format(mapseed_id))
            raise ValueError("no tag mapping for prevet status: {}". format(status))
            continue
        # get the relevant tag:
        tag = Tag.objects.get(name=tag_name)
        logger.info("Tag: {}".format(tag))
        place = Place.objects.get(id=mapseed_id)
        logger.info("place: {}".format(tag))
        PlaceTag.objects.create(tag=tag, place=place)

    logger.info("ideas not vetted: {}".format(ideas_not_vetted))


class Command(BaseCommand):
    help = """
    Ingest PlaceTags from a spreadsheet into our app.
    """

    def handle(self, *args, **options):
        with transaction.atomic():
            create_tags()
            create_place_tags()
