from django.urls import path
from .push_service import register_push_subscription, send_test_notification

urlpatterns = [
    path('push/register/', register_push_subscription, name='register_push_subscription'),
    path('push/test/', send_test_notification, name='send_test_notification'),
]