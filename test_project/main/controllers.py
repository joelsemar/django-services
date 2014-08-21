
from services.controllers import BaseController
from services.views import ModelView
from main.models import *




class CRUDController(BaseController):

    def create(self, request, response):
        """
        POST to this controller
        API Handler: POST /crud
        """
        response.set(method=request.method)
        response.attribute_method=request.method

    def read(self, request, response):
        """
        GET this controller
        API Handler: GET /crud
        """
        response.set(method=request.method)
        response.attribute_method=request.method

    def update(self, request, response):
        """
        PUT to this controller
        API Handler: PUT /crud
        """
        response.set(method=request.method)
        response.attribute_method=request.method

    def delete(self, request, response):
        """
        DELETE to this controller
        API Handler: DELETE /crud
        """
        response.set(method=request.method)
        response.attribute_method=request.method


class BlogPostController(BaseController):

    def create(self, request, response):
        """
        Create a blog post
        API Handler: POST /blog

        Params:
           @title [string] title for the blog post 
        """
        title = request.POST.get('title', 'why no title?')
        response.set(**BlogPost.objects.create(title=title).dict)


    def read(self, request, response, blog_id):
        """
        Fetch a blog post by id
        API Handler: POST /blog/:id
        """
        try:
            post = BlogPost.objects.get(id=blog_id)
        except BlogPost.DoesNotExist:
            return response.not_found()

        [][1]
        response.id = post.id
        response.title = post.title

