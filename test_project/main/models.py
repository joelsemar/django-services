
from django.db import models
from services.models import BaseModel
# Create your models here.

class BlogPost(BaseModel):
    title = models.CharField(max_length=128)
