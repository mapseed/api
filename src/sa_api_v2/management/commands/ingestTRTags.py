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

FEASIBILITY_COLUMN = "Feasibility Score"
EQUITY_COLUMN = "Equity Score"
IMPACT_COLUMN = "Impact Score"

TAG_MAPPINGS = {
    FEASIBILITY_COLUMN: "feasibility",
    EQUITY_COLUMN: "equity",
    IMPACT_COLUMN: "impact"
}

# 1. Create the tags on our pbdurham dataset
RED = "#c9302c"
YELLOW = "#e99a00"
GREEN = "#449d44"
BLUE = "#6495ED"

TAGS = [
    {
        "name": "Technical Review",
        "is_enabled": False,
        "children": [
            {
                "name": "merged",
                "color": BLUE
            },
            {
                "name": "feasibility",
                "is_enabled": False,
                "children": [
                    {
                        "name": "1",
                        "color": RED
                    },
                    {
                        "name": "2",
                        "color": YELLOW
                    },
                    {
                        "name": "3",
                        "color": GREEN
                    },
                ]
            },
            {
                "name": "equity",
                "is_enabled": False,
                "children": [
                    {
                        "name": "1",
                        "color": RED
                    },
                    {
                        "name": "2",
                        "color": YELLOW
                    },
                    {
                        "name": "3",
                        "color": GREEN
                    },
                ]
            },
            {
                "name": "impact",
                "is_enabled": False,
                "children": [
                    {
                        "name": "1",
                        "color": RED
                    },
                    {
                        "name": "2",
                        "color": YELLOW
                    },
                    {
                        "name": "3",
                        "color": GREEN
                    },
                ]
            },
        ]
    }
]


# 2. parse the csv
# NOTE: replaced 6550 with 6650 (typo)
# NOTE: replaced 5761 with 5671 (typo)

# NOTE: deleted four rows for 5161, 5267, community center post (in
# spanish), 5626, b/c no scores given

# NOTE: fixed 4766 row - double spaces
FILEPATH = "./tr-tags.csv"

# 3. get the tag name from the "Pre-Vetting Status" column
#    find the tag using the tag name and TAG_MAPPINGS
# 4. get the place id from the "Mapseed ID" column
#    if there are multiple id's (separate by a " "), then add the place tag to each place, along with a "merged with" tag on each place.
# 5. create a PlaceTag, Tag to the Place model


def create_tags(dataset):

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


def get_tag(row, column_name):
    score = row[column_name]
    if type(score) == float and math.isnan(score):
        logger.info("row has invalid score: {}".format(row))
        raise ValueError("row has invalid score: {}".format(row))
    tag_name = TAG_MAPPINGS.get(column_name)
    tag = Tag.objects.get(name=tag_name)
    for child in tag.children.all():
        if int(child.name) == int(score):
            tag_child = child
    return tag_child


def create_place_tags(dataset):
    df = pd.read_csv(FILEPATH)
    for index, row in df.iterrows():
        # get the relevant place:
        id_field = row['Mapseed ID']
        if type(id_field) == str:
            id_field = id_field.split(" ")
        elif type(id_field) == float and math.isnan(id_field):
            logger.info("invalid mapseed id field on row: {}".format(row))
            continue
        elif type(id_field) == float:
            id_field = [int(id_field)]
        else:
            logger.info("invalid mapseed id field on row: {}".format(row))
            continue
        logger.info("parsed id field: {}".format(id_field))

        places = map(lambda x: Place.objects.get(id=int(x), dataset=dataset), id_field)
        logger.info("places: {}".format(places))

        # create a merge tag for each place, pointing back to the
        # first place in the list:
        merged_tag = Tag.objects.get(name="merged")
        main_place = places[0]
        for place in places[1:]:
            place_tag = PlaceTag.objects.create(
                tag=merged_tag,
                place=place,
                note='This idea has been merged with another idea:\
                https://pbdurham.mapseed.org/idea/{}'.format(main_place.id)
            )
            logger.info("place tag created: {}".format(place_tag))

        feasibility_tag = get_tag(row, FEASIBILITY_COLUMN)
        equity_tag = get_tag(row, EQUITY_COLUMN)
        impact_tag = get_tag(row, IMPACT_COLUMN)
        PlaceTag.objects.create(tag=equity_tag, place=main_place)
        PlaceTag.objects.create(tag=feasibility_tag, place=main_place)
        PlaceTag.objects.create(tag=impact_tag, place=main_place)


class Command(BaseCommand):
    help = """
    Ingest PlaceTags from a spreadsheet into our app.
    """

    def handle(self, *args, **options):
        with transaction.atomic():
            dataset = DataSet.objects.get(display_name="pbdurham")
            create_tags(dataset)
            create_place_tags(dataset)
