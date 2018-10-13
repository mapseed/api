from rest_framework.negotiation import DefaultContentNegotiation


class _JSONPCallbackNegotiation (DefaultContentNegotiation):
    """
    If the request has a 'callback' querystring parameter then we shouldn't
    have to specify format=jsonp; it should be implied.
    """

    def select_renderer(self, request, renderers, format_suffix=None):
        if 'callback' in request.query_params:
            format_suffix = 'jsonp'
        return super(_JSONPCallbackNegotiation, self).select_renderer(request, renderers, format_suffix)


class _XDomainRequestCompatNegotiation (DefaultContentNegotiation):
    """
    In IE 8 and 9 CORS is supported with the XDomainRequest object. However,
    POST requests will only be sent with a content-type header of text/plain.
    In this case, we just want to "correct" this to be JSON.
    """

    def select_parser(self, request, parsers):
        # For cross-origin requests (with an Origin header), if we get a plain
        # text content type (or no content type at all), then assume we are
        # dealing with an XDomainRequest and the content should be JSON.
        if 'HTTP_ORIGIN' in request.META and request.META.get('CONTENT_TYPE', '') in ('text/plain', ''):
            request.META['CONTENT_TYPE'] = 'application/json'

            # Also set this semi-hidden variable on the request, as it has
            # already been set and needs to be calculated again.
            request._content_type = 'application/json'
        return super(_XDomainRequestCompatNegotiation, self).select_parser(request, parsers)


class ShareaboutsContentNegotiation (_JSONPCallbackNegotiation, _XDomainRequestCompatNegotiation):
    pass
