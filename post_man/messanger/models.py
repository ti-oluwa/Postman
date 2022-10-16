from datetime import timedelta
from django.urls import reverse
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone, timesince
from users.models import CustomUser
import telnyx, time, math, random
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import numpy
from django.core.mail import EmailMessage
from django.core import mail
from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings



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
        ordering = ['address', '-date_added']
        verbose_name_plural = "Email addresses"


class TextMessage(models.Model):
    '''The message to be sent'''
    message = models.TextField(max_length=500)
    sent_by = models.ForeignKey(CustomUser, related_name='text_messages', verbose_name="sender", null=True, on_delete=models.CASCADE)
    send_to = models.ManyToManyField(PhoneNumber, max_length=16, related_name="directed_sms", default=None, verbose_name="proposed receivers")
    sent_to = models.ManyToManyField(PhoneNumber, max_length=16, default=None, blank=True, related_name="sms_received", verbose_name="receivers")
    date_created = models.DateTimeField(auto_now_add=True)
    date_sent = models.DateTimeField(default=timezone.now) 
    is_sent = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)

    def __str__(self):
        return self.message

    class Meta:
        ordering = ['-date_created']
        verbose_name_plural = "Text Messages"


    def send(self, receivers=None):
        '''Handles the sending of sms objects'''
        settings_url = reverse('settings')

        if self.sent_by.message_credit > 0:
            self.sent_by.can_send = True
        else:
            self.sent_by.can_send = False

        if not self.sent_by.accepted_pp:
            self.sent_by.accepted_pp = True
        self.sent_by.save()

        if self.sent_by.can_send and self.sent_by.accepted_pp:
            if receivers and receivers != []:
                for receiver in receivers:
                    self.send_to.add(receiver)
                self.save()
                return self.finish_sending(receivers) 

            elif not receivers and self.send_to.all() != []:
                return self.finish_sending(self.send_to.all())

            else:
                return False, 'No receivers specified.'
        elif self.sent_by.can_send == False and self.sent_by.message_credit <= 0:
            return False, "You have no credit to send messages. Please top-up your account. Click <a href='{}?purchase'>here</a> to top-up".format(settings_url)
        else:
            return False, "You are not permitted to send messages. Please <a href='mailto:{}'>contact</a> our support to reactivate your account.".format(settings.POSTMAN_SUPPORT_EMAIL)


    def delete(self, *args, **kwargs):
        '''Deletes the message object'''
        self.sent_to.clear()
        super().delete(*args, **kwargs)
    

    def finish_sending(self, receivers):
        '''Finishes sending the message to all the receivers'''
        settings_url = reverse('settings')
        active_senders = self.sent_by.message_profiles.filter(is_active=True)
        if active_senders and active_senders != []:
            count = 0
            start_time = timezone.now()
            # randomize the order of the active senders
            if self.sent_by.wants_random:
                random.shuffle(active_senders)
            if self.is_sent:
                return False, 'Message already sent.'
            for receiver in receivers:
                # allows only five messages to be sent per second
                if count < self.sent_by.preferred_sms_rate and timesince.timesince(start_time) < '1 minutes':
                    if self.sent_by.wants_random:
                        # further randomize the order of the active senders
                        senders = random.choices(random.choices(active_senders, k=len(active_senders)), k=(len(self.send_to.all())*len(active_senders)))
                        random.shuffle(senders)
                        sender = random.choice(senders)
                    else:
                        sender = random.choice(active_senders)
                    if math.floor(self.sent_by.message_credit) >= len(self.send_to.all()) or self.sent_by.is_privileged:
                        if sender.api_provider == 'telnyx':
                            self.send_via_telnyx(sender, receiver)
                            self.sent_by.save()
                            count += 1

                        elif sender.api_provider == 'twilio':
                            self.send_via_twilio(sender, receiver)
                            self.sent_by.save()
                            count += 1
                    
                    else:
                        self.save()
                        return False, 'Insufficient message credits.[{} recipient(s), {} message credit(s) available] Please <a href="{}?purchase">purchase more</a>.'.format( len(self.send_to.all()), math.floor(self.sent_by.message_credit), settings_url)

                elif count > self.sent_by.preferred_sms_rate and timesince.timesince(start_time) < '1 minutes':
                    # wait for the remaining time
                    wait_time = (timedelta(minutes=1) + start_time) - timezone.now()
                    time.sleep(wait_time.total_seconds())
                    # reset  time and count
                    start_time = timezone.now()
                    count = 0

            if not self.sent_by.wants_history:    
                self.delete()

            if len(self.sent_to.all()) == len(self.send_to.all()):
                self.is_sent = True
                self.is_draft = False
                self.save()
                return True, 'Message sent successfully.'
            elif len(self.sent_to.all()) > 0 and len(self.sent_to.all()) < len(self.send_to.all()):
                self.is_sent = True
                self.is_draft = False
                self.save()
                return True, 'Message sent! Some failed'
            else:
                return False, 'Message failed to send. Might be your internet connectivity.'
        else:
            return False, 'You have no active messaging profiles. Please create or enable one and retry. You can do this <a href="{}?add-m-profile">here</a>'.format(settings_url)
    
    def send_via_twilio(self, sender, receiver):
        '''Sends the message via twilio'''
        try:
            account_sid = sender.get_account_sid()
            auth_token = sender.get_api_key()
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=self.message,
                from_=sender.number.as_e164,
                to=receiver.number.as_e164,
            )
            print(message.sid)
            if not self.sent_by.is_privileged:
                self.sent_by.message_credit -= 1
            self.sent_to.add(receiver)
            self.save()

        except TwilioRestException as e:
            print(e)
            pass
        except Exception as e:
            print(e)
            pass


    def send_via_telnyx(self, sender, receiver):
        '''Sends the message via telnyx'''
        try:
            telnyx.api_key = sender.get_api_key()
            telnyx.Message.create(
                from_= sender.number.as_e164,
                to=receiver.number.as_e164,
                text=self.message,
            )
            if not self.sent_by.is_privileged:
                self.sent_by.message_credit -= 1
            self.sent_to.add(receiver)
            self.save()

        except telnyx.error.APIConnectionError as e:
            print(e)
            pass
            # return False, 'Connection error! Please Check your internet connectivity.'
        except telnyx.error.APIError as e:
            print(e)
            pass
            # return False, e.__dict__['errors'][0]['detail']
        except telnyx.error.AuthenticationError as e:
            print(e)
            pass
            # return False, e.__dict__['errors'][0]['detail']
        except telnyx.error.InvalidRequestError as e:
            print(e)
            pass
            # return False, e.__dict__['errors'][0]['detail']
        except telnyx.error.RateLimitError as e:
            print(e)
            pass
            # return False, e.__dict__['errors'][0]['detail']
        except Exception as e:
            print(e)
            pass
            # return False, e




class Email(models.Model):
    '''Handles the creation and sending of email objects'''
    subject = models.CharField(max_length=200, null=True, blank=True, default=None)
    bcc = models.TextField(max_length=500, default=None, blank=True, null=True)
    cc = models.TextField(max_length=500, default=None, blank=True, null=True)
    body = models.TextField(max_length=5000, default=None)
    sent_by = models.ForeignKey(CustomUser, related_name='mails', null=True, verbose_name="sender", on_delete=models.CASCADE)
    send_to = models.ManyToManyField(EmailAddress, related_name="directed_mails", default=None, verbose_name="proposed receivers")
    sent_to = models.ManyToManyField(EmailAddress, related_name="mails_received", verbose_name="receivers")
    date_created = models.DateTimeField(auto_now_add=True)
    date_sent = models.DateTimeField(default=timezone.now)
    is_sent = models.BooleanField(default=False)
    is_html = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)

    def __str__(self):
        if self.subject:
            return self.subject
        return self.body

    class Meta:
        ordering = ['-date_created']


    def send(self, receivers=None):
        settings_url = reverse('settings')

        if self.sent_by.message_credit > 0:
            self.sent_by.can_send = True
        else:
            self.sent_by.can_send = False

        if not self.sent_by.accepted_pp:
            self.sent_by.accepted_pp = True
        self.sent_by.save()

        if self.sent_by.can_send and self.sent_by.accepted_pp: 
            if receivers and receivers != []:
                for receiver in receivers:
                    self.send_to.add(receiver)
                self.save()
                return self.finish_sending()
                
            elif not receivers and self.send_to.all() != []:
                return self.finish_sending()

            else:
                return False, 'No receivers specified.'
        elif self.sent_by.can_send == False and self.sent_by.message_credit <= 0:
            return False, "You have no credit to send mails. Please top-up your account. Click <a href='{}?purchase'>here</a> to top-up.".format(settings_url)
        else:
            return False, 'You are not permitted to send emails. Please <a href="mailto:{}">contact</a> our support to reactivate your account.'.format(settings.POSTMAN_SUPPORT_EMAIL)
    
    
    def finish_sending(self):
            settings_url = reverse('settings')
            active_senders = list(self.sent_by.email_profiles.filter(is_active=True))
            
            if self.sent_by.can_use_default and self.sent_by.wants_default:
                if CustomUser.objects.filter(is_active=True, username='Default user').exists():
                    active_senders += list(CustomUser.objects.filter(is_active=True, username='Default user')[0].email_profiles.filter(is_active=True))
            if active_senders and active_senders != []:
                random.shuffle(active_senders)
                if self.sent_by.wants_random:
                    #further randomize the order of the active senders
                    senders = random.choices(random.choices(active_senders, k=len(active_senders)), k=(len(self.send_to.all())*len(active_senders)))
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
                no_of_splits = math.ceil(len(self.send_to.all())/100)
                list_of_receivers = numpy.array_split(self.send_to.all(), no_of_splits)
                email_msgs = []
                    
                for receivers in list_of_receivers:
                    for receiver in receivers:
                        sender = random.choice(senders)
                        connection = EmailBackend(host=sender.host, port=sender.port, username=sender.email, password=sender.get_app_pass(), use_tls=sender.use_tls, use_ssl=sender.use_ssl)
                        email = EmailMessage(
                                    subject=self.subject,
                                    body=self.body,
                                    from_email=sender.email,
                                    to=[receiver.address,],
                                    bcc=bcc,
                                    cc=cc,
                                    attachments=attachments,
                                    connection=connection,
                                )
                        email_msgs.append(email)
                #send the emails
                if self.is_sent:
                    return False, 'Email already sent.'
                try:
                    start_time = timezone.now()
                    count = 0
                    for email in email_msgs:
                        if count < self.sent_by.preferred_mail_rate and timesince.timesince(start_time) < '1 minutes':
                            if self.is_html:
                                email.content_subtype = 'html'
                            if math.floor(self.sent_by.message_credit) >= len(self.send_to.all()) or self.sent_by.is_privileged:
                                try:
                                    email.send()
                                    if not self.sent_by.is_privileged:
                                        self.sent_by.message_credit -= 1
                                    receiver_ = [ EmailAddress.objects.filter(address=recipient, added_by=self.sent_by).first() for recipient in email.recipients() if EmailAddress.objects.filter(address=recipient, added_by=self.sent_by).exists() ][0]
                                    self.sent_to.add(receiver_)
                                    self.save()
                                    self.sent_by.save()
                                except Exception as e:
                                    print(e.args)
                                    pass

                            else:
                                self.save()
                                return False, 'Insufficient message credits.[{} recipient(s), {} message credit(s) available] Please <a href="{}?purchase">purchase more</a>.'.format(len(self.send_to.all()), math.floor(self.sent_by.message_credit), settings_url)
                        elif count > self.sent_by.preferred_mail_rate and timesince.timesince(start_time) < '1 minutes':
                            # wait for the remaining time
                            wait_time = (timedelta(minutes=1) + start_time) - timezone.now()
                            time.sleep(wait_time.total_seconds())
                            # reset time and count
                            start_time = timezone.now()
                            count = 0

                    if not self.sent_by.wants_history:
                        self.delete()

                    if len(self.sent_to.all()) == len(self.send_to.all()):
                        self.is_sent = True
                        self.is_draft = False
                        self.save()
                        return True, 'Email sent successfully.'
                    elif len(self.sent_to.all()) > 0 and len(self.sent_to.all()) < len(self.send_to.all()):
                        self.is_sent = True
                        self.is_draft = False
                        self.save()
                        return True, 'Email sent! Some failed'
                    else:
                        return False, 'Email failed to send. Might be your internet connectivity.'
                except Exception as e:
                    print(e)
                    return False, f'Failed to send email: {e}'
            else:
                return False, 'You have no active emailing profiles. Please create or enable one and retry. You can do this <a href="{}?add-e-profile">here</a>'.format(settings_url)


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



class BlackListedWord(models.Model):
    word = models.CharField(max_length=250, unique=True)
    replacement_word = models.CharField(max_length=250, blank=True, default=None, verbose_name='suitable replacement word')
    date_added = models.DateTimeField(default=timezone.now)
    class Meta:
        ordering = ['word']

    def __str__(self):
        return self.word
    