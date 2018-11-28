from rest_framework import generics
from ..models import PlaceEmailTemplate
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.response import Response
from django.http import Http404

from .. import cors
from django.template import RequestContext, Template
from django.core.mail import EmailMultiAlternatives
import logging
logger = logging.getLogger('sa_api_v2.views')


class EmailTemplateDetailView(generics.RetrieveAPIView):
    """
    A view that returns a static HTML representation of a given email template.
    """
    queryset = PlaceEmailTemplate.objects.all()
    renderer_classes = (StaticHTMLRenderer,)
    model = PlaceEmailTemplate

    def get(self, request, email_template_id):
        data = self.get_object(email_template_id).body_html
        return Response(data)

    def get_object_or_none(self, pk=None):
        if pk is None:
            return None
        try:
            return self.model.objects\
                .filter(pk=pk)\
                .get()
        except self.model.DoesNotExist:
            return None

    def get_object_or_404(self, pk=None):
        obj = self.get_object_or_none(pk)
        if obj is None:
            raise Http404
        return obj

    def get_object(self, email_template_id):
        obj = self.get_object_or_404(email_template_id)
        return obj


# TODO: A class/mixin isn't needed. Refactor this into a function.
class EmailTemplateMixin(object):
    def send_email_notification(self, obj, submission_set_name):
        # TODO: until we establish a many:one relationship between the
        # Origin and EmailTemplate models, we are temporarily
        # disabling email notifications for Supports. Otherwise, there
        # is no way to have an EmailTemplate trigger on only Place and
        # Comment submissions, without having it trigger on Supports
        # as well.
        if submission_set_name not in ['comments', 'places']:
            return

        request_origin = self.request.META.get('HTTP_ORIGIN', '')
        email_templates = [origin.place_email_template for origin in obj.dataset.origins.all()
                           if cors.models.Origin.match(origin.pattern, request_origin) and
                           origin.place_email_template is not None]

        filtered_email_templates = filter(
            lambda template: template.submission_set in [submission_set_name, ''] and
            template.event == 'add',
            email_templates
        )

        for email_template in filtered_email_templates:
            logger.info('[EMAIL] Starting email send')

            from_email = email_template.from_email
            bcc_sources = [email_template.bcc_email_1,
                           email_template.bcc_email_2,
                           email_template.bcc_email_3,
                           email_template.bcc_email_4,
                           email_template.bcc_email_5]
            bcc_list = [source for source in bcc_sources if source]

            logger.debug('[EMAIL] Got from email')

            errors = []

            try:
                email_field = email_template.recipient_email_field
                recipient_email = self.request.data[email_field]
                logger.debug('[EMAIL] recipient_email: ' + recipient_email)
            except KeyError:
                logger.debug('[EMAIL] No primary recipient found. Setting primary recipient to the empty string.')
                recipient_email = ""

            logger.debug('[EMAIL] Got to email')

            # If the user didn't provide an email address, and no BCC emails are provided,
            # then we can't send an email
            if not recipient_email and not bcc_list:
                errors.append('[EMAIL] Error: No primary recipient and no BCC recipients provided. Email will not be sent.')

            # Bail if any errors were found. Send all errors to the logs and otherwise
            # fail silently.
            if errors:
                for error_msg in errors:
                    logger.error(error_msg)
                continue

            # If we didn't find any errors, then render the email and send.
            logger.debug('[EMAIL] Going ahead, no errors')

            # TODO: if this is a comment notification, then add a
            # `comment` key to the context as well. Note that we'll
            # have to change the Origin:EmailTemplate to be One:Many
            # for this to work.
            context_data = RequestContext(self.request, {
                'place': obj,
                'email': recipient_email
            })

            logger.debug('[EMAIL] Got context data')

            subject = Template(email_template.subject).render(context_data)
            body = Template(email_template.body_text).render(context_data)

            logger.debug('[EMAIL] Rendered text')

            if email_template.body_html:
                html_body = Template(email_template.body_html).render(context_data)
                logger.debug('[EMAIL] Rendered html')
            else:
                html_body = None

            # connection = smtp.EmailBackend(
            #     host=...,
            #     port=...,
            #     username=...,
            #     use_tls=...)

            # NOTE: In Django 1.7+, send_mail can handle multi-part email with the
            # html_message parameter, but pre 1.7 cannot and we must construct the
            # multipart message manually.
            msg = EmailMultiAlternatives(
                subject,
                body,
                from_email,
                to=[recipient_email],
                bcc=bcc_list)
            # connection=connection)

            logger.debug('[EMAIL] Created email')

            if html_body:
                msg.attach_alternative(html_body, 'text/html')
                logger.debug('[EMAIL] Attached html')

            msg.send()
            logger.info('[EMAIL] %s email for %d sent.', submission_set_name, obj.id)
            break
