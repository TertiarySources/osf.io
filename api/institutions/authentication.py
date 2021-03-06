import json

import jwe
import jwt

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

from api.base import settings
from website.models import Institution
from website.mails import send_mail, WELCOME_OSF4I
from framework.auth import get_or_create_user


class InstitutionAuthentication(BaseAuthentication):
    media_type = 'text/plain'

    def authenticate(self, request):
        try:
            payload = jwt.decode(
                jwe.decrypt(request.body, settings.JWE_SECRET),
                settings.JWT_SECRET,
                options={'verify_exp': False},
                algorithm='HS256'
            )
        except (jwt.InvalidTokenError, TypeError):
            raise AuthenticationFailed

        # The JWT `data` payload is expected in the following structure.
        #
        # {"provider": {
        #     "idp": "https://login.circle.edu/idp/shibboleth",
        #     "id": "CIR",
        #     "user": {
        #         "middleNames": "",
        #         "familyName": "",
        #         "givenName": "",
        #         "fullname": "Circle User",
        #         "suffix": "",
        #         "username": "user@circle.edu"
        #     }
        # }}
        data = json.loads(payload['data'])
        provider = data['provider']

        institution = Institution.load(provider['id'])
        if not institution:
            raise AuthenticationFailed('Invalid institution id specified "{}"'.format(provider['id']))

        username = provider['user']['username']
        fullname = provider['user']['fullname']

        user, created = get_or_create_user(fullname, username, reset_password=False)

        if created:
            user.given_name = provider['user'].get('givenName') or user.given_name
            user.middle_names = provider['user'].get('middleNames') or user.middle_names
            user.family_name = provider['user'].get('familyName') or user.family_name
            user.suffix = provider['user'].get('suffix') or user.suffix
            user.update_date_last_login()
            user.save()

            # User must be saved in order to have a valid _id
            user.register(username)
            send_mail(
                to_addr=user.username,
                mail=WELCOME_OSF4I,
                mimetype='html',
                user=user
            )

        if not user.is_affiliated_with_institution(institution):
            user.affiliated_institutions.add(institution)
            user.save()

        return user, None
