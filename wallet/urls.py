from django.urls import path
from . import views

app_name = 'wallet'
urlpatterns = [
    path('cotacao/', views.quote, name='quote'),
    path('', views.dashboard, name='dashboard'),
    path('gestao/', views.management, name='management'),
    path('gestao/<uuid:public_id>/', views.review, name='review'),
]
