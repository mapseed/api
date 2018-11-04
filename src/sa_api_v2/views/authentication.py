from rest_framework import (authentication)
###############################################################################
#
# Authentication (that doesn't require an extra model)
# --------------
#


class ShareaboutsSessionAuth(authentication.BaseAuthentication):
    """
    A copy of Django REST Framework's session auth class without the CSRF
    check. We don't do cookie-based CSRF here because the context of receiving
    a submission from a form doesn't usually apply for an API. Also, with CORS
    if the request is coming from a different domain it won't be allowed.
    """

    def authenticate(self, request):
        """
        Returns a `User` if the request session currently has a logged in user.
        Otherwise returns `None`.
        """

        # Get the underlying HttpRequest object
        http_request = request._request
        user = getattr(http_request, 'user', None)

        # Unauthenticated, CSRF validation not required
        if not user or not user.is_active:
            return None

        return (user, None)
