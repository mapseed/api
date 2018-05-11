from django.contrib.auth.backends import ModelBackend
from .cache import UserCache
from social.backends.facebook import FacebookOAuth2

class CachedModelBackend (ModelBackend):
    def get_user(self, user_id):
        user = UserCache.get_instance(user_id=user_id)
        if user is None:
            user = super(CachedModelBackend, self).get_user(user_id)
            UserCache.set_instance(user, user_id=user_id)
        return user

class NoRedirectStateFacebookOAuth2(FacebookOAuth2):
    REDIRECT_STATE = False
