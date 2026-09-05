from django.conf import settings

def google_maps(request):
    return {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }


def notifications(request):
    if hasattr(request, 'user') and request.user.is_authenticated:
        from .models import Notification
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}

