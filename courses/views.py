import random
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Max
from .models import Lesson, LessonProgress, UserActivity

User = get_user_model()

@login_required
def group_progress(request):
    """Оқушылардың апталық графигін оңтайландырылған сұраныспен шығару"""
    today = timezone.now().date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    days_labels = [day.strftime('%d.%m') for day in days]

    # select_related немесе prefetch_related қажет емес, бірақ санды шектейміз
    students = User.objects.all()[:10] 
    chart_data = []

    for student in students:
        student_history = []
        # select_related қолдану арқылы базаға салмақты азайтуға болады
        progress_records = LessonProgress.objects.filter(user=student, date_completed__lte=today)
        
        for day in days:
            # Цикл ішінде .filter().first() жасағанша, Python-да өңдеген жылдамырақ
            day_progress = progress_records.filter(date_completed__lte=day).aggregate(Max('lesson_order'))['lesson_order__max']
            student_history.append(day_progress or 0)
        
        chart_data.append({
            'name': student.first_name or student.username,
            'data': student_history
        })

    return render(request, 'group_progress.html', {
        'days': json.dumps(days_labels),
        'chart_data': chart_data,
    })

@login_required
def lesson_list(request):
    """Сабақтар тізімі мен активтілік торын шығару"""
    # values_list қолдану — жадты үнемдейді
    activities = set(UserActivity.objects.filter(user=request.user).values_list('date', flat=True))
    today = timezone.now().date()
    
    # 1. Күнтізбе диапазонын есептеу
    start_date = today - timedelta(days=34 + today.weekday()) # Бірден дүйсенбіге шығару
    end_date = today + timedelta(days=(6 - today.weekday()))
    
    activity_data = []
    curr = start_date
    while curr <= end_date:
        activity_data.append({
            'date': curr,
            'is_active': curr in activities # Set қолданылғандықтан іздеу өте жылдам
        })
        curr += timedelta(days=1)
    
    # 3. Прогресс
    lessons = Lesson.objects.all().order_by('order')
    total_count = lessons.count()
    current_order = request.user.current_lesson_order
    completed_count = max(0, current_order - 1)
    
    progress_percent = int((completed_count / total_count) * 100) if total_count > 0 else 0
    current_lesson = lessons.filter(order=current_order).first()

    return render(request, 'lesson_list.html', {
        'lessons': lessons,
        'activity_data': activity_data,
        'progress_percent': progress_percent,
        'completed_count': completed_count,
        'total_count': total_count,
        'current_lesson_id': current_lesson.id if current_lesson else None
    })

@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if lesson.order > request.user.current_lesson_order:
        return redirect('lesson_list')

    # get_or_create — артық дубликаттардың алдын алады
    LessonProgress.objects.get_or_create(
        user=request.user,
        lesson_order=lesson.order,
        date_completed=timezone.now().date()
    )

    return render(request, 'lesson_detail.html', {'lesson': lesson})

@login_required
def complete_lesson(request, lesson_id):
    if request.method == 'POST':
        lesson = get_object_or_404(Lesson, id=lesson_id)
        user = request.user
        
        UserActivity.objects.get_or_create(user=user, date=timezone.now().date())

        if lesson.order == user.current_lesson_order:
            user.current_lesson_order += 1
            user.save(update_fields=['current_lesson_order']) # Тек бір бағанды жаңарту жылдамырақ
            
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

def signup_view(request):
    if request.method == 'POST':
        email = request.POST.get('username')
        otp = str(random.randint(100000, 999999))
        
        # Егер пайдаланушы бұрын тіркелген болса, қате бермеуі керек
        user, created = User.objects.get_or_create(
            username=email,
            email=email,
            defaults={
                'first_name': request.POST.get('first_name'),
                'last_name': request.POST.get('last_name'),
                'phone_number': request.POST.get('phone'),
                'is_active': False,
                'otp_code': otp
            }
        )
        
        if not created:
            user.otp_code = otp
            user.set_password(request.POST.get('password'))
            user.save()

        send_mail(
            'Растау коды',
            f'Код: {otp}',
            None, # settings.py-дағы EMAIL_HOST_USER қолданылады
            [email],
            fail_silently=False,
        )
        
        request.session['unverified_user_id'] = user.id
        return redirect('verify_otp')
        
    return render(request, 'signup.html')

def verify_otp_view(request):
    user_id = request.session.get('unverified_user_id')
    if not user_id:
        return redirect('signup')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        if user.otp_code == request.POST.get('otp'):
            user.is_active = True
            user.is_verified = True
            user.save(update_fields=['is_active', 'is_verified'])
            return redirect('login')
        return render(request, 'verify_otp.html', {'error': 'Қате код!'})
            
    return render(request, 'verify_otp.html')