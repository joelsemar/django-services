from services.controller import BaseController
from services.decorators import login_required, render_with
from services.view import ModelView

from django.db import transaction
from django.utils.importlib import import_module
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.sessions.models import Session


class GenericUserController(BaseController):

    def __init__(self):
        for app in settings.INSTALLED_APPS:
            try:
                forms = import_module('%s.forms' % app)
            except:
                continue
            if hasattr(forms, 'UserForm'):
                self.user_form = forms.UserForm
            if hasattr(forms, 'UserProfileForm'):
                self.profile_form = forms.UserProfileForm

    @login_required
    @render_with(ModelView)
    def read(self, request, response=None):
        """
        Return the details of the User's profile and preferences
        API Handler: GET /user
        """

        profile = request.user.get_profile()
        response.set(instance=profile)

    def create(self, request, response):
        """
        Create a new user
        API Handler: POST /user
        Params:
            {{ params }}
        """
        profile_form = None
        profile = None
        if self.profile_form:
            profile_form = self.profile_form(request.POST, request.FILES)

        user_form = self.user_form(request.POST)
        if user_form.is_valid():
            user = user_form.save()

        else:
            response.add_errors(self.format_errors(user_form))
            return

        if profile_form and profile_form.is_valid():
            profile = profile_form.save(commit=False)

        else:
            response.add_errors(self.format_errors(profile_form))

        if response._errors:
            transaction.rollback()
            return

        if profile:
            profile.user = user
            profile.save()

        user = authenticate(username=user_form.cleaned_data['username'], password=request.POST.get('password'))

        if user:
            login(request, user)
            return response.set(user={'username': user.username, 'id': profile.id})

        transaction.rollback()
        return response.add_errors('User creation failed', status=500)

    @render_with(ModelView)
    @transaction.atomic
    def update(self, request, response):
        """
        Update the logged in user
        API handler: PUT /user
        """
        profile = request.user.get_profile()
        profile_form = self.profile_form(request.PUT, request.FILES, instance=profile)
        user_form = self.user_form(request.PUT, instance=request.user)

        if profile_form.is_valid():
            user_profile = profile_form.save()
        else:
            response.add_errors(self.format_errors(profile_form))

        if user_form.is_valid():
            user_form.save()
        else:
            response.add_errors(self.format_errors(user_form))

        if response._errors:
            transaction.rollback()
            return

        response.set(instance=user_profile)


class LoginController(BaseController):
    allowed_methods = ('POST', 'DELETE', 'GET', 'PUT')

    def create(self, request, response):
        """
        Allows the user to login
        API Handler: POST /login

        POST Params:
           @username [string] The users's unique identifier, (may be an email address in some cases)
           @password [password] The user's password

        Returns:
            @username [string] users username
            @id [id] id of the user
            @email [email] user's email address
            @errors [list] insufficient_credentials, invalid_credentials
        """
        # all calls to this handler via '/logout should..
        if request.path.startswith('/logout'):
            return self.read(request, response)

        username = request.POST.get('username', '')
        email = request.POST.get('email', '').lower()
        password = request.POST.get('password')

        if email and not username:
            try:
                user = User.objects.get(email=email)
                username = user.username
            except User.DoesNotExist:
                return response.add_errors('insufficient_credentials', status=401)

        if not all([username, password]):
            return response.add_errors('insufficient_credentials', status=401)

        user = authenticate(username=username, password=password)
        if user:
            single_session = getattr(settings, "SINGLE_SESSION", False)
            if single_session:
                [s.delete() for s in Session.objects.all() if s.get_decoded().get('_auth_user_id') == user.id]
            login(request, user)
            response.set(user={'username': username, 'id': user.id, 'email': user.email})

        else:
            return response.add_errors(errors='invalid_credentials', status=401)

    def read(self, request, response):
        """
        Logout
        API Handler: GET /logout
        """
        logout(request)

    def update(self, request, response):
        """
        Logout
        API Handler: PUT /logout
        PARAMS:
           device_token: (optional)
        """
        return self.read(request, response)

    def delete(self, request, response):
        """
        Logout
        API Handler: DELETE /logout
        """
        return self.read(request, response)
