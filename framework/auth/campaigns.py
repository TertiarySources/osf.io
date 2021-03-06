import furl
import threading

from django.utils import timezone

from website import mails
from website.models import PreprintProvider
from website.settings import DOMAIN, CAMPAIGN_REFRESH_THRESHOLD
from website.util.time import throttle_period_expired


mutex = threading.Lock()
CAMPAIGNS = None
CAMPAIGNS_LAST_REFRESHED = timezone.now()


def get_campaigns():

    global CAMPAIGNS
    global CAMPAIGNS_LAST_REFRESHED

    if not CAMPAIGNS or (not mutex.locked() and throttle_period_expired(CAMPAIGNS_LAST_REFRESHED, CAMPAIGN_REFRESH_THRESHOLD)):
        with mutex:
            # Native campaigns: PREREG and ERPC
            newest_campaigns = {
                'prereg': {
                    'system_tag': 'prereg_challenge_campaign',
                    'redirect_url': furl.furl(DOMAIN).add(path='prereg/').url,
                    'confirmation_email_template': mails.CONFIRM_EMAIL_PREREG,
                    'login_type': 'native',
                },
                'erpc': {
                    'system_tag': 'erp_challenge_campaign',
                    'redirect_url': furl.furl(DOMAIN).add(path='erpc/').url,
                    'confirmation_email_template': mails.CONFIRM_EMAIL_ERPC,
                    'login_type': 'native',
                },
            }

            # Institution Login
            newest_campaigns.update({
                'institution': {
                    'system_tag': 'institution_campaign',
                    'redirect_url': '',
                    'login_type': 'institution',
                },
            })

            # Proxy campaigns: Preprints, both OSF and branded ones
            preprint_providers = PreprintProvider.objects.all()
            for provider in preprint_providers:
                if provider._id == 'osf':
                    template = 'osf'
                    name = 'OSF'
                    url_path = 'preprints/'
                else:
                    template = 'branded'
                    name = provider.name
                    url_path = 'preprints/{}'.format(provider._id)
                campaign = '{}-preprints'.format(provider._id)
                system_tag = '{}_preprints'.format(provider._id)
                newest_campaigns.update({
                    campaign: {
                        'system_tag': system_tag,
                        'redirect_url': furl.furl(DOMAIN).add(path=url_path).url,
                        'confirmation_email_template': mails.CONFIRM_EMAIL_PREPRINTS(template, name),
                        'login_type': 'proxy',
                        'provider': name,
                    }
                })

            CAMPAIGNS = newest_campaigns
            CAMPAIGNS_LAST_REFRESHED = timezone.now()

    return CAMPAIGNS


def system_tag_for_campaign(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('system_tag')
    return None


def email_template_for_campaign(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('confirmation_email_template')
    return None


def campaign_for_user(user):
    campaigns = get_campaigns()
    for campaign, config in campaigns.items():
        if config.get('system_tag') in user.system_tags:
            return campaign
    return None


def is_institution_login(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('login_type') == 'institution'
    return None


def is_native_login(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('login_type') == 'native'
    return None


def is_proxy_login(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('login_type') == 'proxy'
    return None


def get_service_provider(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('provider')
    return None


def campaign_url_for(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('redirect_url')
    return None
