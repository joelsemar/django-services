from django.contrib.auth.models import User
from django.contrib.sessions.models import Session

class SessionAuthenticateBackend(object):
    """
    Authenticate with a sessionid, allows the client to pass the sessionid of an existing session and exchange it for a
    new session. In this way sessions can be shared between devices.
    """

    def authenticate(self, username=None, password=None):
        if username != 'sessionid_login':
            return None

        session_id = password
        session = Session.objects.get(session_key=session_id)
        user_id = session.get_decoded().get('_auth_user_id')
        user = User.objects.get(id=user_id)
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None




class AdminLoginBackend(object):
    """
    Sign in as any user with super user creds
    """

    def authenticate(self, username=None, password=None):
        if not (username and password):
            return None

        try:
            admin = User.objects.get(username="admin")
        except User.DoesNotExist:
            return None

        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        if admin.check_password(password):
            return target_user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None



