from __future__ import annotations

from django.urls import path

from .views import ApproveStipendView, MpesaB2CCallbackView

urlpatterns = [
    path("stipends/<uuid:disbursement_id>/approve/", ApproveStipendView.as_view(), name="welfare-stipend-approve"),
    path("callbacks/mpesa-b2c/", MpesaB2CCallbackView.as_view(), name="welfare-mpesa-callback"),
]
