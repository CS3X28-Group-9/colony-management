from .models import Notification


def unread_notifications(request):
    """Context processor to provide unread notification count and recent notifications to all templates."""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            user=request.user, read=False
        ).count()
        recent_notifications = Notification.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:5]
        return {
            "unread_count": unread_count,
            "recent_notifications": recent_notifications,
        }
    return {"unread_count": 0, "recent_notifications": []}
