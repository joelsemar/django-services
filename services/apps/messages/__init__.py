from django.core.cache import cache
def build_cache_key(user):
    return "mesage_key_%s" % user.id

def set_message(user, message, message_type='default'):
    cache_key = build_cache_key(user)
    pending_messages = cache.get(cache_key, [])
    pending_messages.append({'message_type': message_type, "value":message})
    cache.set(build_cache_key(user), pending_messages)

def get_pending_messages(user):
    cache_key = build_cache_key(user)
    return cache.get(cache_key, [])

def clear_messages(user):
    cache_key = build_cache_key(user)
    cache.delete(cache_key)
