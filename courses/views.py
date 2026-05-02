import random
import json
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from .models import User, LessonProgress
from django.contrib.auth.decorators import login_required
from .models import Lesson
from django.http import JsonResponse
from .models import UserActivity
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model



User = get_user_model()

@login_required
def group_progress(request):
    # Соңғы 7 күннің тізімін жасау
    today = timezone.now().date()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    days_labels = [day.strftime('%d.%m') for day in days]

    # Графикке шығатын оқушылар (мысалы, белсенді 5 оқушы)
    students = User.objects.all()[:5]
    chart_data = []

    for student in students:
        student_history = []
        for day in days:
            # Осы күнге дейінгі ең соңғы бітірген сабағын табамыз
            progress = LessonProgress.objects.filter(
                user=student, 
                date_completed__lte=day
            ).order_by('-lesson_order').first()
            
            student_history.append(progress.lesson_order if progress else 0)
        
        chart_data.append({
            'name': student.first_name,
            'data': student_history
        })

    return render(request, 'group_progress.html', {
        'days': json.dumps(days_labels),
        'chart_data': chart_data,
    })


@login_required
def lesson_list(request):
    activities = UserActivity.objects.filter(user=request.user).values_list('date', flat=True)
    today = timezone.now().date()
    
    # 1. ТОРДЫҢ БАСЫН АНЫҚТАУ (5 апта бұрынғы дүйсенбі)
    start_date = today - timedelta(days=34) 
    start_date -= timedelta(days=start_date.weekday())
    
    # 2. ТОРДЫҢ СОҢЫН АНЫҚТАУ (Осы аптаның жексенбісі)
    # Егер бүгін дүйсенбі (0) болса, жексенбіге дейін тағы 6 күн қосу керек
    # Егер бүгін жексенбі (6) болса, 0 күн қосу керек
    days_to_sunday = 6 - today.weekday()
    end_date = today + timedelta(days=days_to_sunday)
    
    activity_data = []
    current_day = start_date
    
    # ТҮЗЕТУ: Енді цикл 'end_date'-ке (жексенбіге) дейін жүреді
    # Бұл соңғы бағанның (қазіргі аптаның) толық 7 шаршы болуын қамтамасыз етеді
    while current_day <= end_date:
        activity_data.append({
            'date': current_day,
            'is_active': current_day in activities
        })
        current_day += timedelta(days=1)
    
    # 3. ПРОГРЕСС ЖӘНЕ БАСҚА ДЕРЕКТЕР
    lessons = Lesson.objects.all().order_by('order')
    total_count = lessons.count()
    completed_count = max(0, request.user.current_lesson_order - 1)
    
    progress_percent = 0
    if total_count > 0:
        progress_percent = int((completed_count / total_count) * 100)
    
    current_lesson = lessons.filter(order=request.user.current_lesson_order).first()
    current_lesson_id = current_lesson.id if current_lesson else None

    return render(request, 'lesson_list.html', {
        'lessons': lessons,
        'activity_data': activity_data,
        'progress_percent': progress_percent,
        'completed_count': completed_count,
        'total_count': total_count,
        'current_lesson_id': current_lesson_id
    })

@login_required
def lesson_detail(request, lesson_id):
    lesson = Lesson.objects.get(id=lesson_id)
    
    # 1. Рұқсатты тексеру
    if lesson.order > request.user.current_lesson_order:
        return redirect('lesson_list')

    # 2. ГРАФИК ҮШІН ДЕРЕК САҚТАУ
    # Оқушы сабақты ашқанда, бүгінгі күнмен осы сабақтың ретін тіркейміз
    LessonProgress.objects.get_or_create(
        user=request.user,
        lesson_order=lesson.order,
        date_completed=timezone.now().date()
    )

    return render(request, 'lesson_detail.html', {'lesson': lesson})
@login_required
def complete_lesson(request, lesson_id):
    if request.method == 'POST':
        lesson = Lesson.objects.get(id=lesson_id)
        
        # 1. Активтілікті тіркеу (Шаршыны бояу үшін)
        UserActivity.objects.get_or_create(
            user=request.user, 
            date=timezone.now().date()
        )

        # 2. Сабақ деңгейін көтеру
        if lesson.order == request.user.current_lesson_order:
            request.user.current_lesson_order += 1
            request.user.save()
            return JsonResponse({'status': 'success'})
            
        return JsonResponse({'status': 'success'}) # Деңгей көтерілмесе де, видео біткенін растаймыз
        
    return JsonResponse({'status': 'error'}, status=400)

def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username') # Gmail-ді логин ретінде қолданамыз
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        
        # 6 таңбалы код генерациялау
        otp = str(random.randint(100000, 999999))
        
        # Пайдаланушыны базаға сақтау (бірақ әлі активті емес)
        user = User.objects.create_user(
            username=username, 
            email=username,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone,
            password=password,
            is_active=False, # Код енгізбегенше кіре алмайды
            otp_code=otp
        )
        
        # Gmail-ге хат жіберу
        subject = 'Сайтқа тіркелуді растау коды'
        message = f'Сәлеметсіз бе! Тіркелуді аяқтау үшін растау коды: {otp}'
        send_mail(subject, message, 'math_course@gmail.com', [username])
        
        # Кодты тексеру бетіне бағыттау
        request.session['unverified_user_id'] = user.id
        return redirect('verify_otp')
        
    return render(request, 'signup.html')

def verify_otp_view(request):
    if request.method == 'POST':
        entered_code = request.POST.get('otp')
        user_id = request.session.get('unverified_user_id')
        user = User.objects.get(id=user_id)
        
        if user.otp_code == entered_code:
            user.is_active = True
            user.is_verified = True
            user.save()
            return redirect('login') # Тіркелу сәтті, енді кіруге болады
        else:
            return render(request, 'verify_otp.html', {'error': 'Қате код!'})
            
    return render(request, 'verify_otp.html')