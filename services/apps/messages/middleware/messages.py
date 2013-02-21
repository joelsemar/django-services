from django.core.cache import cache
from services.apps import messages

class MessagesMiddleware(object):

    def process_response(self, request, response):
        if not request.user.is_authenticated():
            return response
        profile = request.user.get_profile()
        pending_messages = messages.get_pending_messages(profile)
        if messages:
            response.add_messages(pending_messages)
            messages.clear_messages(profile)
        return response




