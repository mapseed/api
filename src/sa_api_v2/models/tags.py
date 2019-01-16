from closuretree.models import ClosureModel
from django.contrib.gis.db import models
from .core import DataSet, Place, TimeStampedModel
from .profiles import User


class Label(ClosureModel):
    name = models.CharField(max_length=24)
    parent = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, null=True, blank=True)
    dataset = models.ForeignKey(DataSet, related_name='labels', on_delete=models.CASCADE)

    def __unicode__(self):
        if self.parent:
            return "{parent_name}:{name}".format(name=self.name,
                                                 parent_name=self.parent.__unicode__())
        else:
            return self.name

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_label'
        ordering = ['name']


class Tag(TimeStampedModel):
    label = models.ForeignKey(Label, related_name='label', null=False)
    submitter = models.ForeignKey(User, related_name='+', null=True)
    place = models.ForeignKey(Place, related_name='tags')
    note = models.TextField(blank=True)

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_tag'
        ordering = ['-created_datetime']
