from .. import apikey
from rest_framework import (permissions)
from ..params import (
    INCLUDE_INVISIBLE_PARAM,
    INCLUDE_PRIVATE_FIELDS_PARAM,
    INCLUDE_PRIVATE_PLACES_PARAM
)
from .. import models
###############################################################################
#
# Permissions
# -----------
#


def is_owner(user, request):
    username = getattr(user, 'username', None)
    allowed_username = getattr(request, 'allowed_username', None)
    # XXX Watch out when mocking users in tests: bool(mock.Mock()) is True
    return (username and allowed_username == username)


def is_apikey_auth(auth):
    return isinstance(auth, apikey.models.ApiKey)


def is_origin_auth(auth):
    return isinstance(auth, basestring) and auth.startswith('origin')


def is_really_logged_in(user, request):
    auth = getattr(request, 'auth', None)
    return (user.is_authenticated() and
            not is_apikey_auth(auth) and
            not is_origin_auth(auth))


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Allows only superusers or the user named by
        `request.allowed_username` to write.

        (If the view has no such attribute, assumes not allowed)
        """
        if request.method == 'OPTIONS':
            return True

        if (request.method in permissions.SAFE_METHODS or
            is_owner(request.user, request) or request.user.is_superuser
            or (hasattr(request, 'client') and
                hasattr(request.client, 'owner') and
                is_owner(request.client.owner, request))):
            return True
        return False


class IsAdminOwnerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Allows only superusers, owners (ie users named by
        `request.allowed_username`), or logged in users, to write.
        """
        if IsOwnerOrReadOnly().has_permission(request, view):
            return True
        if is_really_logged_in(request.user, request):
            return True
        return False


class IsLoggedInOwnerOrPublicDataOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Disallows any request for public data from a user authenticated
        by API key.

        For protecting views related to API keys that should require
        'real' authentication, to avoid users abusing one API key to
        obtain others.
        """
        if request.method == 'OPTIONS':
            return True

        private_data_flags = [
            INCLUDE_PRIVATE_PLACES_PARAM,
            INCLUDE_PRIVATE_FIELDS_PARAM,
            INCLUDE_INVISIBLE_PARAM
        ]
        if not any([flag in request.GET for flag in private_data_flags]):
            return True

        if not is_really_logged_in(request.user, request):
            return False

        if is_owner(request.user, request) or request.user.is_superuser:
            return True

        return False


class IsLoggedInOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Disallows any request for public data from a user authenticated
        by API key.

        For protecting views related to API keys that should require
        'real' authentication, to avoid users abusing one API key to
        obtain others.
        """
        if request.method == 'OPTIONS':
            return True

        if not is_really_logged_in(request.user, request):
            return False

        if is_owner(request.user, request) or request.user.is_superuser:
            return True

        return False


class IsLoggedInAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == 'OPTIONS':
            return True

        if not is_really_logged_in(request.user, request):
            return False

        if request.user.is_superuser:
            return True

        return False


class IsAllowedByDataPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == 'OPTIONS':
            return True

        # Let the owner do whatever they want
        if is_owner(request.user, request):
            return True

        # DataSets are protected by other means
        if hasattr(view, 'model') and issubclass(view.model, models.DataSet):
            return True

        if hasattr(view, 'get_method_actions'):
            actions = view.get_method_actions()
        else:
            actions = {
                'GET': 'retrieve',
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'update',
                'DELETE': 'destroy'
            }

        # We only protect the actions we know about
        if request.method.upper() not in actions:
            return True

        do_action = actions[request.method.upper()]

        # Submission instance or list, or attachments thereon
        # TODO: rename this to 'resource_name_kwarg'
        if hasattr(view, 'submission_set_name_kwarg') and view.submission_set_name_kwarg in view.kwargs:
            data_type = view.kwargs[view.submission_set_name_kwarg]

        elif hasattr(view, 'resource_id'):
            data_type = view.resource_id
        # Place instance or list, or attachents thereon
        else:
            data_type = 'places'

        # Check whether we have to get permission for protected data
        protected = (
            INCLUDE_INVISIBLE_PARAM in request.GET or
            INCLUDE_PRIVATE_FIELDS_PARAM in request.GET or
            INCLUDE_PRIVATE_PLACES_PARAM in request.GET
        )

        user = getattr(request, 'user', None)
        client = getattr(request, 'client', None)
        dataset = getattr(request, 'get_dataset', lambda: None)()
        place_id = None
        if 'id' in request.data:
            place_id = request.data['id']

        return models.check_data_permission(user, client, place_id, do_action, dataset, data_type, protected)

