from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from django.contrib.auth.models import User
import telnyx, time, math
import numpy
from django.core.mail import EmailMessage, send_mail
from django.core import mail
from .send import set_account



class PhoneNumber(models.Model):
    '''This class is used to store phone numbers'''
    number = PhoneNumberField(max_length=16)
    added_by = models.ForeignKey(User, related_name='added_phone_numbers', null=True, verbose_name="added by", on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.number.as_e164

    class Meta:
        ordering = ['-date_added']


class EmailAddress(models.Model):
    '''Email address model'''
    address = models.EmailField(max_length=200)
    added_by = models.ForeignKey(User, related_name='added_email_addresses', null=True, verbose_name="added by", on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return str(self.address)

    class Meta:
        ordering = ['address']


class TextMessage(models.Model):
    '''The message to be sent'''
    message = models.TextField(max_length=500)
    sent_by = models.ForeignKey(User, related_name='text_messages', verbose_name="sender", null=True, on_delete=models.CASCADE)
    sent_to = models.ManyToManyField(PhoneNumber, max_length=16, default=None, blank=True, related_name="sms_received", verbose_name="receivers")
    date_created = models.DateTimeField(default=timezone.now)
    date_sent = models.DateTimeField(default=timezone.now) 
    is_sent = models.BooleanField(default=False)

    def __str__(self):
        return self.message

    class Meta:
        ordering = ['-date_created']

    def send(self, receivers=None):
        '''Handles the sending of sms objects'''
        count = 0
        if receivers and receivers != []:
            for receiver in receivers:
                self.sent_to.add(receiver)
            for receiver in receivers:
                # allows only five messages to be sent per second
                if count < 5:
                    try:
                        telnyx.api_key = "KEY018329C263D7B16A58CACEF6308876B9_wIlFXA6tn4GxeaVHvCsaIT"
                        telnyx.Message.create(
                            from_="+14093595198",
                            to=receiver.number.as_e164,
                            text=self.message,
                        )
                        count += 1
                    except telnyx.error.APIConnectionError as e:
                        print(e)
                        return False, 'Connection error! Please Check your internet connectivity.'
                    except telnyx.error.APIError as e:
                        print(e)
                        return False, e.__dict__['errors'][0]['detail']
                    except telnyx.error.AuthenticationError as e:
                        print(e)
                        return False, e.__dict__['errors'][0]['detail']
                    except telnyx.error.InvalidRequestError as e:
                        print(e)
                        return False, e.__dict__['errors'][0]['detail']
                    except telnyx.error.RateLimitError as e:
                        print(e)
                        return False, e.__dict__['errors'][0]['detail']
                    except Exception as e:
                        print(e)
                        return False, e.__dict__['errors'][0]['detail']
                else:
                    time.sleep(1)
                    count = 0    
            self.is_sent = True
            self.save()
            return True, 'Message sent successfully.'

        elif not receivers and self.sent_to.all() != []:
            for receiver in self.sent_to.all():
                if count < 5:
                    try:
                        telnyx.api_key = "KEY018329C263D7B16A58CACEF6308876B9_wIlFXA6tn4GxeaVHvCsaIT"
                        telnyx.Message.create(
                            from_="+14093595198",
                            to=receiver.number.as_e164,
                            text=self.message,
                        )
                        count += 1
                    except telnyx.error.APIConnectionError as e:
                        print(e)
                        return False, 'Connection error! Please Check your internet connectivity.'
                    except telnyx.error.APIError as e:
                        print(e)
                        return False, e.__dict__['errors'][0]['detail']
                    except telnyx.error.AuthenticationError as e:
                        print(e)
                        return False, e.__dict__['errors'][0]['detail']
                    except telnyx.error.InvalidRequestError as e:
                        print(e)
                        return False, e.__dict__['errors'][0]['detail']
                    except telnyx.error.RateLimitError as e:
                        print(e)
                        return False, e.__dict__['errors'][0]['detail']
                    except Exception as e:
                        print(e)
                        return False, e.__dict__['errors'][0]['detail']
                else:
                    time.sleep(1)
                    count = 0
            self.is_sent = True
            self.save()
            return True, 'Message sent successfully.'
        else:
            return False, "Error! Message needs receivers to be sent."





class Email(models.Model):
    '''Handles the creation and sending of email objects'''
    subject = models.CharField(max_length=200, null=True, blank=True, default=None)
    bcc = models.TextField(max_length=500, default=None, blank=True, null=True)
    cc = models.TextField(max_length=500, default=None, blank=True, null=True)
    body = models.TextField(max_length=5000, default=None)
    sent_by = models.ForeignKey(User, related_name='mails', null=True, verbose_name="sender", on_delete=models.CASCADE)
    sent_to = models.ManyToManyField(EmailAddress, related_name="mails_received", verbose_name="receivers")
    date_created = models.DateTimeField(default=timezone.now)
    date_sent = models.DateTimeField(default=timezone.now)
    is_sent = models.BooleanField(default=False)

    def __str__(self):
        if self.subject:
            return self.subject
        return self.body

    class Meta:
        ordering = ['-date_created']


    def send(self, receivers=None):
        connection = mail.get_connection()
        if receivers and receivers != []:
            for receiver in receivers:
                self.sent_to.add(receiver)
            if len(self.sent_to.all()) <= 500:
                # send_mail('','This is test sms with smtp', 'tholuwarlarshe2003@gmail.com', ['+2349013329333',], auth_user="samasenpai07@gmail.com", auth_password='mxqwczfcansizklo', connection=connection)
                #get attachments
                if self.attachments.all() and len(self.attachments.all()) > 0:
                    attachments = [(attachment.file.name, attachment.file.read()) for attachment in self.attachments.all()]
                else:
                    attachments = None
                #get bcc
                if self.bcc and self.bcc != '':
                    bcc = self.bcc.split(',')
                else:
                    bcc = None
                #get cc
                if self.cc and self.cc != '':
                    cc = self.cc.split(',')
                else:
                    cc = None

                email = EmailMessage(
                            subject=self.subject,
                            body=self.body,
                            to=self.sent_to.values_list('address', flat=True),
                            bcc=bcc,
                            cc=cc,
                            attachments=attachments,
                            connection=connection,
                        )
                try:
                    email.send()
                    self.is_sent = True
                    self.save()
                    return True, 'Email sent successfully'
                except Exception as e:
                    print(e)
                    return False, f'Failed to send email: {e}'

            else:
                no_of_splits = math.ceil(len(self.sent_to.all())/500)
                list_of_receivers = numpy.array_split(self.sent_to.all(), no_of_splits)
                email_msgs = []
                for receiver_list in list_of_receivers:
                    #get attachments
                    if self.attachments.all() and len(self.attachments.all()) > 0:
                        attachments = [(attachment.file.name, attachment.file.read()) for attachment in self.attachments.all()]
                    else:
                        attachments = None
                    #get bcc
                    if self.bcc and self.bcc != '':
                        bcc = self.bcc.split(',')
                    else:
                        bcc = None
                    #get cc
                    if self.cc and self.cc != '':
                        cc = self.cc.split(',')
                    else:
                        cc = None

                    email = EmailMessage(
                                subject=self.subject,
                                body=self.body,
                                to=[receiver.address for receiver in receiver_list],
                                bcc=bcc,
                                cc=cc,
                                attachments=attachments,
                                connection=connection,
                            )
                    email_msgs.append(email)
                try:
                    connection.send_messages(email_msgs)
                    self.is_sent = True
                    self.save()
                    return True, 'Email sent successfully'
                except Exception as e:
                    print(e)
                    return False, f'Failed to send email: {e}'
        
        elif not receivers and self.sent_to.all() != []:
            if len(self.sent_to.all()) <= 500:
                #get attachments
                if self.attachments.all() and len(self.attachments.all()) > 0:
                    attachments = [(attachment.file.name, attachment.file.read()) for attachment in self.attachments.all()]
                else:
                    attachments = None
                #get bcc
                if self.bcc and self.bcc != '':
                    bcc = self.bcc.split(',')
                else:
                    bcc = None
                #get cc
                if self.cc and self.cc != '':
                    cc = self.cc.split(',')
                else:
                    cc = None

                email = EmailMessage(
                            subject=self.subject,
                            body=self.body,
                            to=self.sent_to.values_list('address', flat=True),
                            bcc=bcc,
                            cc=cc,
                            attachments=attachments,
                            connection=connection,
                        )
                try:
                    email.send()
                    self.is_sent = True
                    self.save()
                    return True, 'Email sent successfully'
                except Exception as e:
                    print(e)
                    return False, f'Failed to send email: {e}'

            else:
                no_of_splits = math.ceil(len(self.sent_to.all())/500)
                list_of_receivers = numpy.array_split(self.sent_to.all(), no_of_splits)
                email_msgs = []
                for receiver_list in list_of_receivers:
                    #get attachments
                    if self.attachments.all() and len(self.attachments.all()) > 0:
                        attachments = [(attachment.file.name, attachment.file.read()) for attachment in self.attachments.all()]
                    else:
                        attachments = None
                    #get bcc
                    if self.bcc and self.bcc != '':
                        bcc = self.bcc.split(',')
                    else:
                        bcc = None
                    #get cc
                    if self.cc and self.cc != '':
                        cc = self.cc.split(',')
                    else:
                        cc = None

                    email = EmailMessage(
                                subject=self.subject,
                                body=self.body,
                                to=[receiver.address for receiver in receiver_list],
                                bcc=bcc,
                                cc=cc,
                                attachments=attachments,
                                connection=connection,
                            )
                    email_msgs.append(email)
                try:
                    connection.send_messages(email_msgs)
                    self.is_sent = True
                    self.save()
                    return True, 'Email sent successfully'
                except Exception as e:
                    print(e)
                    return False, f'Failed to send email: {e}'
            


def get_attachment_path(instance, filename):
    return 'attachments/{}/{}'.format(instance.added_by_id, filename)


class Attachment(models.Model):
    '''Handles the creation of attachments'''
    file = models.FileField(upload_to=get_attachment_path, null=True, blank=True, default=None)
    email = models.ForeignKey(Email, related_name='attachments', null=True, blank=True, default=None, on_delete=models.CASCADE)
    added_by = models.ForeignKey(User, related_name='attachments', null=True, default='none', verbose_name="added by", on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.file.name
    