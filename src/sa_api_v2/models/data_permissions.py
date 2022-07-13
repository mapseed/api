from django.contrib.gis.db import models
from django.db.models.signals import post_save
from .. import utils
from .core import CacheClearingModel, Master
from .core import DataSet
from .core import Place
from .mixins import CloneableModelMixin

class DataPermissionManager (models.Manager):
    use_for_related_fields = True

    @utils.memo
    def all_permissions(self):
        return self.all()

    def add_permission(self, submission_set, can_create, can_retrieve, can_update, can_destroy, can_access_protected=False, priority=None):
        PermModel = self.model
        return self.add(PermModel(
            # TODO: rename this to 'resource'
            submission_set=submission_set,
            can_create=can_create,
            can_retrieve=can_retrieve,
            can_update=can_update,
            can_destroy=can_destroy,
            can_access_protected=can_access_protected,
            priority=priority), bulk=False)


class DataPermission (CloneableModelMixin, CacheClearingModel, models.Model):
    """
    Rules for what permissions a given authentication method affords.
    """
    # TODO: rename this 'submission_set' to 'resource'
    # TODO: enable resources with selectors like
    # "tags:3>*" or "tags:3>5>*". That way, group will have access to
    # that tag, and any of its children.
    submission_set = models.CharField(max_length=128, blank=True, help_text='Either the name of a submission set (e.g., "comments"), "tags", or "places". Leave blank to refer to all things.')
    can_retrieve = models.BooleanField(default=True)
    can_create = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_destroy = models.BooleanField(default=False)
    can_access_protected = models.BooleanField(default=False)
    priority = models.PositiveIntegerField(blank=True)

    objects = DataPermissionManager()

    class Meta:
        abstract = True
        ordering = ('priority',)

    def parent():
        def fget(self): return getattr(self, self.parent_attr)
        def fset(self, value): setattr(self, self.parent_attr, value)
        return locals()
    parent = property(**parent())

    def siblings():
        def fget(self): return self.parent.permissions.all()
        return locals()
    siblings = property(**siblings())

    def dataset():
        def fget(self): return self.parent.dataset
        return locals()
    dataset = property(**dataset())

    def get_abilities(self):
        abilities = []
        if self.can_create: abilities.append('create')
        if self.can_retrieve: abilities.append('retrieve')
        if self.can_update: abilities.append('update')
        if self.can_destroy: abilities.append('destroy')
        if self.can_access_protected: abilities.append('can_access_protected')

        return abilities

    def abilities(self):
        abilities = self.get_abilities()
        things = self.submission_set if self.submission_set.strip() not in ('', '*') else 'anything'

        if abilities:
            if len(abilities) > 1: abilities[-1] = 'or ' + abilities[-1]
            return 'can ' + ', '.join(abilities) + ' ' + things
        else:
            return 'can not create, retrieve, update, or destroy ' + things + ' at all'

    def clear_instance_cache(self):
        return self.dataset.clear_instance_cache()

    def save(self, *args, **kwargs):
        if self.priority is None:
            try:
                lowest = self.siblings.order_by('-priority')[0]
                self.priority = lowest.priority + 1
            except IndexError:
                self.priority = 0

        return super(DataPermission, self).save(*args, **kwargs)


class DataSetPermission (DataPermission):
    dataset = models.ForeignKey('DataSet', related_name='permissions')
    parent_attr = 'dataset'

    class Meta:
        app_label = 'sa_api_v2'

    def __unicode__(self):
        return '%s %s' % ('submitters', self.abilities())


class GroupPermission (DataPermission):
    group = models.ForeignKey('Group', related_name='permissions')
    parent_attr = 'group'

    class Meta:
        app_label = 'sa_api_v2'

    def __unicode__(self):
        return '%s %s' % (self.group, self.abilities())


class KeyPermission (DataPermission):
    key = models.ForeignKey('sa_api_v2.ApiKey', related_name='permissions')
    parent_attr = 'key'

    class Meta:
        app_label = 'sa_api_v2'

    def __unicode__(self):
        return 'submitters %s' % (self.abilities(),)


class OriginPermission (DataPermission):
    origin = models.ForeignKey('sa_api_v2.Origin', related_name='permissions')
    parent_attr = 'origin'

    class Meta:
        app_label = 'sa_api_v2'

    def __unicode__(self):
        return 'submitters %s' % (self.abilities(),)


def create_data_permissions(sender, instance, created, **kwargs):
    """
    Create a default permission instance for a new dataset.
    """
    cloned = hasattr(instance, '_cloned_from')
    if created and not cloned:
        DataSetPermission.objects.create(dataset=instance, submission_set='*',
            can_retrieve=True, can_create=False, can_update=False, can_destroy=False)
post_save.connect(create_data_permissions, sender=DataSet, dispatch_uid="dataset-create-permissions")


def any_allow(permissions, do_action, resource, protected=False):
    """
    Check whether any of the data permissions in the managed set allow the
    action on a submission set with the given name. Specify whether the action
    is on protected data.
    """
    for permission in permissions:
        # TODO: rename this to permission.resource and handle a "tags:1>3>*" use case
        if (permission.submission_set in (resource, '*')
            and getattr(permission, 'can_' + do_action, False)
            and (permission.can_access_protected or not protected)):
            return True
    return False


def check_data_permission(user, client, place_id, do_action, dataset, resource, protected=False):
    """
    Check whether the given user has permission on the resource in
    the context of the given client (e.g., an API key or an origin). Specify
    whether the permission is for protected data.
    """
    if do_action not in ('retrieve', 'create', 'update', 'destroy'):
        raise ValueError

    if user and user.is_superuser:
        return True

    # Owner can do anything
    if user and dataset and user.id == dataset.owner_id:
        return True

    # Start with the dataset permission
    if dataset and any_allow(dataset.permissions.all(), do_action, resource, protected):
        return True

    # Then the client permission
    if client is not None:
        if (client.dataset == dataset and
            any_allow(client.permissions.all(), do_action, resource, protected)):
            return True

    # Next, check the user's groups
    if user is not None and user.is_authenticated():
        for group in user._groups.all():
            if (dataset and group.dataset_id == dataset.id and
                any_allow(group.permissions.all(), do_action, resource, protected)):
                return True

    # Finally, check place permissions:
    # 1) If user is the place's submitter and trying to Update/Delete the place, then allow
    # 2) if the place is private, and user doesn't have protected privileges (checked above), and user isn't the
    # submitter, then don't allow
    if place_id is not None and user is not None and user.is_authenticated:
        target_place = Place.objects.get(id=place_id)
        submitter = getattr(target_place, 'submitter', None)
        place_submitter_id = getattr(submitter, 'id', None)
        user_id = getattr(user, 'id', None)
        if place_submitter_id == user_id:
            return True
        if target_place.private:
            return False

    return False
