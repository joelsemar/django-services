import time
from services.controller import BaseController
from services.decorators import unauthenticated


class AliveController(BaseController):

    @unauthenticated
    def read(self, request, response):
        """
        Alive health check endpoint
        Api Handler: GET /alive

        """
        response.set(time=time.time())
