from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from users.models import CustomUser
import telnyx, time, math, random
import numpy
from django.core.mail import EmailMessage
from django.core import mail
from django.core.mail.backends.smtp import EmailBackend


class PhoneNumber(models.Model):
    '''This class is used to store phone numbers'''
    number = PhoneNumberField(max_length=16)
    added_by = models.ForeignKey(CustomUser, related_name='added_phone_numbers', null=True, verbose_name="added by", on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.number.as_e164

    class Meta:
        ordering = ['-date_added']


class EmailAddress(models.Model):
    '''Email address model'''
    address = models.EmailField(max_length=200)
    added_by = models.ForeignKey(CustomUser, related_name='added_email_addresses', null=True, verbose_name="added by", on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return str(self.address)

    class Meta:
        ordering = ['address']
        verbose_name_plural = "Email addresses"


class TextMessage(models.Model):
    '''The message to be sent'''
    message = models.TextField(max_length=500)
    sent_by = models.ForeignKey(CustomUser, related_name='text_messages', verbose_name="sender", null=True, on_delete=models.CASCADE)
    sent_to = models.ManyToManyField(PhoneNumber, max_length=16, default=None, blank=True, related_name="sms_received", verbose_name="receivers")
    date_created = models.DateTimeField(default=timezone.now)
    date_sent = models.DateTimeField(default=timezone.now) 
    is_sent = models.BooleanField(default=False)

    def __str__(self):
        return self.message

    class Meta:
        ordering = ['-date_created']
        verbose_name_plural = "Text Messages"


    def send(self, receivers=None):
        '''Handles the sending of sms objects'''
        if self.sent_by.can_send:
            if receivers and receivers != []:
                for receiver in receivers:
                    self.sent_to.add(receiver)
                self.save()
                return self.finish_sending(receivers) 

            elif not receivers and self.sent_to.all() != []:
                return self.finish_sending(self.sent_to.all())

            else:
                return False, 'No receivers specified.'
        else:
            return False, 'You are not permitted to send messages. Please reactivate your account.'


    def delete(self, *args, **kwargs):
        '''Deletes the message object'''
        self.sent_to.clear()
        super().delete(*args, **kwargs)
    

    def finish_sending(self, receivers):
        '''Finishes sending the message to all the receivers'''
        active_senders = self.sent_by.telnyx_profiles.filter(is_active=True)
        if active_senders and active_senders != []:
            count = 0
            # randomize the order of the active senders
            if self.sent_by.wants_random:
                random.shuffle(active_senders)
            for receiver in receivers:
                # allows only five messages to be sent per second
                if count < 5:
                    try:
                        if self.sent_by.wants_random:
                            # further randomize the order of the active senders
                            senders = random.choices(random.choices(active_senders, k=len(active_senders)), k=(len(self.sent_to.all())*len(active_senders)))
                            random.shuffle(senders)
                            sender = random.choice(senders)
                        else:
                            sender = random.choice(active_senders)
                        telnyx.api_key = sender.get_api_key()
                        telnyx.Message.create(
                            from_= sender.number.as_e164,
                            to=receiver.number.as_e164,
                            text=self.message,
                        )
                        count += 1
                    except telnyx.error.APIConnectionError as e:
                        (e)
                        return False, 'Connection error! Please Check your internet connectivity.'
                    except telnyx.error.APIError as e:
                        (e)
                        return False, e.__dict__['errors'][0]['detail']
                    except telnyx.error.AuthenticationError as e:
                        (e)
                        return False, e.__dict__['errors'][0]['detail']
                    except telnyx.error.InvalidRequestError as e:
                        (e)
                        return False, e.__dict__['errors'][0]['detail']
                    except telnyx.error.RateLimitError as e:
                        (e)
                        return False, e.__dict__['errors'][0]['detail']
                    except Exception as e:
                        (e)
                        return False, e
                else:
                    time.sleep(1)
                    count = 0
            if self.sent_by.wants_history:    
                self.is_sent = True
                self.save()
            else:
                self.delete()
            return True, 'Message sent successfully.'
        else:
            return False, 'You have no active messaging profiles. Please create or enable one.'

        




class Email(models.Model):
    '''Handles the creation and sending of email objects'''
    subject = models.CharField(max_length=200, null=True, blank=True, default=None)
    bcc = models.TextField(max_length=500, default=None, blank=True, null=True)
    cc = models.TextField(max_length=500, default=None, blank=True, null=True)
    body = models.TextField(max_length=5000, default=None)
    sent_by = models.ForeignKey(CustomUser, related_name='mails', null=True, verbose_name="sender", on_delete=models.CASCADE)
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
        if self.sent_by.can_send:
            if receivers and receivers != []:
                for receiver in receivers:
                    self.sent_to.add(receiver)
                self.save()
                return self.finish_sending()
                
            elif not receivers and self.sent_to.all() != []:
                return self.finish_sending()

            else:
                return False, 'No receivers specified.'
        else:
            return False, 'You are not permitted to send emails. Please reactivate your account.'
    
    
    def finish_sending(self):
            active_senders = list(self.sent_by.email_profiles.filter(is_active=True))
            if active_senders and active_senders != []:
                if self.sent_by.wants_random:
                    random.shuffle(active_senders)

                if self.sent_by.wants_random:
                    #further randomize the order of the active senders
                    senders = random.choices(random.choices(active_senders, k=len(active_senders)), k=(len(self.sent_to.all())*len(active_senders)))
                    random.shuffle(senders)
                else:
                    senders = random.choices(active_senders, k=(len(active_senders)))

                # prepare the emails to be sent
                #get attachments
                if self.attachments.all() and len(self.attachments.all()) > 0:
                    attachments = [(attachment.file.name, attachment.file.read()) for attachment in self.attachments.all()]
                else:
                    attachments = None
                #get bcc
                if self.bcc and self.bcc != '':
                    bcc = self.bcc.split(',')
                else:
                    bcc = []
                #get cc
                if self.cc and self.cc != '':
                    cc = self.cc.split(',')
                else:
                    cc = []

                #split the receivers into chunks to be sent with different senders and connections
                no_of_splits = math.ceil(len(self.sent_to.all())/100)
                list_of_receivers = numpy.array_split(self.sent_to.all(), no_of_splits)
                email_msgs = []
                    
                for receivers in list_of_receivers:
                    for receiver in receivers:
                        sender = random.choice(senders)
                        connection = EmailBackend(host=sender.host, port=sender.port, username=sender.email, password=sender.get_app_pass(), use_tls=True, use_ssl=False)
                        email = EmailMessage(
                                    subject=self.subject,
                                    body=self.body,
                                    to=[sender.email,],
                                    bcc=bcc + [receiver.address,],
                                    cc=cc,
                                    attachments=attachments,
                                    connection=connection,
                                )
                        email_msgs.append(email)
                #send the emails
                    try:
                        for email in email_msgs:
                            email.send()
                        if self.sent_by.wants_history:    
                            self.is_sent = True
                            self.save()
                        else:
                            self.delete()
                        return True, 'Email sent successfully'
                    except Exception as e:
                        (e)
                        return False, f'Failed to send email: {e}'
            else:
                return False, 'You have no active emailing profiles. Please create or enable one.'

    def delete(self, *args, **kwargs):
        for attachment in self.attachments.all():
            attachment.delete()
        self.sent_to.clear()
        super().delete(*args, **kwargs)
        



def get_attachment_path(instance, filename):
    return 'attachments/{}/{}'.format(instance.added_by_id, filename)


class Attachment(models.Model):
    '''Handles the creation of attachments'''
    file = models.FileField(upload_to=get_attachment_path, null=True, blank=True, default=None)
    email = models.ForeignKey(Email, related_name='attachments', null=True, blank=True, default=None, on_delete=models.CASCADE)
    added_by = models.ForeignKey(CustomUser, related_name='attachments', null=True, default=None, verbose_name="added by", on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.file.name
    