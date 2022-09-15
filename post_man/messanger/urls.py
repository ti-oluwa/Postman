from django.urls import path
from django.views.generic import TemplateView
from .views import (MessageView, AjaxView, EmailView, AjaxDeleteView, RetryView, DownloadView)

urlpatterns = [
    path('', TemplateView.as_view(template_name='messanger/home.html'), name='home'),
    path('messages/', MessageView.as_view(), name='messages'),
    path('mails/', EmailView.as_view(), name='emails'),
    path('send/', AjaxView.as_view(), name='send'),
    path('delete/', AjaxDeleteView.as_view(), name='delete'),
    path('retry/', RetryView.as_view(), name='retry'),
    path('download/attachment/', DownloadView.as_view(), name='download'),
]
