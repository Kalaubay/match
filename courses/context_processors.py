# context_processors.py
from datetime import timedelta
from django.utils import timezone
from .models import UserActivity

def activity_context(request):
    if request.user.is_authenticated:
        activities = UserActivity.objects.filter(user=request.user).values_list('date', flat=True)
        today = timezone.now().date()
        start_date = today - timedelta(days=34)
        start_date -= timedelta(days=start_date.weekday())
        
        activity_data = []
        current_day = start_date
        while current_day <= today:
            activity_data.append({
                'date': current_day,
                'is_active': current_day in activities
            })
            current_day += timedelta(days=1)
        return {'activity_data': activity_data}
    return {'activity_data': []}