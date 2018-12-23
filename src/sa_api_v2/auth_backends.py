from django.contrib.auth.backends import ModelBackend
from .cache import UserCache
from social_core.backends.facebook import FacebookOAuth2


class CachedModelBackend (ModelBackend):
    def get_user(self, user_id):
        user = UserCache.get_instance(user_id=user_id)
        if user is None:
            user = super(CachedModelBackend, self).get_user(user_id)
            UserCache.set_instance(user, user_id=user_id)
        return user

# This custom backend prevents the dynamic redirect_state query param from
# being sent with FB OAuth requests. redirect_state interferes with upgraded
# FB security requirements.
# https://stackoverflow.com/questions/45307723/valid-oauth-redirect-uris-for-facebook-django-social-auth
# https://developers.facebook.com/docs/facebook-login/security/#surfacearea
class NoRedirectStateFacebookOAuth2(FacebookOAuth2):
    REDIRECT_STATE = False
