from django.urls import path
from . import views

app_name = 'foodscan'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/lookup/', views.api_lookup, name='api_lookup'),
    path('api/register/', views.api_register, name='api_register'),
    path('api/history/', views.api_history, name='api_history'),
]
