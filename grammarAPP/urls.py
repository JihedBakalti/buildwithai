from django.urls import path
from . import views

app_name = 'grammarAPP'

urlpatterns = [
    path('', views.grammar_helper, name='grammar_helper'),
]

