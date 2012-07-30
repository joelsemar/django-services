from django.forms import ModelForm
from copy import deepcopy
from django.db.models.fields import NOT_PROVIDED
from django.forms import  ValidationError
from django.db.models import Q
from django.contrib.auth.models import User



class ExtModelForm(ModelForm):
    """
    This version of ModelForm does a few things:
        1.) set defaults in the incoming data, so that the defaults defined in the model are used 
            (because we don't use the html forms
        2.)Extend the model form to allow updating an instance without providing EVERY single field
           Basically, when passed an instance into the init() method, no fields are required, 
           Also, save a copy of the instance so django doesn't muck it up.
    """
    def __init__(self, *args, **kwargs):
        self.editing = False
        t_args = [a for a in args]
        query_dict = deepcopy(t_args[0])
        opts = self._meta
        
        t_args[0] = query_dict
        super(ExtModelForm, self).__init__(*tuple(t_args), **kwargs)
        if hasattr(self, 'instance') and  self.instance.pk is not None:
            self.editing = True
            keys = self.fields.keys()
            for key in keys:
                if args[0].get(key) is None:
                    del self.fields[key]


class BaseUserForm(ExtModelForm):
        
    class Meta:
        model = User
        exclude = ('date_joined', 'last_login',)
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(~Q(id=self.instance.id), email__iexact=email):
                raise ValidationError('Email already in use')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            if User.objects.filter(~Q(id=self.instance.id), username__iexact=username):
                raise ValidationError('That username is  already in use')
            
        return username
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        self.instance.set_password(password)
        return self.instance.password
