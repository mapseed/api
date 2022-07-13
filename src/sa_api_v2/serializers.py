"""
DjangoRestFramework resources for the Shareabouts REST API.
"""
from django.utils import six
import ujson as json
import re
from collections import defaultdict, OrderedDict
from itertools import chain
from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from django.utils.http import urlquote_plus
from rest_framework import pagination, serializers, fields
from rest_framework.response import Response
from rest_framework.reverse import reverse

from . import apikey
from . import cors
from . import models
from .models import check_data_permission
from .params import (
    INCLUDE_INVISIBLE_PARAM,
    INCLUDE_TAGS_PARAM,
    INCLUDE_PRIVATE_FIELDS_PARAM,
    INCLUDE_SUBMISSIONS_PARAM,
    FORMAT_PARAM
)

import logging
logger = logging.getLogger(__name__)

# TODO: renmae this into serializers/core.py and make a separate serializers/__init__.py


###############################################################################
#
# Geo-related fields
# ------------------
#

class GeometryField(serializers.Field):
    def __init__(self, format='dict', *args, **kwargs):
        self.format = format

        if self.format not in ('json', 'wkt', 'dict'):
            raise ValueError('Invalid format: %s' % self.format)

        super(GeometryField, self).__init__(*args, **kwargs)

    def to_representation(self, obj):
        if self.format == 'json':
            return obj.json
        elif self.format == 'wkt':
            return obj.wkt
        elif self.format == 'dict':
            return json.loads(obj.json)
        else:
            raise ValueError('Cannot output as %s' % self.format)

    def to_internal_value(self, data):
        if not isinstance(data, basestring):
            data = json.dumps(data)

        try:
            return GEOSGeometry(data)
        except Exception as exc:
            raise ValidationError('Problem converting native data to Geometry: %s' % (exc,))

###############################################################################
#
# Shareabouts-specific fields
# ---------------------------
#


class ShareaboutsFieldMixin (object):

    # These names should match the names of the cache parameters, and should be
    # in the same order as the corresponding URL arguments.
    url_arg_names = ()

    def get_url_kwargs(self, obj):
        """
        Pull the appropriate arguments off of the cache to construct the URL.
        """
        if isinstance(obj, models.User):
            instance_kwargs = {'owner_username': obj.username}
        else:
            instance_kwargs = obj.cache.get_cached_instance_params(obj.pk,
                                                                   lambda: obj)

        url_kwargs = {}
        for arg_name in self.url_arg_names:
            arg_value = instance_kwargs.get(arg_name, None)
            if arg_value is None:
                try:
                    arg_value = getattr(obj, arg_name)
                except AttributeError:
                    raise KeyError('No arg named %r in %r' % (arg_name,
                                                              instance_kwargs))
            url_kwargs[arg_name] = arg_value
        return url_kwargs


def api_reverse(view_name, kwargs={}, request=None, format=None):
    """
    A special case of URL reversal where we know we're getting an API URL. This
    can be much faster than Django's built-in general purpose regex resolver.

    """
    if request:
        url = '{}://{}/api/v2'.format(request.scheme, request.get_host())
    else:
        url = '/api/v2'

    route_template_strings = {
        'submission-detail': '/{owner_username}/datasets/{dataset_slug}/places/{place_id}/{submission_set_name}/{submission_id}',
        'submission-list': '/{owner_username}/datasets/{dataset_slug}/places/{place_id}/{submission_set_name}',

        'place-detail':
        '/{owner_username}/datasets/{dataset_slug}/places/{place_id}',
        'place-list': '/{owner_username}/datasets/{dataset_slug}/places',
        'place-tag-list': '/{owner_username}/datasets/{dataset_slug}/places/{place_id}/tags',

        'dataset-detail': '/{owner_username}/datasets/{dataset_slug}',
        'user-detail': '/{owner_username}',
        'dataset-submission-list': '/{owner_username}/datasets/{dataset_slug}/{submission_set_name}',
        'attachment-detail': '/{owner_username}/datasets/{dataset_slug}/places/{place_id}/attachments/{attachment_id}',
    }

    try:
        route_template_string = route_template_strings[view_name]
    except KeyError:
        raise ValueError('No API route named {} formatted.'.format(view_name))

    url_params = dict([(key, urlquote_plus(val))
                       for key, val in kwargs.iteritems()])
    url += route_template_string.format(**url_params)

    if format is not None:
        url += '.' + format

    return url


class ShareaboutsRelatedField (ShareaboutsFieldMixin,
                               serializers.HyperlinkedRelatedField):
    """
    Represents a Shareabouts relationship using hyperlinking.
    """
    read_only = True
    view_name = None

    def __init__(self, *args, **kwargs):
        if self.view_name is not None:
            kwargs['view_name'] = self.view_name
        if self.queryset is not None:
            kwargs['queryset'] = self.queryset
        super(ShareaboutsRelatedField, self).__init__(*args, **kwargs)

    def get_attribute(self, obj):
        # Pass the entire object through to `to_representation()`,
        # instead of the standard attribute lookup. Otherwise,
        # obj is just a DRF relations.PKOnlyObject.
        return obj

    def to_representation(self, obj):
        view_name = self.view_name
        request = self.context.get('request', None)
        format = self.format or self.context.get('format', None)

        pk = getattr(obj, 'pk', None)
        if pk is None:
            return

        kwargs = self.get_url_kwargs(obj)
        return api_reverse(view_name, kwargs=kwargs, request=request,
                           format=format)


class DataSetRelatedField (ShareaboutsRelatedField):
    view_name = 'dataset-detail'
    url_arg_names = ('owner_username', 'dataset_slug')

    def get_url(self, obj, request):
        url_kwargs = {
            'owner_username': obj.owner.username,
            'dataset_slug': obj.slug,
        }
        return reverse('dataset-detail', kwargs=url_kwargs, request=request)

    def get_object(self, view_name, view_args, view_kwargs):
        lookup_kwargs = {
            'display_name': view_kwargs['dataset_slug'],
            'owner__username': view_kwargs['owner_username'],
        }
        return self.get_queryset().get(**lookup_kwargs)


class DataSetKeysRelatedField (ShareaboutsRelatedField):
    view_name = 'apikey-list'
    url_arg_names = ('owner_username', 'dataset_slug')


class UserRelatedField (ShareaboutsRelatedField):
    view_name = 'user-detail'
    url_arg_names = ('owner_username',)


class PlaceRelatedField (ShareaboutsRelatedField):
    view_name = 'place-detail'
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id')
    queryset = models.Place.objects.all()

    def get_object(self, view_name, view_args, view_kwargs):
        lookup_kwargs = {
            'id': view_kwargs['place_id'],
        }
        return self.get_queryset().get(**lookup_kwargs)


class SubmissionSetRelatedField (ShareaboutsRelatedField):
    view_name = 'submission-list'
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id',
                     'submission_set_name')


# TODO: enable this with caching
class TagRelatedField (serializers.HyperlinkedRelatedField):
    view_name = 'tag-detail'
    queryset = models.Tag.objects.all()
    lookup_field = 'id'

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'owner_username': obj.dataset.owner.get_username(),
            'dataset_slug': obj.dataset.slug,
            'tag_id': obj.pk
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)

    # TODO: do we need this?
    def get_object(self, view_name, view_args, view_kwargs):
        lookup_kwargs = {
           'dataset__slug': view_kwargs['dataset_slug'],
           'id': view_kwargs['tag_id']
        }
        return self.get_queryset().get(**lookup_kwargs)


class ShareaboutsIdentityField (ShareaboutsFieldMixin,
                                serializers.HyperlinkedIdentityField):
    read_only = True

    def __init__(self, *args, **kwargs):
        view_name = kwargs.pop('view_name', None) or getattr(self, 'view_name',
                                                             None)
        super(ShareaboutsIdentityField, self).__init__(view_name=view_name,
                                                       *args, **kwargs)

    def get_attribute(self, obj):
        # Pass the entire object through to `to_representation()`,
        # instead of the standard attribute lookup. Otherwise,
        # obj is just a DRF relations.PKOnlyObject.
        return obj

    def to_representation(self, obj):
        if obj.pk is None:
            return None

        request = self.context.get('request', None)
        format = self.context.get('format', None)
        view_name = self.view_name or self.parent.opts.view_name

        kwargs = self.get_url_kwargs(obj)

        if format and self.format and self.format != format:
            format = self.format

        return api_reverse(view_name, kwargs=kwargs, request=request,
                           format=format)


class PlaceIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id')
    view_name = 'place-detail'


class AttachmentIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id', 'attachment_id')
    view_name = 'attachment-detail'


class SubmissionSetIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id',
                     'submission_set_name')
    view_name = 'submission-list'


class DataSetPlaceSetIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug')
    view_name = 'place-list'


class DataSetSubmissionSetIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'submission_set_name')
    view_name = 'dataset-submission-list'


class SubmissionIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id',
                     'submission_set_name', 'submission_id')
    view_name = 'submission-detail'


class TagIdentityField (serializers.HyperlinkedIdentityField):
    lookup_field = 'id'

    def __init__(self, *args, **kwargs):
        super(TagIdentityField, self).__init__(view_name='tag-detail', *args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'owner_username': obj.dataset.owner.get_username(),
            'dataset_slug': obj.dataset.slug,
            'tag_id': obj.pk
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)


class PlaceTagListIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id',)
    view_name = 'place-tag-list'


class PlaceTagIdentityField (serializers.HyperlinkedIdentityField):
    lookup_field = 'id'

    def __init__(self, *args, **kwargs):
        super(PlaceTagIdentityField, self).__init__(view_name='place-tag-detail', *args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'owner_username': obj.tag.dataset.owner.get_username(),
            'dataset_slug': obj.tag.dataset.slug,
            'place_id': obj.place.id,
            'place_tag_id': obj.pk
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)


class DataSetIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug')
    view_name = 'dataset-detail'


class AttachmentFileField (serializers.FileField):
    def to_representation(self, obj):
        return obj.storage.url(obj.name)


###############################################################################
#
# Serializer Mixins
# -----------------
#


class ActivityGenerator (object):
    def save(self, silent=False, **kwargs):
        request = self.context['request']
        silent_header = request.META.get('HTTP_X_SHAREABOUTS_SILENT', 'False')
        if not silent:
            silent = silent_header.lower() in ('true', 't', 'yes', 'y')
        request_source = request.META.get('HTTP_REFERER', '')
        return super(ActivityGenerator, self).save(
            silent=silent,
            source=request_source,
            **kwargs
        )


class EmptyModelSerializer (object):
    """
    A simple mixin that constructs an in-memory model when None is passed in
    as the object to to_representation.
    """
    def ensure_obj(self, obj):
        if obj is None: obj = self.opts.model()
        return obj


class DataBlobProcessor (EmptyModelSerializer):
    """
    Like ModelSerializer, but automatically serializes/deserializes a
    'data' JSON blob of arbitrary key/value pairs.
    """

    def to_internal_value(self, data):
        """
        Dict of native values <- Dict of primitive datatypes.
        """
        known_fields_object = super(DataBlobProcessor, self).to_internal_value(data)

        model = self.Meta.model
        blob = json.loads(self.instance.data) if self.partial else {}
        data_copy = OrderedDict()

        # Pull off any fields that the model doesn't know about directly
        # and put them into the data blob.
        known_fields = set(model._meta.get_fields())

        # Also ignore the following field names (treat them like reserved
        # words).
        known_fields.update(self.fields.keys())

        # And allow an arbitrary value field named 'data' (don't let the
        # data blob get in the way).
        known_fields.remove('data')

        # Split the incoming data into stuff that will be set straight onto
        # preexisting fields, and stuff that will go into the data blob.
        for key in data:
            if key not in known_fields:
                blob[key] = data[key]

        for key in known_fields_object:
            data_copy[key] = known_fields_object[key]

        data_copy['data'] = json.dumps(blob)

        if not self.partial:
            for field_name, field in self.fields.items():
                if (not field.read_only and field_name not in data_copy and field.default is not fields.empty):
                    data_copy[field_name] = field.default

        return data_copy

    # TODO: What is this replaced with?
    def convert_object(self, obj):
        attrs = super(DataBlobProcessor, self).convert_object(obj)

        data = json.loads(obj.data)
        del attrs['data']
        attrs.update(data)

        return attrs

    def explode_data_blob(self, data):
        blob = data.pop('data')

        blob_data = json.loads(blob)

        # Did the user not ask for private data? Remove it!
        if not self.is_flag_on(INCLUDE_PRIVATE_FIELDS_PARAM):
            for key in blob_data.keys():
                if key.startswith('private'):
                    del blob_data[key]

        data.update(blob_data)
        return data

    def to_representation(self, obj):
        obj = self.ensure_obj(obj)
        data = super(DataBlobProcessor, self).to_representation(obj)
        self.explode_data_blob(data)
        return data


class AttachmentSerializerMixin (EmptyModelSerializer, serializers.ModelSerializer):
    url = AttachmentIdentityField()

    def to_representation(self, instance):
        # add an 'id', which is the primary key
        ret = super(AttachmentSerializerMixin, self).to_representation(instance)
        ret['id'] = instance.pk
        return ret

###############################################################################
#
# User Data Strategies
# --------------------
# Shims for reading user data from various social authentication provider
# objects.
#

class DefaultUserDataStrategy (object):
    def extract_avatar_url(self, user_info):
        return ''

    def extract_full_name(self, user_info):
        return ''

    def extract_bio(self, user_info):
        return ''


class TwitterUserDataStrategy (object):
    def extract_avatar_url(self, user_info):
        try:
          url = user_info['profile_image_url_https']
        except:
          url = user_info['profile_image_url']

        url_pattern = '^(?P<path>.*?)(?:_normal|_mini|_bigger|)(?P<ext>\.[^\.]*)$'
        match = re.match(url_pattern, url)
        if match:
            return match.group('path') + '_bigger' + match.group('ext')
        else:
            return url

    def extract_full_name(self, user_info):
        return user_info['name']

    def extract_bio(self, user_info):
        return user_info['description']


class FacebookUserDataStrategy (object):
    def extract_avatar_url(self, user_info):
        url = user_info['picture']['data']['url']
        return url

    def extract_full_name(self, user_info):
        return user_info['name']

    def extract_bio(self, user_info):
        return user_info['about']


class GoogleUserDataStrategy (object):
    def extract_avatar_url(self, user_info):
       url = user_info['image']['url']
       return url

    def extract_full_name(self, user_info):
        name = user_info['name']['givenName'] + ' ' + user_info['name']['familyName']
        return name

    def extract_bio(self, user_info):
        return user_info["aboutMe"]

class ShareaboutsUserDataStrategy (object):
    """
    This strategy exists so that we can add avatars and full names to users
    that already exist in the system without them creating a Twitter or
    Facebook account.
    """
    def extract_avatar_url(self, user_info):
        return user_info.get('avatar_url', None)

    def extract_full_name(self, user_info):
        return user_info.get('full_name', None)

    def extract_bio(self, user_info):
        return user_info.get('bio', None)


###############################################################################
#
# Serializers
# -----------
#
# Many of the serializers below come in two forms:
#
# 1) A hyperlinked serializer -- this form includes URLs to the object's
#    related fields, as well as the object's own URL. This is useful for the
#    self-describing nature of the web API.
#
# 2) A simple serializer -- this form does not include any of the URLs in the
#    hyperlinked serializer. This is more useful for bulk data dumps where all
#    of the related data is included in a package.
#
 
class AttachmentListSerializer (AttachmentSerializerMixin):
    class Meta:
        model = models.Attachment
        exclude = ('thing', 'id')

class AttachmentInstanceSerializer (AttachmentSerializerMixin):
    class Meta:
        model = models.Attachment
        exclude = ('thing', 'id')

class DataSetPermissionSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.DataSetPermission
        exclude = ('id', 'dataset')

class GroupPermissionSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.GroupPermission
        exclude = ('id', 'group')

class KeyPermissionSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.KeyPermission
        exclude = ('id', 'key')

class OriginPermissionSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.OriginPermission
        exclude = ('id', 'origin')


class ApiKeySerializer (serializers.ModelSerializer):
    permissions = KeyPermissionSerializer(many=True)

    class Meta:
        model = apikey.models.ApiKey
        exclude = ('id', 'dataset', 'logged_ip', 'last_used')

class OriginSerializer (serializers.ModelSerializer):
    permissions = OriginPermissionSerializer(many=True)

    class Meta:
        model = cors.models.Origin
        exclude = ('id', 'dataset', 'logged_ip', 'last_used')

# Group serializers
class BaseGroupSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.Group
        exclude = ('submitters', 'id')


class SimpleGroupSerializer (BaseGroupSerializer):
    permissions = GroupPermissionSerializer(many=True)

    class Meta (BaseGroupSerializer.Meta):
        exclude = ('id', 'dataset', 'submitters')


class GroupSerializer (BaseGroupSerializer):
    dataset = DataSetRelatedField(queryset=models.DataSet.objects.all())

    class Meta (BaseGroupSerializer.Meta):
        pass

    def to_representation(self, obj):
        ret = {}
        ret['dataset'] = six.text_type(self.fields['dataset']
                                       .to_representation(obj.dataset))
        ret['name'] = obj.name
        ret['dataset_slug'] = obj.dataset.slug
        ret['permissions'] = [] 

        for permission in obj.permissions.all():
            ret['permissions'].append({
                'abilities': permission.get_abilities(),
                'submission_set': permission.submission_set
            })

        return ret


# User serializers
class BaseUserSerializer (serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    provider_type = serializers.SerializerMethodField()
    provider_id = serializers.SerializerMethodField()

    strategies = {
        'twitter': TwitterUserDataStrategy(),
        'facebook': FacebookUserDataStrategy(),
        'google-oauth2': GoogleUserDataStrategy(),
        'shareabouts': ShareaboutsUserDataStrategy()
    }
    default_strategy = DefaultUserDataStrategy()

    class Meta:
        model = models.User
        exclude = ('first_name', 'last_name', 'email', 'password', 'is_staff',
                   'is_active', 'is_superuser', 'last_login', 'date_joined',
                   'user_permissions')

    def get_strategy(self, obj):
        for social_auth in obj.social_auth.all():
            provider = social_auth.provider
            if provider in self.strategies:
                return social_auth.extra_data, self.strategies[provider]

        return None, self.default_strategy

    def get_name(self, obj):
        user_data, strategy = self.get_strategy(obj)
        return strategy.extract_full_name(user_data)

    def get_avatar_url(self, obj):
        user_data, strategy = self.get_strategy(obj)
        return strategy.extract_avatar_url(user_data)

    def get_provider_type(self, obj):
        for social_auth in obj.social_auth.all():
            return social_auth.provider
        else:
            return ''

    def get_provider_id(self, obj):
        for social_auth in obj.social_auth.all():
            return social_auth.uid
        else:
            return None

    def to_representation(self, obj):
        return {
            "name": self.get_name(obj),
            "avatar_url": self.get_avatar_url(obj),
            "provider_type": self.get_provider_type(obj),
            "provider_id": self.get_provider_id(obj),
            "id": obj.id,
            "username": obj.username
        } if obj else {}


class SimpleUserSerializer (BaseUserSerializer):
    """
    Generates a partial user representation, for use as submitter data in bulk
    data calls.
    """
    class Meta (BaseUserSerializer.Meta):
        exclude = BaseUserSerializer.Meta.exclude + ('groups',)


class UserSerializer (BaseUserSerializer):
    """
    Generates a partial user representation, for use as submitter data in API
    calls.
    """
    class Meta (BaseUserSerializer.Meta):
        exclude = BaseUserSerializer.Meta.exclude + ('groups',)


class FullUserSerializer (BaseUserSerializer):
    """
    Generates a representation of the current user. Since it's only for the
    current user, it should have all the user's information on it (all that
    the user would need).
    """
    groups = GroupSerializer(many=True, source='_groups', read_only=True)

    class Meta (BaseUserSerializer.Meta):
        pass

    def to_representation(self, obj):
        data = super(FullUserSerializer, self).to_representation(obj)
        if obj:
            group_serializer = self.fields['groups']
            groups_field = obj.get_groups()
            data['groups'] = group_serializer.to_representation(groups_field)
        return data


# DataSet place set serializer
class DataSetPlaceSetSummarySerializer (serializers.HyperlinkedModelSerializer):
    length = serializers.IntegerField(source='places_length')
    url = DataSetPlaceSetIdentityField()

    class Meta:
        model = models.DataSet
        fields = ('length', 'url')

    def get_place_counts(self, obj):
        """
        Return a dictionary whose keys are dataset ids and values are the
        corresponding count of places in that dataset.
        """
        # This will currently do a query for every dataset, not a single query
        # for all datasets. Generally a bad idea, but not a huge problem
        # considering the number of datasets at the moment. In the future,
        # we should perhaps use some kind of many_to_representation function.

        # if self.many:
        #     include_invisible = INCLUDE_INVISIBLE_PARAM in self.context['request'].GET
        #     places = models.Place.objects.filter(dataset__in=obj)
        #     if not include_invisible:
        #         places = places.filter(visible=True)

        #     # Unset any default ordering
        #     places = places.order_by()

        #     places = places.values('dataset').annotate(length=Count('dataset'))
        #     return dict([(place['dataset'], place['length']) for place in places])

        # else:
        include_invisible = INCLUDE_INVISIBLE_PARAM in self.context['request'].GET
        places = obj.places
        if not include_invisible:
            places = places.filter(visible=True)
        return {obj.pk: places.count()}

    def to_representation(self, obj):
        place_count_map = self.get_place_counts(obj)
        obj.places_length = place_count_map.get(obj.pk, 0)
        data = super(DataSetPlaceSetSummarySerializer, self).to_representation(obj)
        return data


# DataSet submission set serializer
class DataSetSubmissionSetSummarySerializer (serializers.HyperlinkedModelSerializer):
    length = serializers.IntegerField(source='submission_set_length')
    url = DataSetSubmissionSetIdentityField()

    class Meta:
        model = models.DataSet
        fields = ('length', 'url')

    def is_flag_on(self, flagname):
        request = self.context['request']
        param = request.GET.get(flagname, 'false')
        return param.lower() not in ('false', 'no', 'off')

    def get_submission_sets(self, dataset):
        include_invisible = self.is_flag_on(INCLUDE_INVISIBLE_PARAM)
        submission_sets = defaultdict(list)
        for submission in dataset.submissions.all():
            if include_invisible or submission.visible:
                set_name = submission.set_name
                submission_sets[set_name].append(submission)
        return {dataset.id: submission_sets}

    def to_representation(self, obj):
        request = self.context['request']
        submission_sets_map = self.get_submission_sets(obj)
        sets = submission_sets_map.get(obj.id, {})
        summaries = {}
        for set_name, submission_set in sets.iteritems():
            # Ensure the user has read permission on the submission set.
            user = getattr(request, 'user', None)
            client = getattr(request, 'client', None)
            dataset = obj
            if not check_data_permission(user, client, None, 'retrieve', dataset, set_name):
                continue

            obj.submission_set_name = set_name
            obj.submission_set_length = len(submission_set)
            summaries[set_name] = super(DataSetSubmissionSetSummarySerializer, self).to_representation(obj)
        return summaries


class SubmittedThingSerializer (ActivityGenerator, DataBlobProcessor):
    def is_flag_on(self, flagname):
        request = self.context['request']
        param = request.GET.get(flagname, 'false')
        return param.lower() not in ('false', 'no', 'off')


# Place serializers
class BasePlaceSerializer (SubmittedThingSerializer,
                           serializers.ModelSerializer):
    geometry = GeometryField(format='wkt')
    attachments = AttachmentListSerializer(read_only=True, many=True)
    submitter = SimpleUserSerializer(required=False, allow_null=True)
    private = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = models.Place

    def get_submission_sets(self, place):
        include_invisible = self.is_flag_on(INCLUDE_INVISIBLE_PARAM)
        submission_sets = defaultdict(list)
        for submission in place.submissions.all():
            if include_invisible or submission.visible:
                set_name = submission.set_name
                submission_sets[set_name].append(submission)
        return submission_sets

    def summary_to_native(self, set_name, submissions):
        return {
            'name': set_name,
            'length': len(submissions)
        }

    def get_submission_set_summaries(self, place):
        """
        Get a mapping from place id to a submission set summary dictionary.
        Get this for the entire dataset at once.
        """
        request = self.context['request']

        submission_sets = self.get_submission_sets(place)
        summaries = {}
        for set_name, submissions in submission_sets.iteritems():
            # Ensure the user has read permission on the submission set.
            user = getattr(request, 'user', None)
            client = getattr(request, 'client', None)
            dataset = getattr(request, 'get_dataset', lambda: None)()

            if not check_data_permission(user, client, None, 'retrieve', dataset, set_name):
                continue

            summaries[set_name] = self.summary_to_native(set_name, submissions)

        return summaries

    def get_tag_summary(self, place):
        """
        Get a mapping from place id to a tag summary dictionary.
        Get this for the entire dataset at once.
        """
        url_field = PlaceTagListIdentityField()
        url_field.context = self.context
        url = url_field.to_representation(place)
        return {
            'url': url,
            'length': place.tags.count()
        }

    def get_detailed_tags(self, place):
        """
        Get a mapping from place id to an array of place tag details.
        TODO: Get this for the entire dataset at once.
        """
        request = self.context['request']

        tags = place.tags.all()

        return [PlaceTagSerializer(context={'request': request})
                .to_representation(tag) for tag in tags]

    def set_to_native(self, set_name, submissions):
        serializer = SimpleSubmissionSerializer(submissions, many=True, context=self.context)
        return serializer.data

    def get_detailed_submission_sets(self, place):
        """
        Get a mapping from place id to a detiled submission set dictionary.
        Get this for the entire dataset at once.
        """
        request = self.context['request']

        submission_sets = self.get_submission_sets(place)
        details = {}
        for set_name, submissions in submission_sets.iteritems():
            # Ensure the user has read permission on the submission set.
            user = getattr(request, 'user', None)
            client = getattr(request, 'client', None)
            dataset = getattr(request, 'get_dataset', lambda: None)()

            if not check_data_permission(user, client, None, 'retrieve', dataset, set_name):
                continue

            # We know that the submission datasets will be the same as the
            # place dataset, so say so and avoid an extra query for each.
            for submission in submissions:
                submission.dataset = place.dataset

            details[set_name] = self.set_to_native(set_name, submissions)

        return details

    def attachments_to_native(self, obj):
        return [AttachmentListSerializer(a, context=self.context).data for a in obj.attachments.filter(visible=True)]

    def submitter_to_native(self, obj):
        return SimpleUserSerializer(obj.submitter).data if obj.submitter else None

    def to_representation(self, obj):
        obj = self.ensure_obj(obj)
        fields = self.get_fields()

        request = self.context.get('request', None)

        data = {
            'id': obj.pk,  # = serializers.PrimaryKeyRelatedField(read_only=True)
            'geometry': str(obj.geometry or 'POINT(0 0)'),  # = GeometryField(format='wkt')
            'dataset': fields['dataset'].get_url(obj.dataset, request),
            'attachments': self.attachments_to_native(obj),  # = AttachmentSerializer(read_only=True)
            'submitter': self.submitter_to_native(obj),
            'data': obj.data,
            'visible': obj.visible,
            'created_datetime': obj.created_datetime.isoformat() if obj.created_datetime else None,
            'updated_datetime': obj.updated_datetime.isoformat() if obj.updated_datetime else None,
        }
        # If the place is public, don't inlude the 'private' attribute
        # in the serialized representation. This minimizes the JSON
        # payload:
        if obj.private:
            data['private'] = obj.private

        if 'url' in fields:
            field = fields['url']
            field.context = self.context
            data['url'] = field.to_representation(obj)

        data = self.explode_data_blob(data)

        # data = super(PlaceSerializer, self).to_representation(obj)

        # TODO: Put this flag value directly in to the serializer context,
        #       instead of relying on the request query parameters.
        if not self.is_flag_on(INCLUDE_SUBMISSIONS_PARAM):
            submission_sets_getter = self.get_submission_set_summaries
        else:
            submission_sets_getter = self.get_detailed_submission_sets

        if not self.is_flag_on(INCLUDE_TAGS_PARAM):
            tags_getter = self.get_tag_summary
        else:
            tags_getter = self.get_detailed_tags

        data['submission_sets'] = submission_sets_getter(obj)
        data['tags'] = tags_getter(obj)

        if hasattr(obj, 'distance'):
            data['distance'] = str(obj.distance)

        return data


class SimplePlaceSerializer (BasePlaceSerializer):
    class Meta (BasePlaceSerializer.Meta):
        read_only_fields = ('dataset',)


class PlaceListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        place_mapping = {place.id: place for place in instance}

        ret = []
        for item in validated_data:
            place_id = item['id'] if 'id' in item else None
            place = None
            if place_id is not None:
                place = place_mapping.get(place_id, None)
            update_or_create_data = item.copy()
            url_kwargs = self.context['view'].kwargs
            dataset = models.DataSet.objects.get(slug=url_kwargs['dataset_slug'])
            update_or_create_data['dataset_id'] = dataset.id
            if place is None:
                ret.append(self.child.create(update_or_create_data))
            else:
                ret.append(self.child.update(place, update_or_create_data))

        return ret


class PlaceSerializer (BasePlaceSerializer,
                       serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(required=False)
    url = PlaceIdentityField()
    dataset = DataSetRelatedField(queryset=models.DataSet.objects.all(), required=False)
    submitter = UserSerializer(required=False, allow_null=True)

    class Meta (BasePlaceSerializer.Meta):
        list_serializer_class = PlaceListSerializer

    def summary_to_native(self, set_name, submissions):
        url_field = SubmissionSetIdentityField()
        url_field.context = self.context
        set_url = url_field.to_representation(submissions[0])

        return {
            'name': set_name,
            'length': len(submissions),
            'url': set_url,
        }

    def set_to_native(self, set_name, submissions):
        serializer = SubmissionSerializer(submissions, many=True, context=self.context)
        return serializer.data

    def submitter_to_native(self, obj):
        return UserSerializer(obj.submitter).data if obj.submitter else None


# Submission serializers
class BaseSubmissionSerializer (SubmittedThingSerializer, serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    attachments = AttachmentListSerializer(read_only=True, many=True)
    submitter = SimpleUserSerializer(required=False, allow_null=True)

    class Meta:
        model = models.Submission
        exclude = ('set_name',)


class SimpleSubmissionSerializer (BaseSubmissionSerializer):
    class Meta (BaseSubmissionSerializer.Meta):
        read_only_fields = ('dataset', 'place_model')


class SubmissionListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        submission_mapping = {submission.id: submission for submission in instance}

        ret = []
        for item in validated_data:
            submission_id = item['id'] if 'id' in item else None
            submission = None
            if submission_id is not None:
                submission = submission_mapping.get(submission_id, None)
            update_or_create_data = item.copy()
            url_kwargs = self.context['view'].kwargs
            dataset = models.DataSet.objects.get(slug=url_kwargs['dataset_slug'])
            update_or_create_data['dataset_id'] = dataset.id
            update_or_create_data['place_model_id'] = url_kwargs['place_id']
            update_or_create_data['set_name'] = url_kwargs['submission_set_name']
            if submission is None:
                ret.append(self.child.create(update_or_create_data))
            else:
                ret.append(self.child.update(submission, update_or_create_data))

        return ret


class SubmissionSerializer (BaseSubmissionSerializer,
                            serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(required=False)
    url = SubmissionIdentityField()
    dataset = DataSetRelatedField(queryset=models.DataSet.objects.all(), required=False)
    set = SubmissionSetRelatedField(source='*', required=False, read_only=True)
    place = PlaceRelatedField(required=False, source='place_model')
    submitter = UserSerializer(required=False, allow_null=True)

    class Meta (BaseSubmissionSerializer.Meta):
        model = models.Submission
        list_serializer_class = SubmissionListSerializer
        exclude = BaseSubmissionSerializer.Meta.exclude + ('place_model',)


class TagSerializer (serializers.ModelSerializer):
    url = TagIdentityField()

    class Meta:
        model = models.Tag
        fields = ['id', 'url', 'name', 'parent', 'color', 'is_enabled', 'children']


class PlaceTagSerializer (serializers.ModelSerializer):
    url = PlaceTagIdentityField()
    id = serializers.IntegerField(read_only=True, required=False)
    place = PlaceRelatedField()
    submitter = SimpleUserSerializer(required=False, allow_null=True)
    note = serializers.CharField(allow_blank=True)
    tag = TagRelatedField()
    created_datetime = serializers.DateTimeField(required=False)
    updated_datetime = serializers.DateTimeField(required=False)

    class Meta:
        model = models.PlaceTag
        fields = ('url', 'id', 'place', 'submitter', 'note', 'tag', 'created_datetime', 'updated_datetime')


# DataSet serializers
class BaseDataSetSerializer (EmptyModelSerializer,
                             serializers.ModelSerializer):
    class Meta:
        model = models.DataSet

    # TODO: We may need to re-implement this if want support for serving HTML
    # in the browseable api form
    # def to_representation(self, obj):
    #     obj = self.ensure_obj(obj)
    #     fields = self.get_fields()

    #     data = {
    #         'id': obj.pk,
    #         'slug': obj.slug,
    #         'display_name': obj.display_name,
    #         'owner': fields['owner'].to_representation(obj) if obj.owner_id else None,
    #     }

    #     if 'places' in fields:
    #         fields['places'].context = self.context
    #         data['places'] = fields['places'].to_representation(obj)

    #     if 'submission_sets' in fields:
    #         fields['submission_sets'].context = self.context
    #         data['submission_sets'] = fields['submission_sets'].to_representation(obj)

    #     if 'url' in fields:
    #         data['url'] = fields['url'].to_representation(obj)

    #     if 'keys' in fields: data['keys'] = fields['keys'].to_representation(obj)
    #     if 'origins' in fields: data['origins'] = fields['origins'].to_representation(obj)
    #     if 'groups' in fields: data['groups'] = fields['groups'].to_representation(obj)
    #     if 'permissions' in fields: data['permissions'] = fields['permissions'].to_representation(obj)

    #     # Construct a SortedDictWithMetaData to get the brosable API form
    #     ret = self._dict_class(data)
    #     ret.fields = self._dict_class()
    #     for field_name, field in fields.iteritems():
    #         default = getattr(field, 'get_default_value', lambda: None)()
    #         value = data.get(field_name, default)
    #         ret.fields[field_name] = self.augment_field(field, field_name, field_name, value)
    #     return ret

class SimpleDataSetSerializer (BaseDataSetSerializer, serializers.ModelSerializer):
    keys = ApiKeySerializer(many=True, read_only=False)
    origins = OriginSerializer(many=True, read_only=False)
    groups = SimpleGroupSerializer(many=True, read_only=False)
    permissions = DataSetPermissionSerializer(many=True, read_only=False)

    class Meta (BaseDataSetSerializer.Meta):
        pass


class DataSetSerializer (BaseDataSetSerializer, serializers.HyperlinkedModelSerializer):
    url = DataSetIdentityField()
    owner = UserRelatedField(read_only=True)

    places = DataSetPlaceSetSummarySerializer(source='*', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    submission_sets = DataSetSubmissionSetSummarySerializer(source='*', read_only=True)

    load_from_url = serializers.URLField(write_only=True, required=False)

    class Meta (BaseDataSetSerializer.Meta):
        validators = []
        pass

    def validate_load_from_url(self, attrs, source):
        url = attrs.get(source)
        if url:
            # Verify that at least a head request on the given URL is valid.
            import requests
            head_response = requests.head(url)
            if head_response.status_code != 200:
                raise ValidationError('There was an error reading from the URL: %s' % head_response.content)
        return attrs

    # NOTE: as part of the DRF3 upgrade we're commenting this method out pending
    #       further investigation. DRF3 has replaced save_object() with other
    #       methods, but the correct refactor of the below method is unclear at
    #       the moment. Major functionality of the API does not seem to be
    #       affected by removing this method however.
    # def save_object(self, obj, **kwargs):
    #     obj.save(**kwargs)

    #     # Load any bulk dataset definition supplied
    #     if hasattr(self, 'load_url') and self.load_url:
    #         # Somehow, make sure there's not already some loading going on.
    #         # Then, do:
    #         from .tasks import load_dataset_archive
    #         load_dataset_archive.apply_async(args=(obj.id, self.load_url,))

    def to_internal_value(self, data):
        if data and 'load_from_url' in data:
            self.load_url = data.pop('load_from_url')
            if self.load_url and isinstance(self.load_url, list):
                self.load_url = unicode(self.load_url[0])
        return super(DataSetSerializer, self).to_internal_value(data)


# Action serializer
class ActionSerializer (EmptyModelSerializer, serializers.ModelSerializer):
    target_type = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()

    class Meta:
        model = models.Action
        exclude = ('thing', 'source')

    def get_target_type(self, obj):
        try:
            if obj.thing.place is not None:
                return u'place'
        except models.Place.DoesNotExist:
            pass

        return obj.thing.submission.set_name

    def get_target(self, obj):
        try:
            if obj.thing.place is not None:
                serializer = PlaceSerializer(obj.thing.place, context=self.context)
            else:
                serializer = SubmissionSerializer(obj.thing.submission, context=self.context)
        except models.Place.DoesNotExist:
            serializer = SubmissionSerializer(obj.thing.submission, context=self.context)

        return serializer.data


###############################################################################
#
# Pagination Serializers
# ----------------------
#

class MetadataPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'
    page_size = 50

    def get_paginated_response(self, data):
        return Response({
            'metadata': {
                'length': self.page.paginator.count,
                'page': self.page.number,
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'results': data
        })

class FeatureCollectionPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'
    page_size = 50

    def get_paginated_response(self, data):
        return Response({
            'metadata': {
                'length': self.page.paginator.count,
                'page': self.page.number,
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'type': 'FeatureCollection',
            'features': data
        })
