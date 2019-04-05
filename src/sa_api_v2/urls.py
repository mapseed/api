from django.conf.urls import url, include
from django.contrib.auth.views import login
from django.http import HttpResponse
from . import views

urlpatterns = [
    url(r'^$',
        views.ShareaboutsAPIRootView.as_view(),
        name='api-root'),
    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/places/(?P<thing_id>\d+)/attachments$',
        views.AttachmentListView.as_view(),
        name='place-attachments'),

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/places/(?P<place_id>\d+)/attachments/(?P<attachment_id>\d+)$',
        views.AttachmentInstanceView.as_view(),
        name='attachment-detail'),

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/places/(?P<place_id>\d+)/(?P<submission_set_name>[^/]+)/(?P<thing_id>\d+)/attachments$',
        views.AttachmentListView.as_view(),
        name='submission-attachments'),

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/actions$',
        views.ActionListView.as_view(),
        name='action-list'),

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/metadata$',
        views.DataSetMetadataView.as_view(),
        name='dataset-metadata'),

    # bulk data snapshots

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/(?P<submission_set_name>[^/]+)/snapshots$',
        views.DataSnapshotRequestListView.as_view(),
        name='dataset-snapshot-list'),
    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/(?P<submission_set_name>[^/]+)/snapshots/(?P<data_guid>[^/.]+)(:?\.(?P<format>[^/]+))?$',
        views.DataSnapshotInstanceView.as_view(),
        name='dataset-snapshot-instance'),

    # place tags
    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/places/(?P<place_id>\d+)/tags/(?P<place_tag_id>\d+)$',
        views.PlaceTagInstanceView.as_view(),
        name='place-tag-detail'),

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/places/(?P<place_id>\d+)/tags$',
        views.PlaceTagListView.as_view(),
        name='place-tag-list'),

    # submission sets (votes, comments)

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/places/(?P<place_id>\d+)/(?P<submission_set_name>[^/]+)/(?P<submission_id>\d+)$',
        views.SubmissionInstanceView.as_view(),
        name='submission-detail'),
    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/places/(?P<place_id>\d+)/(?P<submission_set_name>[^/]+)(?:/(?P<pk_list>(?:\d+,)+\d+))?$',
        views.SubmissionListView.as_view(),
        name='submission-list'),

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/places/(?P<place_id>\d+)$',
        views.PlaceInstanceView.as_view(),
        name='place-detail'),
    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/places(?:/(?P<pk_list>(?:\d+,)+\d+))?$',
        views.PlaceListView.as_view(),
        name='place-list'),

    # HACK: Adding this route so that the downloaded file has the `.csv` extension:
    # https://github.com/mapseed/api/issues/139
    # Endpoint accepts a page_size, include_private, and format query params.
    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/mapseed-places.csv',
        views.PlaceListView.as_view(),
        name='place-list'),

    url(r'^~/datasets$',
        views.AdminDataSetListView.as_view(),
        name='admin-dataset-list'),

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/keys$',
        views.ApiKeyListView.as_view(),
        name='apikey-list'),

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/origins$',
        views.OriginListView.as_view(),
        name='origin-list'),

    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)$',
        views.DataSetInstanceView.as_view(),
        name='dataset-detail'),
    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/tags/(?P<tag_id>\d+)$',
        views.TagInstanceView.as_view(),
        name='tag-detail'),
    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/tags$',
        views.TagListView.as_view(),
        name='tag-list'),
    url(r'^(?P<owner_username>[^/]+)/datasets/(?P<dataset_slug>[^/]+)/(?P<submission_set_name>[^/]+)(?:/(?P<pk_list>(?:\d+,)+\d+))?$',
        views.DataSetSubmissionListView.as_view(),
        name='dataset-submission-list'),

    url(r'^(?P<owner_username>[^/]+)/datasets$',
        views.DataSetListView.as_view(),
        name='dataset-list'),

    url(r'^email-template/(?P<email_template_id>\d+)$',
        views.EmailTemplateDetailView.as_view(),
        name='email-template-detail'),

    # profiles and user info

    url(r'^(?P<owner_username>[^/]+)$',
        views.UserInstanceView.as_view(),
        name='user-detail'),

    url(r'^(?P<owner_username>[^/]+)/password$',
        lambda *a, **k: None,
        name='user-password'),

    url(r'^users/current$',
        views.CurrentUserInstanceView.as_view(),
        name='current-user-detail'),

    # authentication / association

    url(r'^users/login/error/$', views.remote_social_login_error, name='remote-social-login-error'),
    url(r'^users/login/(?P<backend>[^/]+)/$', views.remote_social_login, name='remote-social-login'),
    url(r'^users/logout/$', views.remote_logout, name='remote-logout'),

    # existing django-oauth2-provider url package:
    # url(r'^users/oauth2/', include('provider.oauth2.urls', namespace='oauth2')),
    # switch to django-oauth-toolkit url package:
    url(r'^users/oauth2/', include('oauth2_provider.urls', namespace='oauth2')),

    url(r'^users/', include('social_django.urls', namespace='social')),

    url(r'^forms/', include('rest_framework.urls', namespace='rest_framework')),

    # Utility routes

    url(r'^utils/send-away', views.redirector, name='redirector'),
    url(r'^utils/session-key', views.SessionKeyView.as_view(), name='session-key'),
    url(r'^utils/noop/?$', lambda request: HttpResponse(''), name='noop-route'),
]

#places_base_regex = r'^(?P<dataset__owner__username>[^/]+)/datasets/(?P<dataset__slug>[^/]+)/places/'
