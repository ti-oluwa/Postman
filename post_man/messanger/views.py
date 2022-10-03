from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.utils import IntegrityError
from users.models import EmailProfile, MessageProfile
from .models import EmailAddress, PhoneNumber, TextMessage, Email, Attachment, BlackListedWord
from django.http import HttpResponse, JsonResponse
import json, mimetypes, os, re, time
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.encoding import smart_str
from django.contrib.auth import get_user_model

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
        object_type = kwargs['object_type']
        object_id = kwargs['pk']

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





class RetryView(LoginRequiredMixin, UserPassesTestMixin, View):
    '''Handles requests related to the retrying mails or sms'''
    model1 = TextMessage
    model2 = Email
    
    def get(self, request, *args, **kwargs):
        object_id = self.request.GET.get('pk')
        object_type = self.request.GET.get('type')
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
        object_id = self.request.GET.get('pk')
        object_type = self.request.GET.get('type')
        if object_type == 'sms':
            if self.request.user == self.model1.objects.get(id=object_id).sent_by and self.request.user.can_send:
                return True
            return False
        elif object_type == 'email':
            if self.request.user == self.model2.objects.get(id=object_id).sent_by and self.request.user.can_send:
                return True
            return False


class DownloadView(LoginRequiredMixin, UserPassesTestMixin,View):
    model = Email

    def get(self, request, *args, **kwargs):
        object_id = self.request.GET.get('pk')
        attachment_id = self.request.GET.get('file_id')
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
        
        if is_ajax:
            payload, files = json.loads(request.POST['payload']), request.FILES
            add_form = payload['addFormData']
            select_form = payload['selectFormData']
            message_form = payload['messageFormData']
            action = payload['action']
            phone_number_pattern = re.compile(r'^\+(?:[0-9] ?){10,14}[0-9]$')
            email_pattern = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,6}$')
            receivers = []
            already_exists = []
            attached_files = []
            new_contacts = 0
            lines = []
            html_message = None

            for key in files.keys():
                if key == 'file':
                    file = files['file']
                    if file.name.endswith('.txt')==False or file.name.endswith('.csv')==False:
                        messages.error(request, 'Invalid file format')
                        if action == 'send_message':
                            return redirect('messages')
                        elif action == 'send_email':
                            return redirect('emails')

                    elif file.size > 1048576:
                        messages.error(request, 'File size too large')
                        if action == 'send_message':
                            return redirect('messages')
                        elif action == 'send_email':
                            return redirect('emails')

                    else:
                        if action == 'send_message':
                            lines = re.split(r"[\s,.;\-']", file.read().decode('utf-8'))
                        else: 
                            lines = re.split(r"[\s,;']", file.read().decode('utf-8'))

            for key in files.keys():
                if key.startswith('attached_file'):
                    attached_files.append(files[key])
                    for file in attached_files:
                        if file.size > 26214400:
                            messages.error(request, f'{file.name} is too large. File size must not exceed 25MB')
                            return JsonResponse(data={'success':'false',}, status=400)
                        else:
                            pass
            for key in files.keys():
                if key.startswith('attached_html_file'):
                    html_file = files[key]
                    html_message = html_file.read().decode('utf-8')

            # for sms
            if action == 'send_message':
                if files and lines != []:
                    for line in lines:
                        for phone_number in phone_number_pattern.findall(line):
                            if PhoneNumber.objects.filter(number=phone_number, added_by=request.user).exists():
                                already_exists.append(phone_number)
                                receivers.append(PhoneNumber.objects.get(number=phone_number))
                            else:
                                registered_number = PhoneNumber.objects.create(number=phone_number, added_by=request.user)
                                registered_number.save()
                                new_contacts += 1
                                receivers.append(registered_number)

                if receivers == [] and 'file' in files.keys():
                    messages.error(request, 'No phone number found in file')
                elif receivers != [] and files:
                    if len(receivers) > 1:
                        messages.info(request, f'{len(receivers)} phone numbers found in {file.name}')
                    else:
                        messages.info(request, f'{len(receivers)} phone number found in {file.name}')
                
                if add_form['phone_numbers'] != '':
                    for phone_number in add_form['phone_numbers'].split(','):
                        if PhoneNumber.objects.filter(number=phone_number, added_by=request.user).exists():
                            already_exists.append(phone_number)
                            receivers.append(PhoneNumber.objects.get(number=phone_number))
                        else:
                            registered_number = PhoneNumber.objects.create(number=phone_number, added_by=request.user)
                            registered_number.save()
                            new_contacts += 1
                            receivers.append(registered_number)
                if new_contacts > 0:
                    if new_contacts > 1:
                        messages.success(request, f'{new_contacts} new phone numbers added')
                    else:
                        messages.success(request, f'{new_contacts} new phone number added')

                if already_exists != [] and len(already_exists) < 4:
                    self.feedback['messages'].append(f'{", ".join(already_exists)} already exists')
                    messages.info(request, f'{", ".join(already_exists)} already exists')

                elif already_exists != [] and len(already_exists) >= 4:
                    messages.info(request, f'{len(already_exists)} phone numbers already exists')

                if select_form['all_contacts'] == 'true':
                    receivers += [phone_number for phone_number in PhoneNumber.objects.filter(added_by=request.user)]

                elif select_form['selected_contacts'] != [] and select_form['all_contacts'] != 'true':
                    receivers += [phone_number for phone_number in PhoneNumber.objects.filter(number__in=select_form['selected_contacts'])]


                if message_form['message'] and receivers != []:
                    message = message_form['message']
                    if len(message) > 160:
                        messages.error(request, 'Failed to send message: SMS should not exceed 160 characters')
                        return JsonResponse(data={'success':'false',}, status=400)
                    message_list = re.split(r"[\s,.;\-\?\!\(\)\:~'\[\]\{\}&_@#\*\^\>\<]", message.lower())
                    black_listed_words = [bad_word.word.lower() for bad_word in BlackListedWord.objects.all()]
                    bad_words = [word for word in message_list if word.lower() in black_listed_words]
                    if bad_words != []:
                        if len(bad_words) == 1:
                            messages.error(request, f'Failed to send message: {", ".join(bad_words)} is not allowed in message')
                        else:
                            messages.error(request, f'Failed to send message: {", ".join(bad_words)} are not allowed in message')
                        return JsonResponse(data={'success':'false',}, status=400)
                    # create a new message object
                    new_message = TextMessage.objects.create(message=message, sent_by=request.user)
                    new_message.save()
                    # send message to list of receivers and awaits response
                    is_sent, response = new_message.send(receivers)
                    if is_sent:
                        messages.success(request, response)
                        if len(new_message.sent_to.all()) > 1:
                            messages.success(request, f'{len(new_message.sent_to.all())} messages sent')
                        elif len(new_message.sent_to.all()) < 1 and len(new_message.sent_to.all()) != 0:
                            messages.success(request, f'{len(new_message.sent_to.all())} message sent')

                        if len(new_message.sent_to.all()) < len(receivers):
                            diff = len(receivers) - len(new_message.sent_to.all())
                            if diff > 1:
                                messages.info(request, f'{diff} messages failed to send')
                            elif diff == len(receivers):
                                new_message.delete()
                            else:
                                messages.info(request, f'{diff} message failed to send')  
                    
                    else:
                        if len(new_message.sent_to.all()) == 0:
                            new_message.delete()
                        messages.error(request, response)
                        
                    time.sleep(2)
                    return JsonResponse(data={'success':'true',}, status=200)
                elif receivers == []:
                    time.sleep(1)
                    return JsonResponse(data={'success':'false',}, status=400)
        
            # for emails
            elif action == 'send_email':
                if files and lines != []:
                    for line in lines:
                        for email_address in email_pattern.findall(line):
                            if EmailAddress.objects.filter(address=email_address, added_by=request.user).exists():
                                already_exists.append(email_address)
                                receivers.append(EmailAddress.objects.get(address=email_address))
                            else:
                                registered_address = EmailAddress.objects.create(address=email_address, added_by=request.user)
                                registered_address.save()
                                new_contacts += 1
                                receivers.append(registered_address)

                if receivers == [] and 'file' in files.keys():
                    messages.error(request, 'No email address found in file')
                elif receivers != [] and files:
                    if len(receivers) > 1:
                        messages.info(request, f'{len(receivers)} email addresses found in {file.name}')
                    else:
                        messages.info(request, f'{len(receivers)} email address found in {file.name}')

                    
                if add_form['email_addresses'] != '':
                    for email_address in add_form['email_addresses'].split(','):
                        if EmailAddress.objects.filter(address=email_address, added_by=request.user).exists():
                            already_exists.append(email_address)
                            receivers.append(EmailAddress.objects.get(address=email_address))
                        else:
                            registered_address = EmailAddress.objects.create(address=email_address, added_by=request.user)
                            registered_address.save()
                            new_contacts += 1
                            receivers.append(registered_address)
                
                if new_contacts > 0:
                    if new_contacts > 1:
                        messages.success(request, f'{new_contacts} new email addresses added')
                    else:
                        messages.success(request, f'{new_contacts} new email address added')

                if already_exists != [] and len(already_exists) < 4:
                    messages.info(request, f'{", ".join(already_exists)} already exists')

                elif already_exists != [] and len(already_exists) >= 4:
                    messages.info(request, f'{len(already_exists)} email addresses already exists')

                if select_form['all_addresses'] == 'true':
                    receivers += [email_address for email_address in EmailAddress.objects.all()]

                elif select_form['selected_addresses'] != [] and select_form['all_addresses'] != 'true':
                    receivers += [email_address for email_address in EmailAddress.objects.filter(address__in=select_form['selected_addresses'])]

                if message_form and receivers != []:
                    if message_form['subject'] != '':
                        subject = message_form['subject']
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
                    if len(body) > 4500:
                        messages.error(request, 'Failed to send mail: Mail body should not exceed 4500 characters')
                        return JsonResponse(data={'success':'false',}, status=400)
                    message_list = re.split(r"[\s,.;\-\?\!\(\)\:~'\[\]\{\}&_@#\*\^\>\<]", body.lower())
                    black_listed_words = [bad_word.word.lower() for bad_word in BlackListedWord.objects.all()]
                    bad_words = [word for word in message_list if word.lower() in black_listed_words]
                    if bad_words != []:
                        if len(bad_words) == 1:
                            messages.error(request, f'Failed to send message: {", ".join(bad_words)} is not allowed in mails')
                        else:
                            messages.error(request, f'Failed to send message: {", ".join(bad_words)} are not allowed in mails')
                        return JsonResponse(data={'success':'false',}, status=400)
                    # create a new message object
                    if html_message and len(html_message) > 5:
                        new_email = Email.objects.create(subject=subject, bcc=bcc, cc=cc, body=html_message, sent_by=request.user, is_html=True)
                    else:
                        new_email = Email.objects.create(subject=subject, bcc=bcc, cc=cc, body=body, sent_by=request.user)
                    new_email.save()
                    for file in attached_files:
                        attachment = Attachment.objects.create(file=file, added_by=request.user)
                        attachment.save()
                        new_email.attachments.add(attachment)
                        new_email.save()
                    # send mail to list of receivers and awaits response
                    is_sent, response= new_email.send(receivers)
                    if is_sent:
                        messages.success(request, response)
                        if len(new_email.sent_to.all()) > 1:
                            messages.success(request, f'{len(new_email.sent_to.all())} emails sent')
                        elif len(new_email.sent_to.all()) < 1 and len(new_email.sent_to.all()) != 0:
                            messages.success(request, f'{len(new_email.sent_to.all())} email sent')

                        if len(new_email.sent_to.all()) < len(receivers):
                            diff = len(receivers) - len(new_email.sent_to.all())
                            if diff > 1:
                                messages.info(request, f'{diff} emails failed to send')
                            elif diff == 0:
                                new_email.delete()
                            else:
                                messages.info(request, f'{diff} email failed to send')
                        
                    else:
                        if len(new_email.sent_to.all()) == 0:
                            new_email.delete()
                        messages.error(request, response)
                        
                    time.sleep(2)
                    return JsonResponse(data={'success':'true',}, status=200)
                elif receivers == []:
                    time.sleep(1)
                    return JsonResponse(data={'success':'false',}, status=400)

        else:
            return HttpResponse('Not an ajax request')



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

        

