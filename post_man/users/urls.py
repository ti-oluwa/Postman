from django.urls import path
from .views import UserDeleteView, SettingsView, AcceptOrDeclineCookie, PurchaseView, ConfirmPurchaseView, SuccessPurchaseView, FailedPurchaseView, CoinbaseWebhook, ResetPasswordView


urlpatterns = [
    path('delete/', UserDeleteView.as_view(), name="delete-user"),
    path('<int:pk>/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('cookie/', AcceptOrDeclineCookie.as_view(), name='use-cookie'),
    path('ajax/purchase', PurchaseView, name='purchase'),
    path('purchase/confirm/', ConfirmPurchaseView, name='confirm-purchase'),
    path('purchase/success/', SuccessPurchaseView, name='success-purchase'),
    path('purchase/failed/', FailedPurchaseView, name='failed-purchase'),
    path('purchase/webhook/coinbase/', CoinbaseWebhook, name='coinbase-webhook')
]