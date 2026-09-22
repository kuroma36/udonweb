from django.urls import path
from . import views

app_name = 'foodlog'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/day/', views.api_day, name='api_day'),
    path('api/meal/add/', views.api_add_meal, name='api_add_meal'),
    path('api/meal/delete/', views.api_delete_meal, name='api_delete_meal'),
    path('api/search/', views.api_search_foods, name='api_search_foods'),
    path('api/profile/', views.api_update_profile, name='api_update_profile'),
    path('api/udon/recent/', views.api_udon_recent, name='api_udon_recent'),
]
