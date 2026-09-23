from django.urls import path
from . import views

app_name = 'travel'

urlpatterns = [
    path('', views.trip_list, name='home'),
    path('trips/', views.trip_list, name='trip_list'),
    path('trips/create/', views.trip_create, name='trip_create'),
    path('trips/<int:trip_id>/', views.trip_detail, name='trip_detail'),
    path('trips/<int:trip_id>/edit/', views.trip_edit, name='trip_edit'),
    path('trips/<int:trip_id>/delete/', views.trip_delete, name='trip_delete'),
    path('trips/<int:trip_id>/guide/', views.trip_guide, name='trip_guide'),
    path('trips/<int:trip_id>/stops/<int:stop_id>/', views.stop_detail, name='stop_detail'),
    
    # たびしお専用認証
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('register/sent/', views.register_sent_view, name='register_sent'),
    path('activate/<str:uidb64>/<str:token>/', views.activate_view, name='activate'),
    path('activate/success/', views.activation_success_view, name='activation_success'),
    path('resend-activation/', views.resend_activation_view, name='resend_activation'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # API endpoints
    path('api/trips/<int:trip_id>/add-stop/', views.api_add_stop, name='api_add_stop'),
    path('api/trips/<int:trip_id>/reorder-stops/', views.api_reorder_stops, name='api_reorder_stops'),
    path('api/trips/<int:trip_id>/stops/<int:stop_id>/delete/', views.api_delete_stop, name='api_delete_stop'),
    path('api/trips/<int:trip_id>/stops/<int:stop_id>/update-transport/', views.api_update_transport, name='api_update_transport'),
    path('api/trips/<int:trip_id>/stops/<int:stop_id>/photos/upload/', views.api_upload_stop_photo, name='api_upload_stop_photo'),
    path('api/trips/<int:trip_id>/stops/<int:stop_id>/photos/<int:photo_id>/delete/', views.api_delete_stop_photo, name='api_delete_stop_photo'),
    path('api/trips/<int:trip_id>/add-member/', views.api_add_member, name='api_add_member'),
    path('api/trips/<int:trip_id>/members/<int:member_id>/delete/', views.api_delete_member, name='api_delete_member'),
]
