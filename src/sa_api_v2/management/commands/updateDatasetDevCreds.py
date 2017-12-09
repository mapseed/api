from __future__ import print_function
from django.core.management.base import BaseCommand
import os
import re

# for manually testing with `./manage.py shell` commandline:
# from ... import models as sa_models
# from ... import forms

from sa_api_v2 import models as sa_models

import logging
# display our logs to console with StreamHandler:
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

# The name of our file containing our dev key values,
# located in our project root.
DATASET_ENV_FILE = '.dataset-env'
# The suffix of our dev key variables in our .env file:
DEV_KEY_SUFFIX = '_DEV_KEY'


def parse_env(dict):
    """
    Parses variables from a .env file located in the project root
    directory and loads them into the dictionary.

    """
    try:
        file_path = os.path.join(
            os.path.dirname(__file__), '..',  '..', '..', DATASET_ENV_FILE)
        with open(file_path) as f:
            content = f.read()
    except IOError:
        content = ''

    for line in content.splitlines():
        m1 = re.match(r'\A([A-Za-z_0-9]+){}=(.*)\Z'.format(DEV_KEY_SUFFIX),
                      line)
        if m1:
            key, val = m1.group(1), m1.group(2)
            m2 = re.match(r"\A'(.*)'\Z", val)
            if m2:
                val = m2.group(1)
            m3 = re.match(r'\A"(.*)"\Z', val)
            if m3:
                val = re.sub(r'\\(.)', r'\1', m3.group(1))
            logger.info('parsing key from environment file: {}={}'
                        .format(key, val))
            dict.setdefault('{}{}'.format(key, DEV_KEY_SUFFIX), val)


class Command(BaseCommand):
    help = """
    For our dev api, update the api key value of all our datasets to
    the constants defined in our .env file

    This command is idempotent.
    """

    def handle(self, *args, **options):
        logger.info('parsing environment variables...')
        api_key_values = {}
        parse_env(api_key_values)
        logger.info('environment variables: {}'.format(api_key_values))
        logger.info('starting dataset key migration...')

        datasets = sa_models.DataSet.objects.all()
        logger.info('fetching matching...')

        logger.info('')
        for dataset in datasets:
            api_key_value = api_key_values.get('{}{}'.format(
                dataset.display_name.upper(),
                DEV_KEY_SUFFIX), None)
            # handle case when we have a dataset but no dev key:
            if api_key_value is None:
                logger.error('No matching key found for dataset: {}'
                             .format(dataset.display_name))
                logger.error('perhaps we should create a key for it?\n')
                continue
            # handle case when we have a dataset with no key:
            if dataset.keys is None or len(dataset.keys.all()) < 1:
                logger.error('Skipping dataset because it has no api key: {}\n'
                             .format(dataset.display_name))
                continue

            logger.info('setting key for datset name: {} to value: {}'
                        .format(dataset.display_name, api_key_value))
            # save the new value to our dataset's key:
            key = dataset.keys.all()[0]
            key.key = api_key_value
            key.save()
            dataset.key = key
            dataset.save()
