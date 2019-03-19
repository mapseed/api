import time
import json
import logging


# Request logging examples:
# https://github.com/Rhumbix/django-request-logging/blob/master/request_logging/middleware.py
# https://gist.github.com/SehgalDivij/1ca5c647c710a2c3a0397bce5ec1c1b4
class RequestBodyLogger (object):
    logger = logging.getLogger('ms_api.request')
    allowed_methods = ['post', 'put', 'patch', 'delete']

    def process_request(self, request):
        method = request.method.lower()
        if (method in self.allowed_methods and
           request.META.get('CONTENT_TYPE') == 'application/json'):
            # DELETE often has an empty string as body:
            if request.body == '' or request.body is None:
                self.logger.info('"{} {}"'.format(
                    request.method,
                    request.get_full_path(),
                ))
            else:
                self.logger.info('"{} {}" {}'.format(
                    request.method,
                    request.get_full_path(),
                    json.dumps(json.loads(request.body.decode("utf-8")), indent=2)
                ))


class RequestTimeLogger (object):
    def process_request(self, request):
        self.start_time = time.time()

    def process_response(self, request, response):
        # NOTE: If there was some exception, or some other reason that the
        # process_request method was not called, we won't know the start time.
        # Check that we know it first.
        if hasattr(self, 'start_time'):
            duration = time.time() - self.start_time

            # Log the time information
            logger = logging.getLogger('utils.request_timer')
            logger.debug('(%0.3f) "%s %s" %s' % (
                duration,
                request.method,
                request.get_full_path(),
                response.status_code
            ))

        return response


class CookiesLogger (object):
    """
    Logs in the request and response.
    """
    def process_response(self, request, response):
        logger = logging.getLogger('utils.cookies_logger')
        logger.debug(
            '(%s)\n'
            '\n'
            'Request cookies: %s\n'
            '\n'
            'Response cookies: %s' % (
                response.status_code, 
                request.COOKIES, 
                response.cookies or {}
        ))
        return response


class JSEnableAllCookies (object):
    """
    Removes the httponly flag from all the cookies being set.
    """
    def process_response(self, request, response):
        if response.cookies:
            for morsel in response.cookies.values():
                morsel['httponly'] = ''

        return response
