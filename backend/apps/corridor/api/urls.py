from __future__ import annotations

from django.urls import path

from .views import MatchedDiasporaMentorListView, RegisterDiasporaMentorView

urlpatterns = [
    path("mentors/matched/", MatchedDiasporaMentorListView.as_view(), name="corridor-matched-mentors"),
    path("mentors/", RegisterDiasporaMentorView.as_view(), name="corridor-register-mentor"),
]
