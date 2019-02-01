import re
from closuretree.models import ClosureModel
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from .core import DataSet, Place, TimeStampedModel
from .. import cache
from .profiles import User
from django.core.validators import RegexValidator

color_re = re.compile('^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
validate_color = RegexValidator(regex=color_re, message='Enter a valid color.', code='invalid')


class Tag(ClosureModel):
    name = models.CharField(max_length=24)
    parent = models.ForeignKey('self', related_name='children',
                               on_delete=models.CASCADE, null=True, blank=True)
    dataset = models.ForeignKey(DataSet, related_name='tags', on_delete=models.CASCADE)
    color = models.CharField(max_length=7, validators=[validate_color], null=True, blank=True)
    is_enabled = models.BooleanField(default=True)

    def __unicode__(self):
        if self.parent:
            return "{parent_name}:{name}".format(name=self.name,
                                                 parent_name=self.parent.__unicode__())
        else:
            return self.name

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_tag'
        ordering = ['name']


class PlaceTag(TimeStampedModel):
    tag = models.ForeignKey(Tag, related_name='place_tags', null=False, on_delete=models.CASCADE)
    submitter = models.ForeignKey(User, related_name='+', null=True, blank=True, on_delete=models.SET_NULL)
    place = models.ForeignKey(Place, related_name='tags', on_delete=models.CASCADE)
    note = models.TextField(blank=True)

    cache = cache.PlaceTagCache()

    def save(self, *args, **kwargs):
        self.clean()
        super(PlaceTag, self).save(*args, **kwargs)

    def clean(self):
        if hasattr(self, 'tag') and hasattr(self, 'place') and\
           self.tag.dataset.id != self.place.dataset.id:
            raise ValidationError("The Tag must come from the same DataSet as the Place.")

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_place_tag'
        ordering = ['-created_datetime']
