
from services.apps.credential_storage.models import StoredCredential
cached_creds = {}



def get(name):
    credential = cached_creds.get(name)
    if not credential:
        try:
            credential = StoredCredential.objects.get(name=name)
        except StoredCredential.DoesNotExist:
            return 'NO CREDENTIAL STORED'

    value = credential.get_value()
    cached_creds[name] = value
    return cached_creds[name]



