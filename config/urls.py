"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('udon/', include('udon.urls')),
    path('travel/', include('travel.urls')),
    path('pomodoro/', include('pomodoro.urls')),
    path('food/', include('food.urls')),
    path('', RedirectView.as_view(url='/udon/', permanent=False)),
    # 旧APIリクエストの互換用リダイレクト
    re_path(r'^api/(?P<path>.*)$', RedirectView.as_view(url='/udon/api/%(path)s', permanent=False)),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
