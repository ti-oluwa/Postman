from datetime import datetime, timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.utils import IntegrityError
from users.models import EmailProfile, MessageProfile
from .models import EmailAddress, PhoneNumber, TextMessage, Email, Attachment, BlackListedWord
from django.http import HttpResponse, JsonResponse
import json, mimetypes, os, re, time, math
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.encoding import smart_str
from django.contrib.auth import get_user_model
from django.db.models.functions import Lower

CustomUser = get_user_model()







class MessageView(LoginRequiredMixin, View):
    '''Handles requests related to the sms page'''
    model1 = TextMessage
    model2 = PhoneNumber
    template_name = 'messanger/messages.html'
    context_object_name = 'text_messages'
    ordering = ['-date_created']

    def get(self, request, *args, **kwargs):
        messages, phone_numbers = self.get_queryset()
        self.context = {
            'text_messages': messages,
            'phone_numbers': phone_numbers,
        }
        return render(request, self.template_name, self.context)

    def post(self, request, *args, **kwargs):
        pass

    def get_queryset(self):
        return self.model1.objects.filter(sent_by_id=self.request.user.id), self.model2.objects.filter(added_by_id=self.request.user.id)
        
    


class EmailView(LoginRequiredMixin, ListView):
    '''Handles requests related to the mails page'''
    model1 = Email
    model2 = EmailAddress
    template_name = 'messanger/email.html'
    context_object_name = 'emails'
    ordering = ['-date_created']

    def get(self, request, *args, **kwargs):
        emails, addresses = self.get_queryset()
        self.context = {
            'emails': emails,
            'email_addresses': addresses,
        }
        return render(request, self.template_name, self.context)

    def post(self, request, *args, **kwargs):
        pass

    def get_queryset(self):
        return self.model1.objects.filter(sent_by_id=self.request.user.id), self.model2.objects.filter(added_by_id=self.request.user.id)




class ValidateMessage(View):
    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        response ={}
        if is_ajax:
            message = re.split(r"[\s,.;\-\?\!\(\)\:~'\[\]\{\}&_@#\*\^\>\<]", request.POST['message'])
            black_listed_words = [bad_word.word.lower() for bad_word in BlackListedWord.objects.all()]
            bad_words = [word for word in message if word.lower() in black_listed_words]
            bad_words_set = []
            for bad_word in bad_words:
                count = bad_words.count(bad_word)
                if count > 1:
                    bad_words_set.append('{}({})'.format(bad_word, count))
                else:
                    bad_words_set.append(bad_word)

            if len(bad_words_set) == 0:
                response['message'] = 'success'
            else:
                response['message'] = 'error'
                response['bad_words'] = list(set(bad_words_set))
            return JsonResponse(data=response, status=200)


class ProfileDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    '''View for deleting messaging and email profiles'''
    model1 = EmailProfile
    model2= MessageProfile

    def test_func(self):
        if self.kwargs['object_type'] == 'ep':
            if self.model1.objects.filter(id=self.kwargs['pk']).exists() and  self.request.user == self.model1.objects.get(id=self.kwargs['pk']).owned_by:
                return True
            return False
        elif self.kwargs['object_type'] == 'mp':
            if self.model2.objects.filter(id=self.kwargs['pk']).exists() and self.request.user == self.model2.objects.get(id=self.kwargs['pk']).owned_by:
                return True
            return False
        return False

    def get(self, request, *args, **kwargs):
        try:
            object_type = kwargs['object_type']
            object_id = kwargs['pk']
        except KeyError:
            messages.error(request, 'Oops! Something went wrong')
            return redirect('settings')

        if object_type == 'ep':
            try:
                obj = self.model1.objects.get(id=object_id)
                obj.delete()
                messages.success(request, "Profile deleted successfully")
            except Exception as e:
                messages.error(request, 'Error: {}'.format(e))
        elif object_type == 'mp':
            try:
                obj = self.model2.objects.get(id=object_id)
                obj.delete()
                messages.success(request, "Profile deleted successfully")
            except Exception as e:
                messages.error(request, 'Error: {}'.format(e))
        return redirect('settings')
            

class DeleteAllContactsView(LoginRequiredMixin, UserPassesTestMixin, View):
    '''View for deleting all contacts'''
    model1 = EmailAddress
    model2 = PhoneNumber

    def test_func(self):
        if self.request.user.is_active:
            return True
        return False

    def get(self, request, *args, **kwargs):
        try:
            self.model1.objects.filter(added_by_id=request.user.id).delete()
            self.model2.objects.filter(added_by_id=request.user.id).delete()
            messages.success(request, 'All contacts deleted successfully')
        except Exception as e:
            messages.error(request, 'Error: {}'.format(e))
        return redirect('settings')


class EditDraftAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    '''View for editing drafted messages'''
    def test_func(self):
        if self.request.user.is_active and ( TextMessage.objects.filter(id=self.request.POST['draft_id'], sent_by=self.request.user).exists() or Email.objects.filter(id=self.request.POST['draft_id'], sent_by=self.request.user).exists() ):
            return True
        return False

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        response = {}
        if is_ajax:
            draft_id = request.POST['draft_id']
            object_type = request.POST['object_type']
            if object_type == 'sms':
                try:
                    draft = TextMessage.objects.get(id=draft_id)
                    response['data'] = {
                        'message': draft.message,
                    }
                    response['success'] = 'true'
                    request.session.set_test_cookie()
                    request.session['last_edit_request_sms_draft_id'] = draft_id

                except Exception as e:
                    response['success'] = 'false'
                    response['error'] = e
            elif object_type == 'email':
                try:
                    draft = Email.objects.get(id=draft_id)
                    response['data'] = {
                        'message': draft.body,
                        'subject': draft.subject,
                        'bcc': draft.bcc,
                        'cc': draft.cc,
                    }
                    response['success'] = 'true'
                    request.session.set_test_cookie()
                    request.session['last_edit_request_email_draft_id'] = draft_id

                except Exception as e:
                    response['success'] = 'false'
                    response['error'] = e
            return JsonResponse(data=response, status=200)

        return JsonResponse(status=400)



class RetryView(LoginRequiredMixin, UserPassesTestMixin, View):
    '''Handles requests related to the retrying mails or sms'''
    model1 = TextMessage
    model2 = Email
    
    def get(self, request, *args, **kwargs):
        try:
            object_id = self.request.GET.get('pk')
            object_type = self.request.GET.get('type')
        except KeyError:
            messages.error(request, 'Oops! Something went wrong')
            return redirect('home')
        if object_type == 'sms':
            obj = get_object_or_404(self.model1, pk=object_id)
            is_sent, response = obj.send()
            if is_sent:
                messages.success(request, response)
            else:
                messages.error(request, response)
            return redirect('messages')
        elif object_type == 'email':
            obj = get_object_or_404(self.model2, pk=object_id)
            is_sent, response = obj.send()
            if is_sent:
                messages.success(request, response)
            else:
                messages.error(request, response)
            return redirect('emails')

    def test_func(self):
        try:
            object_id = self.request.GET.get('pk')
            object_type = self.request.GET.get('type')
        except KeyError:
            return False
        if object_type == 'sms':
            if self.request.user == self.model1.objects.get(id=object_id).sent_by:
                return True
            return False
        elif object_type == 'email':
            if self.request.user == self.model2.objects.get(id=object_id).sent_by:
                return True
            return False


class DownloadView(LoginRequiredMixin, UserPassesTestMixin,View):
    model = Email

    def get(self, request, *args, **kwargs):
        try:
            object_id = self.request.GET.get('pk')
            attachment_id = self.request.GET.get('file_id')
        except KeyError:
            messages.error(request, 'Oops! Something went wrong')
            return redirect('emails')
        object = get_object_or_404(self.model, id=object_id)
        try:
            attachment = object.attachments.get(id=attachment_id)
        except Attachment.DoesNotExist:
            messages.error(request, f'Download error: Attachment does not exist')
            return redirect('emails')

        file_path = f'{settings.MEDIA_ROOT}/{attachment.file.name}'
        try:
            path = open(file_path, 'rb')
        except Exception or FileNotFoundError:
            messages.error(request, 'Download Error: Could not find attachment')
            return redirect('emails')
        mime_type, _ = mimetypes.guess_type(file_path)
        response = HttpResponse(path, content_type=mime_type)
        response['Content-Disposition'] = "attachment; filename={}".format(smart_str(attachment.file.name.replace(f'attachments/{attachment.added_by_id}/', '')))
        response['X-Sendfile'] = smart_str(file_path)
        return response


    def test_func(self):
        object_id = self.request.GET.get('pk')
        attachment_id = self.request.GET.get('file_id')
        object = get_object_or_404(self.model, id=object_id)
        attachment = object.attachments.get(id=attachment_id)
        if self.request.user == object.sent_by and self.request.user == attachment.added_by:
            return True
        return False

    

class AjaxView(LoginRequiredMixin, View):
    '''Handles ajax requests for sending emails and sms'''
    feedback = {'messages': []}
    feedback_ready = False
    

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        settings_url = reverse('settings')

        if is_ajax:
            payload, files = json.loads(request.POST['payload']), request.FILES
            try:
                add_form = payload['addFormData']
                select_form = payload['selectFormData']
                message_form = payload['messageFormData']
            except KeyError as e:
                print(e)
                pass
            try:
                action = payload['action']
            except KeyError:
                return JsonResponse(data={'success':'false',}, status=200)

            phone_number_pattern = re.compile(r'^\+(?:[0-9] ?){10,14}[0-9]$')
            email_pattern = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,6}$')
            receivers = set()
            already_exists = set()
            attached_files = []
            new_contacts = 0
            lines = []
            html_message = None

            for key in files.keys():
                if key == 'file':
                    contact_file = files['file']
                    if action == 'send_message':
                        lines += re.split(r"[\s,.;\-']", contact_file.read().decode('utf-8'))
                    elif action == 'send_email': 
                        lines += re.split(r"[\s,;']", contact_file.read().decode('utf-8'))

                    if contact_file.name.split('.').pop() not in ['txt', 'csv']:
                        messages.error(request, 'Invalid file format')
                        return JsonResponse(data={'success':'false',}, status=200)

                    if contact_file.size > 1048576:
                        messages.error(request, 'File size too large')
                        if action == 'send_message':
                            return redirect('messages')
                        elif action == 'send_email':
                            return redirect('emails')

                    
            for key in files.keys():
                if key.startswith('attached_file'):
                    total_size = 0
                    attached_files.append(files[key])
                    for file in attached_files:
                        total_size += int(file.size)

                    if total_size > 26214400:
                        messages.error(request, f'Files size must not exceed 25MB')
                        return JsonResponse(data={'success':'false',}, status=200)

            for key in files.keys():
                if key.startswith('attached_html_file'):
                    html_file = files[key]
                    html_message = html_file.read().decode('utf-8')

            # for editing html file content
            if action == 'edit_html' and html_message:
                return JsonResponse(data={'success':'true', 'html': html_message,}, status=200)

            # for sms
            if action == 'send_message':
                if files and lines != []:
                    for line in lines:
                        for phone_number in phone_number_pattern.findall(line):
                            if PhoneNumber.objects.filter(number=phone_number, added_by=request.user).exists():
                                already_exists.add(phone_number)
                                receivers.add(phone_number)
                            else:
                                registered_number = PhoneNumber.objects.create(number=phone_number, added_by=request.user)
                                registered_number.save()
                                new_contacts += 1
                                receivers.add(registered_number.number)

                if len(receivers) == 0 and 'file' in files.keys():
                    messages.error(request, 'No phone number found in file')
                elif len(receivers) > 0 and files:
                    if len(receivers) > 1:
                        messages.info(request, f'{len(receivers)} phone numbers found in {contact_file.name}')
                    else:
                        messages.info(request, f'{len(receivers)} phone number found in {contact_file.name}')
                
                if add_form['phone_numbers'] != '':
                    for phone_number in add_form['phone_numbers'].split(','):
                        if PhoneNumber.objects.filter(number=phone_number, added_by=request.user).exists():
                            already_exists.add(phone_number)
                            receivers.add(phone_number)
                        else:
                            registered_number = PhoneNumber.objects.create(number=phone_number, added_by=request.user)
                            registered_number.save()
                            new_contacts += 1
                            receivers.add(registered_number.number)
                if new_contacts > 0:
                    if new_contacts > 1:
                        messages.success(request, f'{new_contacts} new phone numbers added')
                    else:
                        messages.success(request, f'{new_contacts} new phone number added')

                if len(already_exists) > 0 and len(already_exists) < 4:
                    self.feedback['messages'].append(f'{", ".join(already_exists)} already exists')
                    messages.info(request, f'{", ".join(already_exists)} already exists')

                elif len(already_exists) > 0 and len(already_exists) >= 4:
                    messages.info(request, f'{len(already_exists)} phone numbers already exists')
                
                if select_form['all_contacts'] == 'true':
                    rec = [phone_number for phone_number in PhoneNumber.objects.filter(added_by=request.user)]
                    for phone_number in rec:
                        receivers.add(phone_number.number)

                elif select_form['selected_contacts'] != [] and select_form['all_contacts'] != 'true':
                    rec = [phone_number for phone_number in PhoneNumber.objects.filter(number__in=select_form['selected_contacts'])]
                    for phone_number in rec:
                        receivers.add(phone_number.number)

                # get all phone numbers object in receivers set
                receivers = [ PhoneNumber.objects.filter(number=receiver, added_by=request.user).first() for receiver in receivers ]


                if message_form['message'] and len(receivers) > 0:
                    message = message_form['message']
                    if len(message) > 160:
                        messages.error(request, 'Failed to send message: SMS should not exceed 160 characters')
                        return JsonResponse(data={'success':'false',}, status=400)
                    message_list = re.split(r"[\s,.;\-\?\!\(\)\:~'\[\]\{\}&_@#\*\^\>\<]", message.lower())
                    black_listed_words = [bad_word.word.lower() for bad_word in BlackListedWord.objects.all()]
                    bad_words = [word for word in message_list if word.lower() in black_listed_words]
                    if bad_words != []:
                        bad_words = list(set(bad_words))
                        if len(bad_words) == 1:
                            messages.error(request, f'Failed to send message: {", ".join(bad_words)} is not allowed in message')
                        else:
                            messages.error(request, f'Failed to send message: {", ".join(bad_words)} are not allowed in message')
                        return JsonResponse(data={'success':'false',}, status=200)
                    # create a new message object
                    new_message = TextMessage.objects.create(message=message, sent_by=request.user)
                    new_message.save()
                    # send message to list of receivers and awaits response
                    is_sent, response = new_message.send(receivers)
                    if is_sent:
                        messages.success(request, response)
                        if len(new_message.sent_to.all()) > 0 and len(new_message.sent_to.all()) < len(new_message.send_to.all()):
                            diff = len(new_message.send_to.all()) - len(new_message.sent_to.all())
                            if diff > 1:
                                messages.info(request, f'{diff} messages failed to send')
                            else:
                                messages.info(request, f'{diff} message failed to send') 

                        if len(new_message.sent_to.all()) > 1:
                            messages.success(request, f'{len(new_message.sent_to.all())} messages sent')
                        elif len(new_message.sent_to.all()) == 1:
                            messages.success(request, f'{len(new_message.sent_to.all())} message sent')
                    
                    else:
                        if len(new_message.send_to.all()) == 0:
                            new_message.delete()
                        messages.error(request, response)
                        
                    return JsonResponse(data={'success':'true',}, status=200)
                elif len(receivers) == 0:
                    return JsonResponse(data={'success':'false',}, status=200)


            # for sms drafts
            if action == 'save_message_draft':
                if files and lines != []:
                    for line in lines:
                        for phone_number in phone_number_pattern.findall(line):
                            if PhoneNumber.objects.filter(number=phone_number, added_by=request.user).exists():
                                already_exists.add(phone_number)
                                receivers.add(phone_number)
                            else:
                                registered_number = PhoneNumber.objects.create(number=phone_number, added_by=request.user)
                                registered_number.save()
                                new_contacts += 1
                                receivers.add(registered_number.number)

                if len(receivers) == 0 and 'file' in files.keys():
                    messages.error(request, 'No phone number found in file')
                elif len(receivers) > 0 and files:
                    if len(receivers) > 1:
                        messages.info(request, f'{len(receivers)} phone numbers found in {contact_file.name}')
                    else:
                        messages.info(request, f'{len(receivers)} phone number found in {contact_file.name}')
                
                if add_form['phone_numbers'] != '':
                    for phone_number in add_form['phone_numbers'].split(','):
                        if PhoneNumber.objects.filter(number=phone_number, added_by=request.user).exists():
                            already_exists.add(phone_number)
                            receivers.add(phone_number)
                        else:
                            registered_number = PhoneNumber.objects.create(number=phone_number, added_by=request.user)
                            registered_number.save()
                            new_contacts += 1
                            receivers.add(registered_number.number)
                if new_contacts > 0:
                    if new_contacts > 1:
                        messages.success(request, f'{new_contacts} new phone numbers added')
                    else:
                        messages.success(request, f'{new_contacts} new phone number added')

                if len(already_exists) > 0 and len(already_exists) < 4:
                    self.feedback['messages'].append(f'{", ".join(already_exists)} already exists')
                    messages.info(request, f'{", ".join(already_exists)} already exists')

                elif len(already_exists) > 0 and len(already_exists) >= 4:
                    messages.info(request, f'{len(already_exists)} phone numbers already exists')
                
                if select_form['all_contacts'] == 'true':
                    rec = [phone_number for phone_number in PhoneNumber.objects.filter(added_by=request.user)]
                    for phone_number in rec:
                        receivers.add(phone_number.number)

                elif select_form['selected_contacts'] != [] and select_form['all_contacts'] != 'true':
                    rec = [phone_number for phone_number in PhoneNumber.objects.filter(number__in=select_form['selected_contacts'])]
                    for phone_number in rec:
                        receivers.add(phone_number.number)

                # get all phone numbers object in receivers set
                receivers = [ PhoneNumber.objects.filter(number=receiver, added_by=request.user).first() for receiver in receivers ]


                if message_form['message'] and len(receivers) > 0:
                    message = message_form['message']
                    if len(message) > 160:
                        messages.error(request, 'Failed to send message: SMS should not exceed 160 characters')
                        return JsonResponse(data={'success':'false',}, status=400)
                    message_list = re.split(r"[\s,.;\-\?\!\(\)\:~'\[\]\{\}&_@#\*\^\>\<]", message.lower())
                    black_listed_words = [bad_word.word.lower() for bad_word in BlackListedWord.objects.all()]
                    bad_words = [word for word in message_list if word.lower() in black_listed_words]
                    if bad_words != []:
                        bad_words = list(set(bad_words))
                        if len(bad_words) == 1:
                            messages.error(request, f'Failed to send message: {", ".join(bad_words)} is not allowed in message')
                        else:
                            messages.error(request, f'Failed to send message: {", ".join(bad_words)} are not allowed in message')
                        return JsonResponse(data={'success':'false',}, status=200)
                    # create a new message object
                    new_message = TextMessage.objects.create(message=message, sent_by=request.user)
                    new_message.is_draft = True
                    new_message.save()
                    # add all receivers to the message object
                    for receiver in receivers:
                        new_message.send_to.add(receiver)
                    new_message.save()
                    messages.success(request, 'Message saved as draft')
                    return JsonResponse(data={'success':'true',}, status=200)

                elif len(receivers) == 0:
                    message = message_form['message']
                    if request.session.test_cookie_worked() and request.user.accepted_cookies and request.session['last_edit_request_sms_draft_id']:
                        if TextMessage.objects.filter(sent_by=request.user, is_draft=True, id=request.session['last_edit_request_sms_draft_id']).exists():
                            draft = TextMessage.objects.filter(sent_by=request.user, is_draft=True, id=request.session['last_edit_request_sms_draft_id']).first()
                            draft.message = message
                            draft.save()
                            request.session['last_save_request_sms_draft_id'] = draft.id
                            messages.success(request, 'Draft updated')
                    elif not request.session.test_cookie_worked():
                        messages.error(request, 'Failed to save draft: Session expired. Please try enabling browser cookies and reload the page')
                    elif not request.user.accepted_cookies:
                        messages.error(request, "Failed to save draft: Please accept cookies. View <a href='{}?cookies'>settings</a> to accept cookies".format(settings_url))
                    else:
                        messages.error(request, 'No phone number found')
                    return JsonResponse(data={'success':'false',}, status=200)
        

            # for emails
            elif action == 'send_email':
                if files and lines != []:
                    for line in lines:
                        for email_address in email_pattern.findall(line):
                            if EmailAddress.objects.filter(address=email_address, added_by=request.user).exists():
                                already_exists.add(email_address)
                                receivers.add(email_address)
                            else:
                                registered_address = EmailAddress.objects.create(address=email_address, added_by=request.user)
                                registered_address.save()
                                new_contacts += 1
                                receivers.add(registered_address.address)

                if len(receivers) == 0 and 'file' in files.keys():
                    messages.error(request, 'No email address found in file')
                elif len(receivers) > 0 and files:
                    if len(receivers) > 1:
                        messages.info(request, f'{len(receivers)} email addresses found in {contact_file.name}')
                    else:
                        messages.info(request, f'{len(receivers)} email address found in {contact_file.name}')

                    
                if add_form['email_addresses'] != '':
                    for email_address in add_form['email_addresses'].split(','):
                        if EmailAddress.objects.filter(address=email_address, added_by=request.user).exists():
                            already_exists.add(email_address)
                            receivers.add(email_address)
                        else:
                            registered_address = EmailAddress.objects.create(address=email_address, added_by=request.user)
                            registered_address.save()
                            new_contacts += 1
                            receivers.add(registered_address.address)
                
                if new_contacts > 0:
                    if new_contacts > 1:
                        messages.success(request, f'{new_contacts} new email addresses added')
                    else:
                        messages.success(request, f'{new_contacts} new email address added')

                if len(already_exists) > 0 and len(already_exists) < 4:
                    messages.info(request, f'{", ".join(list(already_exists))} already exists')

                elif len(already_exists) > 0 and len(already_exists) >= 4:
                    messages.info(request, f'{len(already_exists)} email addresses already exists')
                

                if select_form['all_addresses'] == 'true':
                    rec = [email_address for email_address in EmailAddress.objects.all()]
                    for email in rec:
                        receivers.add(email.address)

                elif select_form['selected_addresses'] != [] and select_form['all_addresses'] != 'true':
                    rec = [email_address for email_address in EmailAddress.objects.filter(address__in=select_form['selected_addresses'])]
                    for email in rec:
                        receivers.add(email.address)

                # get all email address object in receivers set
                receivers = [ EmailAddress.objects.filter(address=receiver, added_by=request.user).first() for receiver in receivers ]

                if message_form and len(receivers) > 0:
                    if message_form['subject'] != '':
                        subject = message_form['subject'].title()
                    else:
                        subject = 'No Subject'
                    if message_form['bcc'] != '':
                        bcc = message_form['bcc']
                    else:
                        bcc = None
                    if message_form['cc'] != '':
                        cc = message_form['cc']
                    else:
                        cc = None
                    body = message_form['body']

                    message_list = re.split(r"[\s,.;\-\?\!\(\)\:~'\[\]\{\}&_@#\*\^\>\<]", body.lower())
                    black_listed_words = [bad_word.word.lower() for bad_word in BlackListedWord.objects.all()]
                    bad_words = [word for word in message_list if word.lower() in black_listed_words]
                    if bad_words != []:
                        bad_words = list(set(bad_words))
                        if len(bad_words) == 1:
                            messages.error(request, f'Failed to send message: {", ".join(bad_words)} is not allowed in mails')
                        else:
                            messages.error(request, f'Failed to send message: {", ".join(bad_words)} are not allowed in mails')
                        return JsonResponse(data={'success':'false',}, status=200)
                    # create a new message object
                    if html_message and len(html_message) > 5 and len(body) == 0:
                        new_email = Email.objects.create(subject=subject, bcc=bcc, cc=cc, body=html_message, sent_by=request.user, is_html=True)
                    elif html_message and len(body) > 5:
                        new_email = Email.objects.create(subject=subject, bcc=bcc, cc=cc, body=body, sent_by=request.user, is_html=True)
                    else:
                        new_email = Email.objects.create(subject=subject, bcc=bcc, cc=cc, body=body, sent_by=request.user)
                    new_email.save()
                    if len(body) > 4500 and not new_email.is_html:
                        new_email.delete()
                        messages.error(request, 'Failed to send mail: Mail body should not exceed 4500 characters')
                        return JsonResponse(data={'success':'false',}, status=400)

                    for file in attached_files:
                        attachment = Attachment.objects.create(file=file, added_by=request.user)
                        attachment.save()
                        new_email.attachments.add(attachment)
                    new_email.save()
                    # send mail to list of receivers and awaits response
                    is_sent, response= new_email.send(receivers)
                    if is_sent:
                        messages.success(request, response)
                        if len(new_email.sent_to.all()) > 0 and len(new_email.sent_to.all()) < len(new_email.send_to.all()):
                            diff = len(new_email.send_to.all()) - len(new_email.sent_to.all())
                            if diff > 1:
                                messages.info(request, f'{diff} emails failed to send')
                            else:
                                messages.info(request, f'{diff} email failed to send')

                        if len(new_email.sent_to.all()) > 1:
                            messages.success(request, f'{len(new_email.sent_to.all())} emails sent')
                        elif len(new_email.sent_to.all()) == 1:
                            messages.success(request, f'{len(new_email.sent_to.all())} email sent')
                        
                    else:
                        if len(new_email.send_to.all()) == 0:
                            new_email.delete()
                        messages.error(request, response)
                        
                    return JsonResponse(data={'success':'true',}, status=200)
                elif len(receivers) == 0:
                    return JsonResponse(data={'success':'false',}, status=200)
            
            # for email drafts
            elif action == 'save_email_draft':
                if files and lines != []:
                    for line in lines:
                        for email_address in email_pattern.findall(line):
                            if EmailAddress.objects.filter(address=email_address, added_by=request.user).exists():
                                already_exists.add(email_address)
                                receivers.add(email_address)
                            else:
                                registered_address = EmailAddress.objects.create(address=email_address, added_by=request.user)
                                registered_address.save()
                                new_contacts += 1
                                receivers.add(registered_address.address)

                if len(receivers) == 0 and 'file' in files.keys():
                    messages.error(request, 'No email address found in file')
                elif len(receivers) > 0 and files:
                    if len(receivers) > 1:
                        messages.info(request, f'{len(receivers)} email addresses found in {contact_file.name}')
                    else:
                        messages.info(request, f'{len(receivers)} email address found in {contact_file.name}')

                    
                if add_form['email_addresses'] != '':
                    for email_address in add_form['email_addresses'].split(','):
                        if EmailAddress.objects.filter(address=email_address, added_by=request.user).exists():
                            already_exists.add(email_address)
                            receivers.add(email_address)
                        else:
                            registered_address = EmailAddress.objects.create(address=email_address, added_by=request.user)
                            registered_address.save()
                            new_contacts += 1
                            receivers.add(registered_address.address)
                
                if new_contacts > 0:
                    if new_contacts > 1:
                        messages.success(request, f'{new_contacts} new email addresses added')
                    else:
                        messages.success(request, f'{new_contacts} new email address added')

                if len(already_exists) > 0 and len(already_exists) < 4:
                    messages.info(request, f'{", ".join(list(already_exists))} already exists')

                elif len(already_exists) > 0 and len(already_exists) >= 4:
                    messages.info(request, f'{len(already_exists)} email addresses already exists')
                

                if select_form['all_addresses'] == 'true':
                    rec = [email_address for email_address in EmailAddress.objects.all()]
                    for email in rec:
                        receivers.add(email.address)

                elif select_form['selected_addresses'] != [] and select_form['all_addresses'] != 'true':
                    rec = [email_address for email_address in EmailAddress.objects.filter(address__in=select_form['selected_addresses'])]
                    for email in rec:
                        receivers.add(email.address)

                # get all email address object in receivers set
                receivers = [ EmailAddress.objects.filter(address=receiver, added_by=request.user).first() for receiver in receivers ]

                if message_form and len(receivers) > 0:
                    if message_form['subject'] != '':
                        subject = message_form['subject'].title()
                    else:
                        subject = 'No Subject'
                    if message_form['bcc'] != '':
                        bcc = message_form['bcc']
                    else:
                        bcc = None
                    if message_form['cc'] != '':
                        cc = message_form['cc']
                    else:
                        cc = None
                    body = message_form['body']
                    
                    message_list = re.split(r"[\s,.;\-\?\!\(\)\:~'\[\]\{\}&_@#\*\^\>\<]", body.lower())
                    black_listed_words = [bad_word.word.lower() for bad_word in BlackListedWord.objects.all()]
                    bad_words = [word for word in message_list if word.lower() in black_listed_words]
                    if bad_words != []:
                        bad_words = list(set(bad_words))
                        if len(bad_words) == 1:
                            messages.error(request, f'Failed to save message: {", ".join(bad_words)} is not allowed in mails')
                        else:
                            messages.error(request, f'Failed to save message: {", ".join(bad_words)} are not allowed in mails')
                        return JsonResponse(data={'success':'false',}, status=200)
                    # create a new message object
                    if html_message and len(html_message) > 5 and len(body) == 0:
                        new_email = Email.objects.create(subject=subject, bcc=bcc, cc=cc, body=html_message, sent_by=request.user, is_html=True)
                    elif html_message and len(body) > 5:
                        new_email = Email.objects.create(subject=subject, bcc=bcc, cc=cc, body=body, sent_by=request.user, is_html=True)
                    else:
                        new_email = Email.objects.create(subject=subject, bcc=bcc, cc=cc, body=body, sent_by=request.user)
                    new_email.is_draft = True
                    new_email.save()

                    if len(body) > 4500 and not new_email.is_html:
                        new_email.delete()
                        messages.error(request, 'Failed to save mail: Mail body should not exceed 4500 characters')
                        return JsonResponse(data={'success':'false',}, status=400)
                    # add all receivers to the new mail
                    for receiver in receivers:
                        new_email.send_to.add(receiver)
                    new_email.save()
                    for file in attached_files:
                        attachment = Attachment.objects.create(file=file, added_by=request.user)
                        attachment.save()
                        new_email.attachments.add(attachment)
                    new_email.save()
                    messages.success(request, 'Email saved as draft')
                    return JsonResponse(data={'success':'true',}, status=200)

                elif len(receivers) == 0:
                    if message_form['subject'] != '':
                        subject = message_form['subject'].title()
                    else:
                        subject = 'No Subject'
                    if message_form['bcc'] != '':
                        bcc = message_form['bcc']
                    else:
                        bcc = None
                    if message_form['cc'] != '':
                        cc = message_form['cc']
                    else:
                        cc = None
                    body = message_form['body']
                    if request.session.test_cookie_worked() and request.user.accepted_cookies and request.session['last_edit_request_email_draft_id']:
                        if Email.objects.filter(sent_by=request.user, is_draft=True, id=request.session['last_edit_request_email_draft_id']).exists():
                            draft = Email.objects.filter(sent_by=request.user, is_draft=True, id=request.session['last_edit_request_email_draft_id']).first()
                            draft.subject = subject
                            draft.bcc = bcc
                            draft.cc = cc
                            draft.body = body
                            draft.save()
                            messages.success(request, "Draft updated")
                            request.session['last_save_request_email_draft_id'] = draft.id
                    elif not request.session.test_cookie_worked():
                        messages.error(request, 'Failed to save draft: Session expired. Please try enabling browser cookies and reload the page')
                    elif not request.user.accepted_cookies:
                        messages.error(request, "Failed to save draft: Please accept cookies. View <a href='{}?cookies'>settings</a> to accept cookies".format(settings_url))
                    else:
                        messages.error(request, 'No email address found')
                    return JsonResponse(data={'success':'false',}, status=200)


        else:
            return JsonResponse(data={'success':'false',}, status=400)



class AjaxDeleteView(View):
    '''Ajax view for deleting email or sms objects'''
    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == "XMLHttpRequest"
        response = {'message': ''}
        if is_ajax:
            payload = json.loads(request.POST['payload'])
            # print(payload)
            object_type = payload['object_type']
            object_list = payload['object_list']

            if object_type and object_type == "sms":
                self.model = TextMessage
            elif object_type and object_type == "email":
                self.model = Email

            if object_list and object_list != []:
                count = 0
                for object_id in object_list:
                    object = get_object_or_404(self.model, id=int(object_id))
                    if object.sent_by == request.user:
                        object.delete()
                        count += 1
                    else:
                        response['message'] = "error"
                        messages.info(request, "Forbidden request! you cannot delete messages sent by other users")
                        return JsonResponse(data=response)

                response['message'] = "success"
                if count > 1 and object_type == "sms":
                    messages.success(request, '{} messages deleted'.format(count))
                elif count == 1 and object_type == "sms":
                    messages.success(request, '{} message deleted'.format(count))

                if count > 1 and object_type == "email":
                    messages.success(request, '{} mails deleted'.format(count))
                elif count == 1 and object_type == "email":
                    messages.success(request, '{} mail deleted'.format(count))
                return JsonResponse(data=response, status=200)
            elif object_list and object_list == []:
                response['message'] = "error"
                messages.info(request, "No message deleted")
                return JsonResponse(data=response)
        else:
            return HttpResponse('Not an ajax request!')

        

class ContactsView(LoginRequiredMixin, View):
    '''View for displaying user contacts'''
    model1= EmailAddress
    model2 = PhoneNumber
    template_name = 'messanger/contacts.html'

    def get(self, request, *args, **kwargs):
        try:
            email_addresses = self.model1.objects.filter(added_by=request.user)
            phone_numbers = self.model2.objects.filter(added_by=request.user)
            context = {
                'email_contacts': email_addresses,
                'phone_contacts': phone_numbers,
            }
            request.session.set_test_cookie()
            return render(request, self.template_name, context)
        except Exception as e:
            print(e)
            return HttpResponse('Something went wrong')
    
    def post(self, request, *args, **kwargs):
        payload, files = request.POST, request.FILES
        phone_number_pattern = re.compile(r'^\+(?:[0-9] ?){10,14}[0-9]$')
        email_pattern = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,6}$')
        user = request.user
        already_exists = set()
        no_of_new_contacts = 0
        no_of_contacts_found = 0
        lines = []
        file_data = None

        if files:
            contact_file = files['contact_file']
            if contact_file:
                if contact_file.name.split('.').pop() not in ['csv', 'txt']:
                    messages.error(request, 'Invalid file type')
                    return redirect('contacts')

                else:
                    file_data = contact_file.read().decode('utf-8')

        if payload:
            new_contacts = payload['new_contact'].split(',')
            object_type = request.GET['object_type']

            if object_type == 'email':
                if new_contacts:
                    for new_contact in new_contacts:
                        if not self.model1.objects.filter(address=new_contact, added_by=user).exists():
                            new_email = self.model1.objects.create(address=new_contact.strip(), added_by=user)
                            new_email.save()
                            no_of_new_contacts += 1
                        else:
                            already_exists.add(new_contact)
                if file_data:
                    lines += re.split(r"[\s,;']", file_data)
                    for line in lines:
                        for email_address in email_pattern.findall(line):
                            no_of_contacts_found += 1
                            if not self.model1.objects.filter(address=email_address, added_by=user).exists():
                                if email_address.strip() != '':
                                    new_email = self.model1.objects.create(address=email_address.strip(), added_by=user)
                                    new_email.save()
                                    no_of_new_contacts += 1
                            else:
                                already_exists.add(email_address.strip())

            elif object_type == 'phone_number':
                if new_contacts:
                    for new_contact in new_contacts:
                        if not self.model2.objects.filter(number=new_contact, added_by=user).exists():
                            new_phone = self.model2.objects.create(number=new_contact.strip(), added_by=user)
                            new_phone.save()
                            no_of_new_contacts += 1
                        else:
                            already_exists.add(new_contact)
                if file_data:
                    lines += re.split(r"[\s,.;\-']", file_data)
                    for line in lines:
                        for phone_number in phone_number_pattern.findall(line):
                            # print(phone_number+'here')
                            no_of_contacts_found += 1
                            if not self.model2.objects.filter(number=phone_number, added_by=user).exists():
                                if phone_number.strip() != '':
                                    new_phone = self.model2.objects.create(number=phone_number.strip(), added_by=user)
                                    new_phone.save()
                                    no_of_new_contacts += 1
                            else:
                                already_exists.add(phone_number.strip())

        if no_of_contacts_found > 1:
            messages.success(request, '{} contacts found in file'.format(no_of_contacts_found))
        elif no_of_contacts_found == 1:
            messages.success(request, '{} contact found in file'.format(no_of_contacts_found))
        elif no_of_contacts_found == 0 and file_data:
            messages.info(request, 'No contacts found in file')

        if already_exists:
            print(already_exists)
            messages.info(request, 'Some contacts already exists')

        if no_of_new_contacts > 1:
            messages.success(request, '{} new contacts added'.format(no_of_new_contacts))
        elif no_of_new_contacts == 1:
            messages.success(request, '{} new contact added'.format(no_of_new_contacts))
        elif no_of_new_contacts == 0:
            messages.info(request, 'No new contact added')

        return redirect('contacts')



class ContactsAjaxView(LoginRequiredMixin, View):
    model1 = PhoneNumber
    model2 = EmailAddress

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == "XMLHttpRequest"
        user = request.user
        if is_ajax:
            try:
                action = request.POST['action']
                payload = json.loads(request.POST['payload'])
            except KeyError:
                return JsonResponse(data={'success': 'false'}, status=200)

            if action == 'update_last_active_tab':
                if request.session.test_cookie_worked():
                    if user.accepted_cookies:
                        request.session['contacts_last_active_tab'] = payload
                        return JsonResponse(data={'success': 'true'}, status=200)
                    else:
                        request.session['contacts_last_active_tab'] = None
                        return JsonResponse(data={'success': 'false'}, status=200)
                else:
                    request.session['contacts_last_active_tab'] = None
                return JsonResponse(data={'success': 'false'}, status=200)

            if action == 'edit':
                object_type = payload['object_type']
                object_id = payload['contact_id']
                new_value = payload['new_value']

                if object_type == 'numbers':
                    number = self.model1.objects.filter(id=object_id, added_by=user).first()
                    number.number = new_value
                    number.save()
                    return JsonResponse(data={'success': 'true'}, status=200)

                elif object_type == 'emails':
                    email = self.model2.objects.filter(id=object_id, added_by=user).first()
                    email.address = new_value
                    email.save()
                    return JsonResponse(data={'success': 'true'}, status=200)

            elif action == 'delete':
                object_type = payload['object_type']
                object_ids = payload['contact_ids']

                if object_type == 'numbers':
                    for object_id in object_ids:
                        number = self.model1.objects.filter(id=object_id, added_by=user).first()
                        if number:
                            try:
                                number.delete()
                            except Exception as e:
                                print(e)
                                pass
                    return JsonResponse(data={'success': 'true'}, status=200)

                elif object_type == 'emails':
                    for object_id in object_ids:
                        email = self.model2.objects.filter(id=object_id, added_by=user).first()
                        if email:
                            try:
                                email.delete()
                            except Exception as e:
                                print(e)
                                pass
                    return JsonResponse(data={'success': 'true'}, status=200)


def get_custom_timesince(date_time: datetime):
    if date_time and isinstance(date_time, datetime):
        now = timezone.now()
        time_delta = max(now - date_time, timedelta(seconds=0))
        time_since = ''
        if time_delta <= timedelta(minutes=1):
            time_since = 'Just Now'
        elif time_delta <= timedelta(days=2) and (now.date().day - date_time.date().day) == 1:
            time_since = f"Yesterday {date_time.strftime('%H:%M')}"
        elif time_delta > timedelta(minutes=1) and time_delta < timedelta(days=1):
            time_since = date_time.strftime('%H:%M')
        elif time_delta >= timedelta(days=1) and time_delta < timedelta(days=7):
            time_since = f"{date_time.strftime('%a %d')} {date_time.strftime('%H:%M')}"
        elif time_delta >= timedelta(days=7) and time_delta < timedelta(days=365):
            time_since = f"{date_time.strftime('%d %b')} {date_time.strftime('%H:%M')}"
        elif time_delta >= timedelta(days=365):
            time_since = date_time.strftime('%d %b %Y')
        return time_since
    return date_time or None


class AjaxSearchView(LoginRequiredMixin, View):
    model1 = Email
    model2 = TextMessage

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        user = request.user

        if is_ajax:
            try:
                object_type = str(request.POST['object_type'])
                search_query = str(request.POST['search_query']).strip()
            except KeyError:
                return JsonResponse(data={'success': 'false'}, status=400)
            search_results = []
            data = {}

            if object_type == 'emails' and search_query:
                search_results += [result.id for result in self.model1.objects.filter(sent_by=user, subject__icontains=search_query)]
                search_results += [result.id for result in self.model1.objects.filter(sent_by=user, body__icontains=search_query)]
                search_results+= [result.id for result in self.model1.objects.filter(sent_by=user, bcc__icontains=search_query)]
                search_results += [result.id for result in self.model1.objects.filter(sent_by=user, cc__icontains=search_query)]
                search_results = self.model1.objects.filter(id__in=search_results, sent_by=user).order_by(Lower('subject'), '-date_sent', '-date_created')
                for result in search_results:
                    if not result.is_html:
                        data[f'id-{result.id}'] = {
                            'subject': result.subject,
                            's_body': ' '.join( result.body.split()[:int( min(15, math.ceil(len(result.body.split()) * 0.75) ) )] )+'...',
                            'date': get_custom_timesince(result.date_sent or result.date_created),
                        }
                    else:
                        data[f'id-{result.id}'] = {
                            'subject': result.subject,
                            's_body': 'HTML message',
                            'date': get_custom_timesince(result.date_sent or result.date_created),
                        }

            elif object_type == 'sms' and search_query:
                search_results += [result.id for result in self.model2.objects.filter(sent_by=user, message__icontains=search_query)]
                search_results = self.model2.objects.filter(id__in=search_results, sent_by=user).order_by(Lower('message'), '-date_sent', '-date_created')
                for result in search_results:
                    data[f'id-{result.id}'] ={
                        'body': ' '.join( result.message.split()[:int( min(20, math.ceil(len(result.message.split()) * 0.75) ) )] )+'...',
                        'date': get_custom_timesince(result.date_sent or result.date_created),
                    } 
            if data:
                return JsonResponse(data={'success': 'true', 'data': data}, status=200)
            return JsonResponse(data={'success': 'false'}, status=200)
                