from django.conf.urls import include, url
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth.views import logout_then_login

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import resolve_url

admin.autodiscover()

urlpatterns = [
    # Examples:
    # url(r'^$', 'project.views.home', name='home'),
    # url(r'^project/', include('project.foo.urls')),

    # NOTE: Redirect all manager urls until the manager is fixed.
    url(r'^$', lambda x: HttpResponseRedirect(resolve_url(settings.ROOT_REDIRECT_TO))),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/', include('loginas.urls')),

    # For now, use basic auth.
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^accounts/logout/$', logout_then_login,
        name='manager_logout'),

    # For now, the API and the management console are hosted together.
    url(r'^api/v2/', include('sa_api_v2.urls')),
    url(r'^api/v1/', lambda x: HttpResponse(status=410)),

]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Debug toolbar explicit setup
from django.conf import settings
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
