from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from .forms import UserRegistrationForm
from django.views.generic import View
from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
# from messanger.models import EmailAddress, PhoneNumber, TextMessage, Email, Attachment, BlackListedWord
from .models import EmailProfile, MessageProfile, CreditPackage, Purchase
from messanger.models import BlackListedWord
import json, re, logging, time, requests
from django.db.utils import IntegrityError
from django.utils import timesince, timezone
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from coinbase_commerce.client import Client
from django.conf import settings
from .models import encrypt, decrypt
from coinbase_commerce.client import Client
from coinbase_commerce.error import SignatureVerificationError, WebhookInvalidPayload
from coinbase_commerce.webhook import Webhook
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .signals import DEFAULT_PRICES, BLACK_LISTED_WORDS





CustomUser = get_user_model()


class UserRegisterView(UserPassesTestMixin, View):
    model = CustomUser
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = 'privacy'

    def test_func(self):
        if self.request.user.is_authenticated:
            return False
        return True

    def get(self, request, *args, **kwargs):
        request.session.set_test_cookie()
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        username = self.request.POST['username']
        password = self.request.POST['password1']
        secret_q = self.request.POST['pass_question']
        q_ans = self.request.POST['pass_ans']
        if username.strip().lower() in password.lower():
            messages.error(request, 'Unable to complete user registration!')
            messages.info(request, "Password cannot contain your username")
            return render(request, self.template_name)
        r_form = self.form_class(self.request.POST)

        if request.session.test_cookie_worked():
                print('Can use cookie')
                request.session.delete_test_cookie()

        if r_form.is_valid():
            new_user = r_form.save(commit=False)
            # validates secret question and answer
            if secret_q.strip() != '' and q_ans.strip() != '':
                if secret_q.strip().lower().startswith(('when', 'where', 'who', 'how', 'what')):
                    new_user.secret_question = secret_q.strip().lower()
                    new_user.secret_ans = q_ans.strip().lower()
                else:
                    messages.error(request, 'Unable to complete user registration!')
                    messages.info(request, "Secret question should start with an interrogative pronoun e.g 'What is my best food?'")
                    return render(request, self.template_name)
            else:
                messages.error(request, 'Unable to complete user registration!')
                if secret_q.strip() == '':
                    messages.info(request, "Provide a secret question")
                elif secret_q.strip() != '' and q_ans.strip() == '':
                    messages.info(request, "Give an answer to your secret question")
                elif secret_q.strip() == '' and q_ans.strip() == '':
                    messages.info(request, "A secret question and answer must be provided")
                return render(request, self.template_name)
            new_user.can_send = True
            new_user.can_use_default = True
            new_user.save()
            login(request, new_user)
            messages.success(request, "Welcome {}, Your account was created successfully".format(r_form.cleaned_data.get('username')))
            messages.info(request, 'Please save you user ID! You might require it to fix account related issues.')
            return redirect(self.success_url)

        else:
            for error_msg in r_form.errors.values():
                if error_msg:
                    error_msg = error_msg[0]
                    error_msg = error_msg.replace('Custom', '')
                    error_msg = error_msg.replace('user', 'User')
                    error_msg = error_msg.replace('Username', 'username')
                    messages.error(request, error_msg)
            return render(request, self.template_name)   


class ForgotPasswordView(UserPassesTestMixin, View):
    model = CustomUser
    def test_func(self):
        if self.request.user.is_authenticated:
            return False
        return True

    def get(self, request, *args, **kwargs):
        return render(request, 'users/forgot_password.html')

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if is_ajax:
            user_id = request.POST['user_id']
            if self.model.objects.filter(user_idno=user_id).exists():
                user = self.model.objects.get(user_idno=user_id)
                question = str(user.secret_question).capitalize() + '?'
                return JsonResponse({'status': 'success', 'question': question}, status=200)
            else:
                return JsonResponse({'status': 'error'}, status=200)

        else:
            user_id = request.POST['user_id']
            q_ans = request.POST['q_ans']
            if self.model.objects.filter(user_idno=user_id, secret_ans=q_ans.strip().lower()).exists():
                user = self.model.objects.filter(user_idno=user_id, secret_ans=q_ans.strip().lower())[0]
                login(request, user)
                return redirect('reset-password', user.id)
            else:
                messages.error(request, 'Incorrect answer! Try again')
                return redirect('forgot-password')


class ResetPasswordView(LoginRequiredMixin, View):
    model = CustomUser

    def get(self, request, *args, **kwargs):
        user = self.get_object()
        if user:
            return render(request, 'users/reset_password.html', {'user': user})
        return HttpResponse('User not found', status=404)

    def post(self, request, *args, **kwargs):
        password1 = request.POST['password']
        password2 = request.POST['password2']
        user = self.get_object()
        if not user:
            return HttpResponse('User not found', status=404)
        if user and password1 and password2 and password1 == password2:
            user.set_password(password1)
            user.save()
            logout(request)
            messages.success(request, 'Password reset successful!')
            return redirect('login')
        elif not password1 or not password2:
            messages.error(request, 'Password cannot be empty')
            return redirect('reset-password', user.id)
        elif password1 != password2:
            messages.error(request, 'Passwords do not match')
            return redirect('reset-password', user.id)

    def get_object(self):
        try:
            return self.model.objects.get(id=self.kwargs.get('pk'))
        except self.model.DoesNotExist or Exception:
            return None


class LoginView(UserPassesTestMixin, View):
    '''LoginView is a class based view that handles the login process'''
    template_name = 'users/login.html'
    
    def test_func(self):
        if self.request.user.is_authenticated:
            return False
        return True

    def get(self, request, *args, **kwargs):
        request.session.set_test_cookie()
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if request.session.test_cookie_worked():
                print('Can use cookie')
            if self.request.GET.get('next'):
                return redirect(self.request.GET.get('next')) 
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password")
        return render(request, self.template_name)


class LogoutView(View):
    '''LogoutView is a class based view that handles the logout process'''
    def get(self, request, **kwargs):
        request.user.rejected_cookies = False
        request.user.save()
        logout(request)
        return redirect('home')
    
    def post(self, request, **kwargs):
        return HttpResponse(status=403)


class UserDeleteView(UserPassesTestMixin, LoginRequiredMixin, View):
    '''View for deleting user account'''
    model = CustomUser
    success_url = 'register'

    def get(self, request, *args, **kwargs):
        user = self.request.user
        user.delete()
        messages.success(request, "Account deleted successfully")
        return redirect(self.success_url)        

    def test_func(self):
        return self.request.user.is_authenticated

class AcceptOrDeclineCookie(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            if request.POST['choice'] == 'accept':
                user.accepted_cookies = True
                user.rejected_cookies = False
                user.save()
            elif request.POST['choice'] == 'decline':
                user.accepted_cookies = False
                user.rejected_cookies = True
                user.save()
        else: 
            pass
        return HttpResponse(status=200)

@login_required
def TOSView(request, *args, **kwargs):
    if request.method == 'GET':
        user = request.user
        try:
            if request.GET['action'] == 'accept':
                user.accepted_pp = True
                user.save()
            elif request.GET['action'] == 'decline':
                user.accepted_pp = False
                user.save()
            if timesince.timesince(user.date_joined) > '30 minutes':
                return redirect('privacy')
            return redirect('settings')
        except KeyError as e:
            pass
        return render(request, 'users/tos.html')




def process_purchase(credits, price, user_id=None, username=None):
    '''Processes a purchase request and returns a coinbase charge'''
    if not credits or not price:
        raise ValueError('Credits and price are required')
    client = Client(api_key=settings.COINBASE_COMMERCE_API_KEY)
    domain_url = settings.POSTMAN_DOMAIN_URL
    product = {
        'name': '{} message credits'.format(credits),
        'description': 'Buy {} credits for ${}'.format(credits, price),
        'local_price': {
            'amount': '{}'.format(price),
            'currency': 'USD'
        },
        'metadata': {
            'customer_id': user_id,
            'customer_username': username,
        },
        'pricing_type': 'fixed_price',
        'redirect_url': domain_url + reverse('success-purchase'),
        'cancel_url': domain_url + reverse('failed-purchase'),
    }
    try:
        charge = client.charge.create(**product)
        return charge
    except Exception as e:
        print(e)
    return None

    
@login_required
def PurchaseView(request, *args, **kwargs):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        try:
            user = CustomUser.objects.get(id=request.user.id)
        except CustomUser.DoesNotExist:
            messages.error(request, 'Invalid request: User not found!')
            return JsonResponse({'status': 'error'}, status=200)
        payload = json.loads(request.POST['payload'])
        action = request.POST['action']
        total_price = 0
        total_amount = 0
        packages_= []
        for amount, units in payload.items():
            try:
                package = CreditPackage.objects.get(amount=int(amount))
                if int(units) > 0:
                    packages_.append(package)
                total_price += package.price * int(units)
                total_amount += int(amount) * int(units)
            except CreditPackage.DoesNotExist or CreditPackage.MultipleObjectsReturned:
                pass
        if action == 'process_data':
            return JsonResponse({'price': total_price, 'amount': total_amount, 'status': 'success'}, status=200)
        elif action == 'purchase':
            purchase = Purchase.objects.create(user=user, amount=total_amount, price=total_price)
            for package in packages_:
                purchase.credit_packages.add(package)
            purchase.save()
            try:
                charge = process_purchase(purchase.amount, purchase.price, user.user_idno, user.username)
            except Exception as e:
                print(e)
                return JsonResponse({'status': 'error'}, status=200)
            if charge:
                purchase.charge_id = charge.id
                purchase.save()
                key = str(user.user_idno) * 4
                key = key[:32]
                charge_id = str(encrypt(key, charge.id))
                return JsonResponse({'status': 'success', 'charge_id': charge_id}, status=200)
            else:
                messages.error(request, 'Failed to initiate purchase. Might be your internet connectivity')
                return JsonResponse({'status': 'error'}, status=200)

    elif request.method == 'GET':
        action= request.GET.get('action')
        purchase_id = request.GET.get('purchase_id')
        if action == 'cancel':
            try:
                purchase = Purchase.objects.get(sid=purchase_id)
                url = "https://api.commerce.coinbase.com/charges/{}/cancel".format(purchase.charge_id)
                headers = {"accept": "application/json"}
                response = requests.post(url, headers=headers)
                time.sleep(2)
                if response and response.status_code == 200:
                    purchase.delete()
                    messages.success(request, 'Purchase cancelled')
            except Purchase.DoesNotExist or Exception as e:
                print(e)
                pass          
            return redirect('settings')


def ConfirmPurchaseView(request, *args, **kwargs):
    if request.method == 'GET':
        try:
            charge_id = request.GET['charge_id']
            key = str(request.user.user_idno) * 4
            key = key[:32]
            charge_id = decrypt(key, charge_id)
        except Exception as e:
            print(e)
            return HttpResponse(status=403)
        try:
            purchase = Purchase.objects.get(charge_id=charge_id)
        except Purchase.DoesNotExist:
            return HttpResponse(status=403)
        url = "https://api.commerce.coinbase.com/charges/{}".format(charge_id)
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers)
        charge = response.json()['data']
        return render(request, 'users/confirm_purchase.html', {'charge': charge, 'purchase': purchase})
    else:
        return HttpResponse(status=403)

def test_func1(user):
    if user.is_authenticated and not user.is_privileged:
        recent_purchase = Purchase.objects.filter(user=user).order_by('-date_created').first()
        if recent_purchase:
            if timesince(recent_purchase.date_created) < '1 hour 10 minutes':
                return True
    return False

@user_passes_test(test_func1)
def SuccessPurchaseView(request, *args, **kwargs):
    if request.method == 'GET':
        messages.success(request, 'Purchase successful! It may take a few minutes for the credits to reflect in your account')
        purchase = Purchase.objects.filter(user=request.user).order_by('-date_created').first()
        purchase.success = True
        purchase.save()
        return render(request, 'users/purchase_success.html', {'purchase': purchase})
    else:
        return HttpResponse(status=403)


@user_passes_test(test_func1)
def FailedPurchaseView(request, *args, **kwargs):
    if request.method == 'GET':
        messages.error(request, 'Purchase failed! Please try again')
        purchase = Purchase.objects.filter(user=request.user).order_by('-date_created').first()
        return render(request, 'users/purchase_failure.html', {'purchase': purchase})
    else:
        return HttpResponse(status=403)


with open(settings.STATIC_ROOT + '/images/accounts.json', 'r') as f:
    account = json.load(f)[0]

@csrf_exempt
@require_http_methods(['POST'])
def CoinbaseWebhook(request):
    '''Webhook for coinbase'''
    logger = logging.getLogger(__name__)

    request_data = request.body.decode('utf-8')
    request_sig = request.headers.get('X-CC-Webhook-Signature', None)
    webhook_secret = settings.COINBASE_COMMERCE_WEBHOOK_SHARED_SECRET

    try:
        event = Webhook.construct_event(request_data, request_sig, webhook_secret)

        # List of all Coinbase webhook events:
        # https://commerce.coinbase.com/docs/api/#webhooks
        user_id = event['data']['metadata']['customer_id']
        username = event['data']['metadata']['customer_username']
        charge_id = event['data']['id']
        charge_code = event['data']['code']

        if event['type'] == 'charge:created':
            time.sleep(10)
            try:
                user = CustomUser.objects.get(user_idno=user_id)
                if Purchase.objects.filter(user=user, charge_id=charge_id).exists():
                    logger.info('New charge created')
                else:
                    # sends a request to coinbase to cancel the charge
                    url = "https://api.commerce.coinbase.com/charges/{}/cancel".format(charge_id)
                    headers = {"accept": "application/json"}
                    response = requests.post(url, headers=headers)
                    time.sleep(2)
                    # sends an email to notify me of an unregistered charge
                    connection = EmailBackend(host="smtp.gmail.com", port=587, username=account['auth_user'], password=account['auth_pass'], use_tls=True)
                    email = EmailMessage(
                        subject="Threat - Unregistered Purchase Charge Detected (Postman)",
                        body='Charge ID: '+ str(charge_id) + '\n' + '\n' + 'Charge details: '+ str(event) + '\n' + '\n' + 'Cancel Request Response: ' + response.text + '\n' + '\n' + str(timezone.now()),
                        from_email=account['auth_user'],
                        to=settings.MANAGERS,
                    )
                    try:
                        connection.send_messages([email])
                    except Exception as e:
                        print(e)
            except Exception as e:
                print(e)

        elif event['type'] == 'charge:confirmed':
            logger.info('Payment confirmed.')
            try:
                user = CustomUser.objects.get(user_idno=user_id)
            except CustomUser.DoesNotExist:
                logger.error('User not found.')
                return HttpResponse(status=400)

            try:
                purchase = Purchase.objects.get(charge_id=charge_id)
                if purchase.is_closed:
                    logger.error('Purchase already closed.')
                    return HttpResponse(status=400)
               
                if purchase.user != user:
                    logger.error('Purchase does not belong to user.')
                    return HttpResponse(status=400)
    
            except Purchase.DoesNotExist:
                logger.error('Purchase not found.')
                return HttpResponse(status=400)
            user.message_credit += purchase.amount
            purchase.is_closed = True
            purchase.order_code = charge_code
            purchase.save()
            user.save()
            return HttpResponse(status=200)
        elif event['type'] == 'charge:pending':
            logger.info('Payment pending.')

        elif event['type'] == 'charge:failed':
            logger.info('Payment failed.')
            try:
                user = CustomUser.objects.get(user_idno=user_id)
            except CustomUser.DoesNotExist:
                logger.error('User not found.')
                return HttpResponse(status=400)

            try:
                purchase = Purchase.objects.get(charge_id=charge_id)
                if purchase.is_closed:
                    logger.error('Purchase already closed.')
                    return HttpResponse(status=400)
                elif purchase.user != user:
                    logger.error('Purchase does not belong to user.')
                    return HttpResponse(status=400)
    
            except Purchase.DoesNotExist:
                logger.error('Purchase not found.')
                return HttpResponse(status=400)
            purchase.is_closed = True
            purchase.success = False
            purchase.order_code = charge_code
            purchase.save()
            return HttpResponse(status=200)

    except (SignatureVerificationError, WebhookInvalidPayload) as e:
        return HttpResponse(e, status=400)

    logger.info(f'Received event: id={event.id}, type={event.type}')
    return HttpResponse('ok', status=200)



class AddDefaultItemsView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_admin

    def get(self, request, *args, **kwargs):
        for credit, price in DEFAULT_PRICES.items():
            if not CreditPackage.objects.filter(amount=credit).exists():
                try:
                    package = CreditPackage.objects.create(amount=credit, price=price)
                    package.save()
                except Exception:
                    pass
        messages.success(request, 'Default packages added successfully')
        for word, replacement in BLACK_LISTED_WORDS.items():
            if not BlackListedWord.objects.filter(word=word).exists():
                try:
                    word = BlackListedWord.objects.create(word=word, replacement_word=replacement)
                    word.save()
                except Exception:
                    pass
        messages.success(request, 'Default blacklisted words added successfully')
        return redirect('settings')



class SettingsView(LoginRequiredMixin, UserPassesTestMixin, View):
    '''Handles the modification of user settings'''
    model1 = EmailProfile
    model2 = MessageProfile

    def test_func(self):
        if self.request.user.is_active:
            return True
        return False

    def get(self, request, *args, **kwargs):
        user = CustomUser.objects.get(id=request.user.id)
        packages = CreditPackage.objects.all()
        return render(request, 'messanger/settings.html', {'user': user, 'packages': packages})
 
    def post(self, request, *args, **kwargs):
        user = CustomUser.objects.get(id= request.user.id)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        phone_number_pattern = re.compile(r'^\+(?:[0-9] ?){10,14}[0-9]$')
        email_pattern = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,6}$')
        if is_ajax:
            payload = request.POST
            emailing_profiles = json.loads(payload['emailing_profiles'])
            messaging_profiles = json.loads(payload['messaging_profiles'])
            wants_random = json.loads(payload['wants_random'])
            wants_history = json.loads(payload['wants_history'])
            wants_default = json.loads(payload['wants_default'])
            accepted_cookies = json.loads(payload['accepted_cookies'])

            #apply settings
            user.wants_random = wants_random
            user.wants_history = wants_history
            user.wants_default = wants_default
            user.accepted_cookies = accepted_cookies
            user.save()

            for profile_name, is_active in emailing_profiles.items():
                try:
                    email_profile = self.model1.objects.filter(owned_by=user, email=profile_name)[0]
                    email_profile.is_active = bool(is_active)
                    email_profile.save()
                except self.model1.DoesNotExist:
                    pass

            for profile_name, is_active in messaging_profiles.items():
                try:
                    message_profile = self.model2.objects.filter(owned_by=user, number=profile_name)[0]
                    message_profile.is_active = bool(is_active)
                    message_profile.save()
                except self.model2.DoesNotExist:
                    pass
            return JsonResponse(data={"success":'true'}, status=200)

        else:
            form_data = request.POST
            if 'number' and 'api_key' in form_data.keys():
                number = form_data['number']
                if phone_number_pattern.match(number) is None:
                    messages.error(request, "Invalid phone number")
                    return redirect('settings')
                api_key = form_data['api_key']
                account_sid = form_data['account_sid']
                provider = form_data['provider']
                try:
                    if account_sid != '':
                        message_profile = self.model2.objects.create(owned_by=user, number=number, api_key=api_key, account_sid=account_sid, api_provider=provider)    
                    else:
                        message_profile = self.model2.objects.create(owned_by=user, number=number, api_key=api_key, api_provider=provider)
                    message_profile.save()
                    messages.success(request, 'Profile added successfully')
                except IntegrityError:
                    messages.error(request, 'A profile with this number already exists')

                except Exception as e:
                    print(e)
                    pass
            elif 'email' and 'app_pass' in form_data.keys():
                email = form_data['email']
                if email_pattern.match(email) is None:
                    messages.error(request, "Invalid email address!")
                    return redirect('settings')
                app_pass = form_data['app_pass']
                custom_host = form_data['custom_host']

                try:
                    if custom_host != '':
                        email_profile = self.model1.objects.create(owned_by=user, email=email, app_pass=app_pass, host=custom_host)
                    else:
                        email_profile = self.model1.objects.create(owned_by=user, email=email, app_pass=app_pass)
                    email_profile.save()
                    try:
                        connection = EmailBackend(host=email_profile.host, port=email_profile.port, username=email_profile.email, password=app_pass, use_tls=email_profile.use_tls, use_ssl=email_profile.use_ssl)
                        email = EmailMessage(
                                    subject='Postman email verification',
                                    body='<h3>Postman</h3><p>This is a test email to verify that your email profile is valid</p>',
                                    from_email=email_profile.email,
                                    to=[email_profile.email,],
                                    connection=connection,
                                )
                        email.content_subtype = 'html'
                        email.send()
                    except Exception as e:
                        print(e)
                        if 'application-specific password required' in str(e).lower():
                            messages.error(request, 'Invalid email profile. Please input an application-specific password and try again')
                        elif e.args[0] > 400:
                            messages.error(request, 'Invalid email profile. Please check your credentials and try again')
                        email_profile.delete()
                        return redirect('settings')
                    messages.success(request, 'Profile added successfully')

                except IntegrityError:
                    messages.error(request, 'A profile with this email already exists')

                except Exception as e:
                    print(e)
                    pass
            return redirect('settings')

