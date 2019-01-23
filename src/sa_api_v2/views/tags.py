from .. import models
from rest_framework.response import Response
from django.core.urlresolvers import reverse
from rest_framework import status
from django.shortcuts import get_object_or_404
from .base_views import (
    CachedResourceMixin,
    OwnedResourceMixin,
    FilteredResourceMixin,
)
from rest_framework import generics
from .. import serializers
# from .. import parsers
from rest_framework_bulk import generics as bulk_generics
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect


class TagInstanceView (generics.RetrieveAPIView):
    """
    GET
    ---
    Get a particular PlaceTag

    **Authentication**: Basic, session, or key auth *(optional)*

    """

    model = models.Tag
    serializer_class = serializers.TagSerializer
    # Allows the data permissions to check the group permission
    # TODO: Make this a function that accepts a Tag object, and
    # returns its resource id (eg: "tag:1>3")
    # resource_id = 'tags'

    def get_object_or_404(self, pk):
        try:
            return self.model.objects\
                .filter(pk=pk)\
                .select_related(
                    # 'tag',  # Do we need this?
                    'dataset',
                    'parent',
                    # .prefetch_related('submitter__social_auth')\  # do we need this?
                )\
                .get()
        except self.model.DoesNotExist:
            raise Http404

    def get_object(self, queryset=None):
        tag_id = self.kwargs['tag_id']
        obj = self.get_object_or_404(tag_id)
        # self.verify_object(obj)
        return obj


class TagListView (bulk_generics.ListCreateBulkUpdateAPIView):
    """

    GET
    ---
    Get all the Place Tags for a place

    ------------------------------------------------------------
    """

    model = models.Tag
    serializer_class = serializers.TagSerializer
    pagination_class = serializers.MetadataPagination
    # pagination_class = serializers.FeatureCollectionPagination
    # renderer_classes = (renderers.GeoJSONRenderer, renderers.GeoJSONPRenderer) + OwnedResourceMixin.renderer_classes[2:]
    # parser_classes = (parsers.GeoJSONParser,) + OwnedResourceMixin.parser_classes[1:]

    def get_queryset(self):
        # dataset = self.get_dataset()
        # place = self.get_place_model(dataset)
        # queryset = self.filter_queryset(models.PlaceTag.objects.all())
        slug = self.kwargs['dataset_slug']
        dataset = models.DataSet.objects.get(slug=slug)
        queryset = models.Tag.objects.all()

        # If we're updating, limit the queryset to the items that are being
        # updated.
        # if self.request.method.upper() == 'PUT':
        #     data = self.request.data
        #     ids = [obj['id'] for obj in data if 'id' in obj]
        #     queryset = queryset.filter(pk__in=ids)

        # Do we need to prefetch all of these???
        queryset = queryset.filter(dataset=dataset)\
                           .select_related('dataset', 'dataset__owner')
        # .prefetch_related(
        #     'submitter__social_auth',
        #     'submitter___groups',
        #     # 'submitter___groups__dataset',
        #     # 'submitter___groups__dataset__owner',
        #     # 'submissions',
        #     # 'attachments')
        #     )

        return queryset


class PlaceTagInstanceView (CachedResourceMixin, OwnedResourceMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET
    ---
    Get a particular PlaceTag

    **Authentication**: Basic, session, or key auth *(optional)*

    PUT
    ---
    Update a PlaceTag

    **Authentication**: Basic, session, or key auth *(required)*

    DELETE
    ------
    Delete a PlaceTag

    **Authentication**: Basic, session, or key auth *(required)*

    ------------------------------------------------------------
    """

    model = models.PlaceTag
    serializer_class = serializers.PlaceTagSerializer
    # Allows the data permissions to check the group permission
    # TODO: Make this a function that accepts a Tag object, and
    # returns its resource id (eg: "tag:1>3")
    resource_id = 'tags'

    def get_object_or_404(self, pk):
        try:
            return self.model.objects\
                .filter(pk=pk)\
                .select_related(
                    'place',
                    'place__dataset',
                    'place__dataset__owner',
                    'tag',
                    'tag__dataset',
                    'submitter'
                )\
                .get()
        except self.model.DoesNotExist:
            raise Http404

    def get_object(self, queryset=None):
        place_tag_id = self.kwargs['place_tag_id']
        obj = self.get_object_or_404(place_tag_id)
        self.verify_object(obj)
        return obj


class PlaceTagListView (CachedResourceMixin, OwnedResourceMixin,
                        FilteredResourceMixin, bulk_generics.ListCreateBulkUpdateAPIView):
    """

    GET
    ---
    Get all the Place Tags for a place

    POST
    ----

    Create a Place Tag

    PUT
    ----

    Update an existing Place Tag

    **Authentication**: Basic, session, or key auth *(required)*

    ------------------------------------------------------------
    """

    model = models.PlaceTag
    serializer_class = serializers.PlaceTagSerializer
    pagination_class = serializers.MetadataPagination
    resource_id = 'tags'
    # pagination_class = serializers.FeatureCollectionPagination
    # renderer_classes = (renderers.GeoJSONRenderer, renderers.GeoJSONPRenderer) + OwnedResourceMixin.renderer_classes[2:]
    # parser_classes = (parsers.GeoJSONParser,) + OwnedResourceMixin.parser_classes[1:]

    # Overriding create so we can sanitize submitted fields, which may
    # contain raw HTML intended to be rendered in the client
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        dataset = self.get_dataset()

        if serializer.is_valid():
            user = self.request.user
            if 'submitter' in serializer.validated_data:
                user = serializer.validated_data['submitter']
            self.object = serializer.save(
                force_insert=True,
                submitter=user if user is not None and user.is_authenticated() else None,
                place=self.get_place_model(dataset),
                # note=serializer.validated_data['note'],
                dataset=self.get_dataset()
            )
            self.post_save(self.object, created=True)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_place_model(self, dataset):
        place_id = self.kwargs[self.place_id_kwarg]
        place = get_object_or_404(models.Place, dataset=dataset, id=place_id)
        return place

    def get_cache_metakey(self):
        metakey_kwargs = self.kwargs.copy()
        metakey_kwargs.pop('pk_list', None)
        prefix = reverse('place-tags-list', kwargs=metakey_kwargs)
        return prefix + '_keys'

    def get_queryset(self):
        dataset = self.get_dataset()
        place = self.get_place_model(dataset)
        # queryset = self.filter_queryset(models.PlaceTag.objects.all())
        queryset = models.PlaceTag.objects.all()

        # If we're updating, limit the queryset to the items that are being
        # updated.
        if self.request.method.upper() == 'PUT':
            data = self.request.data
            ids = [obj['id'] for obj in data if 'id' in obj]
            queryset = queryset.filter(pk__in=ids)

        # Do we need to prefetch all of these???
        queryset = queryset.filter(place=place)\
            .select_related('dataset', 'dataset__owner', 'place', 'submitter')\
            .prefetch_related(
                'submitter__social_auth',
                'submitter___groups',
                # 'submitter___groups__dataset',
                # 'submitter___groups__dataset__owner',
                # 'submissions',
                # 'attachments')
                )

        return queryset
