from django.db.models import Q
from rest_framework import serializers
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Account
import requests
from rest_framework.utils import json
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from .utils import get_client_ip, create_token
from authServer.AESEncryption import AESCipher
from authServer.settings import TOKEN_KEY, CLIENT_SECRETS

class SocialSerializer(serializers.Serializer):
    """
    Serializer which accepts an OAuth2 access token.
    """
    access_token = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def oauth2_signin(request):
    serializer = SocialSerializer(data=request.data)

    if serializer.is_valid(raise_exception=True):
        code = serializer.data['access_token']
        try:
            # Upgrade the authorization code into a credentials object
            oauth_flow = flow_from_clientsecrets(CLIENT_SECRETS, scope='')
            oauth_flow.redirect_uri = 'postmessage'
            credentials = oauth_flow.step2_exchange(code)
            PARAMS = { 'access_token': credentials.access_token }
            r = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", params=PARAMS)
            data = json.loads(r.text)
            try:
                user = Account.objects.filter(Q(username=data['given_name'])|Q(email=data['email'])).distinct()
                if user.exists() and user.count() == 1:
                    user_obj = user.first()
                else:
                    user_obj = Account.objects.create_user(
                        data['email'],
                        data['given_name'],
                        data['given_name'],
                        data['family_name']
                    )
                ip = get_client_ip(request)
                token = create_token(user_obj)
                response = {
                    'auth_token': token,
                    'key': AESCipher(TOKEN_KEY).encrypt(token),
                    'ip' : ip
                }
                return Response(response, status=status.HTTP_200_OK)
            except:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        except FlowExchangeError as e:
            return Response(
                {'errors': {
                    'token': 'Invalid token',
                    'detail': str(e),
                }},
                status=status.HTTP_400_BAD_REQUEST,
            )
