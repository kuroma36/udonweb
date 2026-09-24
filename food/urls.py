from django.urls import path
from . import views

app_name = 'food'

urlpatterns = [
    path('', views.food_list, name='index'),
    path('api/fetch/', views.fetch_news_api, name='api_fetch'),
    path('<int:pk>/', views.food_detail, name='detail'),
]
