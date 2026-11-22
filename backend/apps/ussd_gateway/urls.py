from __future__ import annotations

from django.urls import path

from .views import UssdCallbackView

urlpatterns = [
    path("callback/", UssdCallbackView.as_view(), name="ussd-callback"),
]
