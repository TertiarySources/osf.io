from rest_framework import generics
from rest_framework import permissions as drf_permissions

from modularodm import Q as MQ
from django.db.models import Q

from framework.auth.oauth_scopes import CoreScopes

from website.models import Node, Subject, PreprintService, PreprintProvider

from api.base import permissions as base_permissions
from api.base.filters import DjangoFilterMixin, ODMFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.pagination import MaxSizePagination
from api.base.utils import get_object_or_error, get_user_auth
from api.licenses.views import LicenseList
from api.taxonomies.serializers import TaxonomySerializer
from api.preprint_providers.serializers import PreprintProviderSerializer
from api.preprints.serializers import PreprintSerializer

from api.preprints.permissions import PreprintPublishedOrAdmin

class PreprintProviderList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """
    Paginated list of verified PreprintProviders available. *Read-only*

    Assume undocumented fields are unstable.

    ##PreprintProvider Attributes

    OSF Preprint Providers have the "preprint_providers" `type`.

        name           type               description
        =========================================================================
        name           string             name of the preprint provider
        logo_path      string             a path to the preprint provider's static logo
        banner_path    string             a path to the preprint provider's banner
        description    string             description of the preprint provider

    ##Relationships

    ###Preprints
    Link to the list of preprints from this given preprint provider.

    ##Links

        self: the canonical api endpoint of this preprint provider
        preprints: link to the provider's preprints
        external_url: link to the preprint provider's external URL (e.g. https://socarxiv.org)

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    model_class = PreprintProvider

    pagination_class = MaxSizePagination
    serializer_class = PreprintProviderSerializer
    view_category = 'preprint_providers'
    view_name = 'preprint_providers-list'

    ordering = ('name', )

    # implement ODMFilterMixin
    def get_default_odm_query(self):
        return None

    # overrides ListAPIView
    def get_queryset(self):
        return PreprintProvider.find(self.get_query_from_request())


class PreprintProviderDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """ Details about a given preprint provider. *Read-only*

    Assume undocumented fields are unstable.

    ##PreprintProvider Attributes

    OSF Preprint Providers have the "preprint_providers" `type`.

        name           type               description
        =========================================================================
        name           string             name of the preprint provider
        logo_path      string             a path to the preprint provider's static logo
        banner_path    string             a path to the preprint provider's banner
        description    string             description of the preprint provider

    ##Relationships

    ###Preprints
    Link to the list of preprints from this given preprint provider.

    ##Links

        self: the canonical api endpoint of this preprint provider
        preprints: link to the provider's preprints
        external_url: link to the preprint provider's external URL (e.g. https://socarxiv.org)

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    model_class = PreprintProvider

    serializer_class = PreprintProviderSerializer
    view_category = 'preprint_providers'
    view_name = 'preprint_provider-detail'

    def get_object(self):
        return get_object_or_error(PreprintProvider, self.kwargs['provider_id'], display_name='PreprintProvider')


class PreprintProviderPreprintList(JSONAPIBaseView, generics.ListAPIView, DjangoFilterMixin):
    """Preprints from a given preprint_provider. *Read Only*

    To update preprints with a given preprint_provider, see the `<node_id>/relationships/preprint_provider` endpoint

    ##Preprint Attributes

    OSF Preprint entities have the "preprints" `type`.

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the preprint was created
        date_modified                   iso8601 timestamp                   timestamp that the preprint was last modified
        date_published                  iso8601 timestamp                   timestamp when the preprint was published
        is_published                    boolean                             whether or not this preprint is published
        is_preprint_orphan              boolean                             whether or not this preprint is orphaned
        subjects                        array of tuples of dictionaries     ids of Subject in the PLOS taxonomy. Dictionary, containing the subject text and subject ID
        doi                             string                              bare DOI for the manuscript, as entered by the user

    ##Relationships

    ###Node
    The node that this preprint was created for

    ###Primary File
    The file that is designated as the preprint's primary file, or the manuscript of the preprint.

    ###Provider
    Link to preprint_provider detail for this preprint

    ##Links
    - `self` -- Preprint detail page for the current preprint
    - `html` -- Project on the OSF corresponding to the current preprint
    - `doi` -- URL representation of the DOI entered by the user for the preprint manuscript

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PreprintPublishedOrAdmin,
    )

    ordering = ('-date_created')

    serializer_class = PreprintSerializer
    model_class = Node

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'preprint_providers'
    view_name = 'preprints-list'

    def postprocess_query_param(self, key, field_name, operation):
        if field_name == 'provider':
            operation['source_field_name'] = 'provider___id'

        if field_name == 'id':
            operation['source_field_name'] = 'guids___id'

    # overrides DjangoFilterMixin
    def get_default_django_query(self):
        auth = get_user_auth(self.request)
        auth_user = getattr(auth, 'user', None)
        provider = get_object_or_error(PreprintProvider, self.kwargs['provider_id'], display_name='PreprintProvider')

        # Permissions on the list objects are handled by the query
        default_query = Q(node__isnull=False, node__is_deleted=False, provider___id=provider._id)
        no_user_query = Q(is_published=True, node__is_public=True)

        if auth_user:
            contrib_user_query = Q(is_published=True, node__contributor__user_id=auth_user.id, node__contributor__read=True)
            admin_user_query = Q(node__contributor__user_id=auth_user.id, node__contributor__admin=True)
            return (default_query & (no_user_query | contrib_user_query | admin_user_query))
        return (default_query & no_user_query)

    # overrides ListAPIView
    def get_queryset(self):
        return PreprintService.objects.filter(self.get_query_from_request())


class PreprintProviderSubjectList(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'preprint_providers'
    view_name = 'taxonomy-list'

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = TaxonomySerializer

    def is_valid_subject(self, allows_children, allowed_parents, sub):
        if sub._id in allowed_parents:
            return True
        for parent in sub.parents.all():
            if parent._id in allows_children:
                return True
            for grandpa in parent.parents.all():
                if grandpa._id in allows_children:
                    return True
        return False

    def get_queryset(self):
        parent = self.request.query_params.get('filter[parents]', None)
        provider = get_object_or_error(PreprintProvider, self.kwargs['provider_id'], display_name='PreprintProvider')
        if parent:
            if parent == 'null':
                return provider.top_level_subjects
            #  Calculate this here to only have to do it once.
            allowed_parents = [id_ for sublist in provider.subjects_acceptable for id_ in sublist[0]]
            allows_children = [subs[0][-1] for subs in provider.subjects_acceptable if subs[1]]
            return [sub for sub in Subject.find(MQ('parents___id', 'eq', parent)) if provider.subjects_acceptable == [] or self.is_valid_subject(allows_children=allows_children, allowed_parents=allowed_parents, sub=sub)]
        return provider.all_subjects


class PreprintProviderLicenseList(LicenseList):
    ordering = ()
    view_category = 'preprint_providers'

    def get_queryset(self):
        provider = get_object_or_error(PreprintProvider, self.kwargs['provider_id'], display_name='PreprintProvider')
        return provider.licenses_acceptable.get_queryset() if provider.licenses_acceptable.count() else super(PreprintProviderLicenseList, self).get_queryset()
