import datetime
import urlparse
import urllib
import simplejson
import sys
import logging
from urllib2 import HTTPError
from django.db import  models
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from services import oauth, utils, oauth2  as li_oauth
from django.contrib.auth import authenticate, login, logout
from services.decorators import login_required
from services.apps.social.models import SocialNetwork, UserNetworkCredentials
from services.controller import BaseController
from services.view import BaseView
app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
PROFILE_MODEL = models.get_model(app_label, model_name)
NETWORK_HTTP_ERROR = "There was a problem reaching %s, please try again."

logger = logging.getLogger('default')

class SocialNetworkError(Exception):
    pass


class SocialFriendController(BaseController):
    allowed_methods = ('GET',)

    @login_required
    def read(self, request, response):
        """
        Get the list of friends from a social network for a user that has registered us with that network
        API Handler: GET /social/friends
        Params:
          @network [string] {twitter|facebook|linkedin}
        """
        network = request.GET.get('network')
        profile = request.user.get_profile()

        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.add_errors('Invalid network', status=404)

        try:
            credentials = UserNetworkCredentials.objects.get(profile=profile, network=network)
        except UserNetworkCredentials.DoesNotExist:
            return response.add_errors('Either %s does not exist or we do not have credentials for that user.' % network.name)

        if not hasattr(self, network.name):
            return response.add_errors("Not implemented")

        try:
            #Use the name of the network to call the helper function
            friend_social_ids = getattr(self, network.name)(profile, network, credentials)
        except HTTPError:
            return response.add_errors(NETWORK_HTTP_ERROR % network.name)

        social_friends_credentials = UserNetworkCredentials.objects.filter(network=network,
                                                                           uuid__in=friend_social_ids)

        results = [{'id':cred.profile.id,
                    'name_in_network':cred.name_in_network,
                    'username':cred.profile.user.username} for cred in social_friends_credentials]

        response.set(results=results)


    def facebook(self, profile, network, credentials):
        friends = utils.makeAPICall(network.base_url,
                                 'me/friends',
                                 queryData={'access_token': credentials.token},
                                 secure=True)

        return [x['id'] for x in friends['data']]

    def twitter(self, profile, network, credentials):
        oauthRequest = oauth.makeOauthRequestObject('https://%s/1/statuses/friends.json' % network.base_url,
                                                    network.get_credentials(),
                                                    token=oauth.OAuthToken.from_string(credentials.token))
        ret = oauth.fetchResponse(oauthRequest, network.base_url)
        friends = simplejson.loads(ret)
        return [x['id'] for x in friends]

    def linkedin(self, profile, network, credentials):
        oauthRequest = oauth.makeOauthRequestObject('https://%s/v1/people/~/connections' % network.base_url,
                                                    network.get_credentials(), method='GET',
                                                    token=oauth.OAuthToken.from_string(credentials.token))
        ret = oauth.fetchResponse(oauthRequest, network.base_url)
        friends = utils.fromXML(ret).person
        return [urlparse.parse_qs(y['site_standard_profile_request']['url'])['key'][0] for y in friends if y['site_standard_profile_request']]


class SocialMessageController(BaseController):

    @login_required
    def create(self, request, response, network):
        """
        Post a message a social network for a user that has registered us with that network to another user
        API Handler: POST /social/message/linkedin
        PARAMS
             @message [string] message to be posted
             @subject [string] subject message
             @recipient_id [string] identifier for the other user in the network
        """
        profile = request.user.get_profile()
        recipient_id = request.POST.get('recipient_id')
        message = request.POST.get('message')
        subject = request.POST.get('subject')

        if not all([subject, message, recipient_id]):
            return response.add_errors("subject, message, and recipient_id are all required")

        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.add_errors('Invalid network', status=404)

        if not hasattr(self, network.name):
            return response.add_errors("Not Implemented")

        try:
            credentials = UserNetworkCredentials.objects.get(network=network, profile=profile)
        except UserNetworkCredentials.DoesNotExist:
            return response.add_errors("This user has not registered us with the network specified")

        try:
            #Call the name of the network as a helper method to implement the different posts
            getattr(self, network.name)(request, response,  credentials, network, recipient_id, subject, message)
        except HTTPError:
            return response.add_error(errors=NETWORK_HTTP_ERROR % network.name)

    def linkedin(self, request, response, credentials, network, recipient_id, subject, message):
        consumer = li_oauth.Consumer(*network.get_credentials())
        client = li_oauth.Client(consumer, li_oauth.Token.from_string(credentials.token))
        payload = {
          'recipients': {
              'values': [
                 {'person':{ '_path': '/people/' + str(recipient_id) }}
              ]
          },
          "subject": subject,
          "body": message,
        }

        resp, content = client.request(network.get_message_url(), method='POST',  headers={'Content-Type': 'application/json'}, body=simplejson.dumps(payload))
        logger.debug(content)

class SocialFriendRequestController(SocialMessageController):

    @login_required
    def create(self, request, response, network):
        """
        Invite a friend on a social network
        API Handler: POST /social/invite/linkedin
        PARAMS
             @message [string] message to be posted
             @subject [string] subject message
             @recipient_id [string] identifier for the other user in the network
        """
        super(SocialFriendRequestController, self).create(request, response, network)

    def linkedin(self, request, response, credentials, network, recipient_id, subject, message):
        consumer = li_oauth.Consumer(*network.get_credentials())
        client = li_oauth.Client(consumer, li_oauth.Token.from_string(credentials.token))
        try:
            profile = PROFILE_MODEL.objects.get(id=recipient_id)
        except PROFILE_MODEL.DoesNotExist:
            return response.add_errors("Invalid recipient_id")

        payload = {
          "recipients": {
            "values": [{
              "person": { "_path": "/people/email=%s" % profile.email_address }
            }]
          },
          "subject": subject,
          "body": message,
          "item-content":{
             "invitation-request":{
                "connect-type":"friend",
                "authorization":{
                  "name":"NAME_SEARCH",
                  "value":"pXCC"
                }
             }
          }
       }

        resp, content = client.request(network.get_message_url(), method='POST',  headers={'Content-Type': 'application/json'}, body=simplejson.dumps(payload))
        logger.debug(content)

class SocialPostController(BaseController):

    @login_required
    def create(self, request, response):
        """
        Post a message a social network for a user that has registered us with that network
        API Handler: POST /social/post
        PARAMS
             @network [string] {twitter|facebook} Name of the network to post to
             @message [string] message to be posted
        """
        profile = request.user.get_profile()
        network = request.POST.get('network')

        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.add_errors('Invalid network', status=404)

        try:
            credentials = UserNetworkCredentials.objects.get(network=network, profile=profile)
        except UserNetworkCredentials.DoesNotExist:
            return response.add_errors("This user has not registered us with the network specified")

        if not hasattr(self, network.name):
            return response.add_errors("Not Implemented")

        try:
            #Call the name of the network as a helper method to implement the different posts
            getattr(self, network.name)(request,  response, credentials, network)
        except HTTPError:
            return response.add_errors(NETWORK_HTTP_ERROR % network.name)


    def twitter(self, request, credentials, network):
        message = self.get_twitter_post_data(request)
        oauthRequest = oauth.makeOauthRequestObject('https://%s/1/statuses/update.json' % network.base_url,
                                                    network.get_credentials(), token=oauth.OAuthToken.from_string(credentials.token),
                                                    method='POST', params={'status': message})
        oauth.fetchResponse(oauthRequest, network.base_url)

    def facebook(self, request, response,  credentials, network):
        postData = {'access_token': credentials.token}
        postData.update(self.get_facebook_post_data(request))
        utils.makeAPICall(network.base_url,
                          '%s/feed' % credentials.uuid,
                           postData=postData,
                           secure=True, deserializeAs='skip')

    def linkedin(self, request, response,  credentials, network):
        consumer = li_oauth.Consumer(*network.get_credentials())
        client = li_oauth.Client(consumer, token=li_oauth.Token.from_string(credentials.token))
        url = 'https://api.linkedin.com/v1/people/~/shares'
        message = request.POST.get('message')
        body = u"""<?xml version="1.0" encoding="UTF-8"?>
                   <share>
                     <comment>%s</comment>
                     <visibility>
                      <code>anyone</code>
                     </visibility>
                   </share>""" % message
        headers = {'Content-Type':'application/xml'}
        resp, content = client.request(url, method="POST", body=body.encode('utf-8'), headers=headers)
        logger.debug(content)


    def get_facebook_post_data(self, request):
        """
        Return a dictionary of parameters you'd like to augment the messge with
        Go here to see what the possible parameters are: you'd like to give to the posted message to facebook
        """
        message = request.POST.get('message')
        if message:
            return {'message': message}
        return {}

    def get_twitter_post_data(self, request):
        """
        Return the string to post to Twitter
        """
        message = request.POST.get('message')
        if message:
            return message
        return ''

class SocialRegisterController(BaseController):
    allowed_methods = ('POST', 'GET')

    model = SocialNetwork

    def read(self, request, response, network=None):
        """
        Handler to allow GETs to this url
        """
        return self.create(request, response, network)

    def create(self, request, response, network=None):
        """
        Attempts to gain permission to a user's data with a social network, if successful, will
        return a redirect to the network's servers, there the user will be prompted to login if
        necessary, and allow or deny us access. network = {facebook|twitter|linkedin|latitude|gowalla|foursquare}
        API handler: POST /social/register/{network}
        Params:
            None
        """
        if request.GET.get('redirect_url'):
            request.session['last_url'] = request.GET.get('redirect_url')

        elif request.META.get('HTTP_REFERER') and not 'social/test' in request.META.get('HTTP_REFERER'):
            request.session['last_url'] = request.META['HTTP_REFERER']

        if not response:
            response = BaseView()

        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.add_errors('Invalid network', status=404)

        #return the results of the helper function that has the name of the network referenced
        return getattr(self, network.name)(request, response, network)


    def facebook(self, request, response, network):
        """
        Helper function to handle facebook redirect
        """
        args = urllib.urlencode({'client_id' : network.getAppId(),
                                 'redirect_uri': network.callback_url(request),
                                 'scope': network.scope_string,
                                 'display': 'touch'})

        return HttpResponseRedirect(network.get_auth_url() + '?' + args)

    def twitter(self, request, response, network):
        """
        Helper function to handle twitter redirect
        """
        #the first step is a an unauthed 'request' token, the provider will not even deal with us until we have that
        # so we build a request, and sign it,
        consumer = li_oauth.Consumer(*network.get_credentials())
        client = li_oauth.Client(consumer)

        tries = 5
        while True:
            resp, content = client.request(network.request_token_url() + '&oauth_callback=%s' %
                    network.callback_url(request), "POST")
            tries -= 1
            if resp['status'] != 404:
                break
            if not tries:
                break

        if not tries:
            logger.error(content)
            return response.add_errors(NETWORK_HTTP_ERROR % network.name)

        try:
            token = li_oauth.Token.from_string(content)
        except (KeyError, ValueError):
            if 'whale' in content:
                return HttpResponse(content)
            return response.add_errors(content)


        # save the token to compare to the one provider will send back to us
        request.session['%s_unauthed_token' % network.name] = token.to_string()

        # we needed the token to form the authorization url for the user to go to
        # so we build the oauth request, sign it, and use that url
        oauth_request_url = "%s?oauth_token=%s" % (network.get_auth_url(), token.key)

        #finally, redirect the user to the url we've been working so hard on
        request.session['from_url'] = request.META.get('HTTP_REFERER', '/')

        return HttpResponseRedirect(oauth_request_url)

    def linkedin(self, request, response, network):
        """
        Helper function to handle the linkedin redirect
        """
        return self.twitter(request, response, network)

    def gowalla(self, request, response, network):
        """
        Helper function to redirect the user to gowalla for authorization
        """
        args = urllib.urlencode({'client_id': network.getAppId(),
                                 'display': 'touch',
                                 'scope': network.scope_string,
                                 'redirect_uri': network.callback_url(request)})

        return HttpResponseRedirect(network.get_auth_url() + '?' + args)

    def foursquare(self, request, response, network):
        """
        Helper function to handle foursquare redirect
        """
        args = urllib.urlencode({'client_id': network.getAppId(),
                                 'redirect_uri': network.callback_url(request),
                                 'response_type': 'code',
                                 'display': 'touch'})

        return HttpResponseRedirect(network.get_auth_url() + '?' + args)

    def latitude(self, request, response, network):
        """
        Helper function to handle latitude redirect
        """
        args = urllib.urlencode({'client_id': network.getAppId(),
                                 'redirect_uri': network.callback_url(request),
                                 'response_type': 'code',
                                 'display': 'touch',
                                 'scope': network.scope_string})

        return HttpResponseRedirect(network.get_auth_url() + '?' + args)


class SocialCallbackController(BaseController):
    allowed_methods = ('GET',)

    internal = True

    def read(self, request, response, network):
        """
        This is the entrypoint for social network's callbacks

        """

        try:
            network = SocialNetwork.objects.get(name=network)
        except SocialNetwork.DoesNotExist:
            return response.add_errors('Invalid network', status=404)

        redirect_to = request.session.get('last_url')
        if redirect_to:
            getattr(self, network.name)(request, response, network)
            return HttpResponseRedirect(redirect_to)
        return getattr(self, network.name)(request, response, network)

    def twitter(self, request, response, network):
        """
        Helper function to handle the callbacks for twitter
        """
        # The first step is to make sure there is an unauthed_token in the session, and that it matches the one
        # the provider gave us back
        consumer = li_oauth.Consumer(*network.get_credentials())
        client = li_oauth.Client(consumer)
        unauthed_token = request.session.get('%s_unauthed_token' % network.name, None)
        if not unauthed_token:
            logger.debug("Unauthed token not found in session")
            return response.add_errors(NETWORK_HTTP_ERROR % network.name)
        request.session['%s_unauthed_token' % network.name]
        requestToken = li_oauth.Token.from_string(unauthed_token)

        if requestToken.key != request.GET.get('oauth_token'):
            logger.debug("token key in session doesnt match li token")
            logger.debug("session unauthed key was %s, li token was %s" % (requestToken.key, request.GET.get('oauth_token')))
            return response.add_errors(NETWORK_HTTP_ERROR % network.name)
        verifier = request.GET.get('oauth_verifier')

        client.token = requestToken
        #Now we are building a request, so we can exchange this unauthed token for an access_token
        resp, access_token = client.request(network.access_token_url() + '?oauth_verifier=%s' % verifier)

        try:
           li_oauth.Token.from_string(access_token)
        except KeyError:
            logger.debug(resp, access_token)
            return response.add_errors(NETWORK_HTTP_ERROR % network.name)

        #store the token in the session and in the db, in the future we will look in the session first, and then
        #the db if that fails
        request.session['%s_access_token' % network.name] = access_token
        params = urlparse.parse_qs(access_token)
        if network.name == 'linkedin':
            profile_request_url = 'https://%s/v1/people/~:%s' % (network.base_url, settings.LINKEDIN_PROFILE_FIELDS)
            consumer = li_oauth.Consumer(*network.get_credentials())
            client = li_oauth.Client(consumer, token=li_oauth.Token.from_string(access_token))
            resp, content = client.request(profile_request_url, headers={'x-li-format': 'json'})
            ret = simplejson.loads(content)

            connections_request_url = 'https://%s/v1/people/~/connections:%s' % (network.base_url, settings.LINKEDIN_CONNECTION_FIELDS)
            resp, connections = client.request(connections_request_url, headers={'x-li-format': 'json'})
            ret['connections'] = simplejson.loads(connections)
            if ret.get('publicProfileUrl'):
                pass #forget this for now
                import urllib
                public_profile_url = urllib.quote(ret.get('publicProfileUrl'), safe='')
                profile_request_url = "https://%s/v1/people/url=%s:public" % (network.base_url, public_profile_url)
                oauthRequest = oauth.makeOauthRequestObject(profile_request_url, network.get_credentials(),
                                                            token=oauth.OAuthToken.from_string(access_token), method='GET')
                public_response = oauth.fetchResponse(oauthRequest, network.base_url, headers={'x-li-format': 'json'})
                public_profile = simplejson.loads(public_response)


            else:
                public_profile = {}

            #params['user_id'] = [urlparse.parse_qs(ret['siteStandardProfileRequest']['url'])['key'][0], '0']
            params['user_id'] = [ret['id'],]
            params['screen_name'] = ['%s %s' % (ret['firstName'], ret['lastName']), '0']
            params['profile'] = ret
            params['public_profile'] = public_profile

        network_dict = {}
        network_dict['access_token'] = access_token
        network_dict['uuid'] = params['user_id'][0]
        network_dict['name_in_network'] = params['screen_name'][0]
        network_dict['network'] = network
        network_dict['profile'] = params['profile']

        self.finish_callback(request, response, network_dict=network_dict)

    def facebook(self, request, response, network):
        """
        Helper function to handle the callbacks for facebook
        """

        verification_string = request.GET.get('code', '')
        if not verification_string:
            # probably the user didn't accept our advances
            return response.add_errors(NETWORK_HTTP_ERROR % network.name)

        token_request_args = {'client_id' :  network.getAppId(),
                              'client_secret': network.getSecret(),
                              'redirect_uri': network.callback_url(request),
                              'code' : verification_string}

        result = utils.makeAPICall(domain=network.base_url,
                                   apiHandler=network.access_token_path,
                                   queryData=token_request_args,
                                   secure=True, deserializeAs=None)

        ret = urlparse.parse_qs(result, keep_blank_values=False)
        access_token = ret['access_token'][0]
        ret = utils.makeAPICall(domain=network.base_url,
                                apiHandler='me?access_token=%s' % access_token,
                                secure=True)

        network_dict = {}
        network_dict['access_token'] = access_token
        network_dict['uuid'] = ret['id']
        network_dict['name_in_network'] = ret['name']
        network_dict['network'] = network

        self.finish_callback(request, response, network_dict=network_dict)


    def linkedin(self, request, response, network):
        """
        Helper function to handle the callbacks for linkedin
        """
        return self.twitter(request, response, network)

    def gowalla(self, request, response, network):
        """
        Helper function to handle the callbacks for gowalla
        """
        verification_string = request.GET.get('code', '')
        if not verification_string:
            # probably the user didn't accept our advances
            return response.add_errors(NETWORK_HTTP_ERROR % network.name)

        token_request_args = {'client_id' :  network.getAppId(),
                              'client_secret': network.getSecret(),
                              'redirect_uri': network.callback_url(request),
                              'grant_type' : 'authorization_code',
                              'code' : verification_string}

        result = utils.makeAPICall(domain=network.base_url,
                                   apiHandler=network.access_token_path,
                                   postData=token_request_args,
                                   secure=True)
        network_user  = utils.makeAPICall(domain=network.base_url,
                                apiHandler='users/me',
                                queryData={'access_token':result['access_token']},
                                headers={'Accept':'application/json'},
                                secure=True)
        network_dict = {}
        network_dict['access_token'] = result['access_token']
        network_dict['refresh_token'] = result['refresh_token']
        network_dict['timeout'] = datetime.datetime.utcnow() + datetime.timedelta(seconds=result['expires_in'])
        network_dict['uuid'] = result['username']
        network_dict['name_in_network'] = '%s %s' % (network_user['first_name'], network_user['last_name'])
        network_dict['network'] = network

        self.finish_callback(request, response, network_dict=network_dict)

    def foursquare(self, request, response, network):
        """
        Helper function to handle the callbacks for foursquare
        """
        verification_string = request.GET.get('code', '')
        if not verification_string:
            # probably the user didn't accept our advances
            return response.add_errors(NETWORK_HTTP_ERROR % network.name)

        token_request_args = {'client_id' :  network.getAppId(),
                              'client_secret': network.getSecret(),
                              'redirect_uri': network.callback_url(request),
                              'grant_type' : 'authorization_code',
                              'code' : verification_string}

        result = utils.makeAPICall(domain=network.base_url,
                                   apiHandler=network.access_token_path,
                                   queryData=token_request_args,
                                   secure=True)

        network_user  = utils.makeAPICall(domain=network.base_url,
                                apiHandler='v2/users/self',
                                queryData={'oauth_token':result['access_token']},
                                headers={'Accept':'application/json'},
                                secure=True)

        network_dict = {}
        network_dict['access_token'] = result['access_token']
        network_dict['uuid'] = network_user['id']
        network_dict['name_in_network'] = '%s %s' % (network_user['firstName'], network_user['lastName'])
        network_dict['network'] = network

        self.finish_callback(request, response, network_dict=network_dict)


    def latitude(self, request, response, network):
        """
        Helper Function to handle the callbacks for Google Latitude
        """
        verification_string = request.GET.get('code', '')
        error = request.GET.get('error', '')
        if error:
            return response.add_errors(error)
        if not verification_string:
            # probably the user didn't accept our advances
            return response.add_errors(NETWORK_HTTP_ERROR % network.name)

        token_request_args = {'client_id' :  network.getAppId(),
                              'client_secret': network.getSecret(),
                              'redirect_uri': network.callback_url(request),
                              'grant_type' : 'authorization_code',
                              'code' : verification_string}

        result = utils.makeAPICall(domain=network.base_url,
                                   apiHandler=network.access_token_path,
                                   postData=token_request_args,
                                   secure=True)

        network_user  = utils.makeAPICall(domain=network.base_url,
                                apiHandler='users/me',
                                queryData={'access_token':result['access_token']},
                                headers={'Accept':'application/json'},
                                secure=True)
        network_dict = {}
        network_dict['access_token'] = result['access_token']
        network_dict['refresh_token'] = result['refresh_token']
        network_dict['timeout'] = datetime.datetime.utcnow() + datetime.timedelta(seconds=result['expires_in'])
        network_dict['uuid'] = result['username']
        network_dict['name_in_network'] = '%s %s' % (network_user['first_name'], network_user['last_name'])
        network_dict['network'] = network

        self.finish_callback(request, response, network_dict=network_dict)

    def finish_callback(self, request, response, network_dict):
        logout(request)

        try:
            profile = UserNetworkCredentials.objects.get(uuid=network_dict['uuid']).profile
            profile.update_from_profile(network_dict['profile'], initial=False)
        except UserNetworkCredentials.DoesNotExist:
            profile = PROFILE_MODEL.create_from_profile(network_dict, network_dict['profile'], ip=request.META['REMOTE_ADDR'])

        del network_dict['profile']
        profile.user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, profile.user)

        UserNetworkCredentials.objects.filter(profile=profile, network=network_dict['network']).delete()
        credentials = UserNetworkCredentials.objects.create(profile=profile, **network_dict)
        join_linkedin_group(credentials, settings.LI_GROUP_ID)




def join_linkedin_group(credentials, groupid):
    xml_body = """<group-membership>
      <membership-state>
        <code>member</code>
      </membership-state>
    </group-membership>"""

    try:
        network = SocialNetwork.objects.get(name='linkedin')
    except SocialNetwork.DoesNotExist:
        return False

    consumer = li_oauth.Consumer(*network.get_credentials())
    client = li_oauth.Client(consumer, token=li_oauth.Token.from_string(credentials.token))
    group_join_url = 'https://%s/v1/people/~/group-memberships/%s' % (network.base_url, groupid)
    return client.request(group_join_url, method='PUT', body=xml_body)


#ALL DEFINITION EOF
module_name = globals().get('__name__')
handlers = sys.modules[module_name]
handlers._all_ = []
for handler_name in dir():
    m = getattr(handlers, handler_name)
    if type(m) == type(BaseController):
        handlers._all_.append(handler_name)
