from django.urls import path
from . import views

app_name = 'udon'

urlpatterns = [
    path('', views.home, name='home'),
    path('trips/', views.trip_list, name='trip_list'),
    path('trips/create/', views.trip_create, name='trip_create'),
    path('trips/<int:trip_id>/', views.trip_map, name='trip_map'),
    path('trips/<int:trip_id>/edit/', views.trip_edit, name='trip_edit'),
    path('trips/<int:trip_id>/delete/', views.trip_delete, name='trip_delete'),
    path('trips/<int:trip_id>/shops/<int:shop_id>/', views.shop_detail, name='shop_detail_in_trip'),
    path('trips/<int:trip_id>/shops/<int:shop_id>/review/', views.review_create, name='review_create_in_trip'),
    
    path('shops/', views.shop_list, name='shop_list'),
    path('shops/<int:shop_id>/', views.shop_detail, name='shop_detail'),
    path('shops/<int:shop_id>/review/', views.review_create, name='review_create'),
    path('shops/<int:shop_id>/photos/upload/', views.shop_photo_upload, name='shop_photo_upload'),
    path('trips/<int:trip_id>/shops/<int:shop_id>/photos/upload/', views.shop_photo_upload, name='shop_photo_upload_in_trip'),
    
    # AJAX / REST APIs
    path('api/trips/<int:trip_id>/reorder-stops/', views.api_reorder_stops, name='api_reorder_stops'),
    path('api/trips/<int:trip_id>/add-stop/', views.api_add_stop, name='api_add_stop'),
    path('api/trips/<int:trip_id>/stops/<int:stop_id>/delete/', views.api_delete_stop, name='api_delete_stop'),
    path('api/trips/<int:trip_id>/add-member/', views.api_add_member, name='api_add_member'),
    path('api/trips/<int:trip_id>/members/<int:member_id>/delete/', views.api_delete_member, name='api_delete_member'),
    path('api/reviews/<int:review_id>/delete/', views.api_delete_review, name='api_delete_review'),
    path('api/reviews/<int:review_id>/delete-photo/', views.api_delete_review_photo, name='api_delete_review_photo'),
    path('api/reviews/<int:review_id>/like/', views.api_toggle_review_like, name='api_toggle_review_like'),
    path('api/reviews/<int:review_id>/comments/', views.api_create_review_comment, name='api_create_review_comment'),
    path('api/comments/<int:comment_id>/delete/', views.api_delete_review_comment, name='api_delete_review_comment'),
    path('api/photos/<int:photo_id>/delete/', views.api_delete_shop_photo, name='api_delete_shop_photo'),
    path('api/notifications/', views.api_get_notifications, name='api_get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.api_mark_notification_read, name='api_mark_notification_read'),
    path('api/notifications/read-all/', views.api_mark_all_notifications_read, name='api_mark_all_notifications_read'),
    path('api/shops/<int:shop_id>/favorite/', views.api_toggle_shop_favorite, name='api_toggle_shop_favorite'),
    path('api/shops/create-from-place/', views.api_create_shop_from_place, name='api_create_shop_from_place'),
    path('api/shops/search/', views.api_search_shops, name='api_search_shops'),
    
    # Auth & Profile
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('login/', views.login_view, name='login'),
    path('guest/', views.guest_mode, name='guest_mode'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
]
