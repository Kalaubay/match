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
from django.db.models import Avg

# Модельдерді импорттау
from .models import Lesson, LessonProgress, UserActivity, Question, Choice

User = get_user_model()

def get_user_activity_data(user):
    """Қолданушының соңғы 5 апталық белсенділік күнтізбесін дайындайтын көмекші функция"""
    user_activities = UserActivity.objects.filter(user=user).values_list('date', flat=True)
    activities = {act_date for act_date in user_activities if act_date is not None}
    
    today = timezone.now().date()
    
    # base.html-дегі 7 қатарлы (апталық) Heatmap тор көзіне сәйкес келу үшін 
    # аптаның басы мен аяғын дұрыс пішімдеу
    start_date = today - timedelta(days=34 + today.weekday()) 
    end_date = today + timedelta(days=(6 - today.weekday()))
    
    activity_data = []
    curr = start_date
    while curr <= end_date:
        activity_data.append({
            'date': curr,
            'is_active': curr in activities
        })
        curr += timedelta(days=1)
    return activity_data


@login_required
def group_progress(request):
    """Студенттердің сабақтар бойынша жинаған пайыздарын көрсету (Админдерсіз)"""
    
    # 1. Барлық сабақтар тізімі
    lessons = Lesson.objects.all().order_by('order')
    lesson_labels = [f"{lesson.order}-сабақ" for lesson in lessons]

    # 2. ЖҮЙЕДЕГІ СТУДЕНТТЕРДІ АЛУ (Админдерді сүзгіден өткізіп, алып тастаймыз 🚫)
    students = User.objects.filter(is_superuser=False)[:12] 
    
    student_scores_data = []
    total_group_score = 0
    completed_tests_count = 0

    for student in students:
        scores = []
        student_total = 0
        student_passed_lessons = 0
        
        for lesson in lessons:
            progress = LessonProgress.objects.filter(user=student, lesson_order=lesson.order).first()
            score = progress.best_score if progress else 0
            scores.append(score)
            
            if score > 0:
                student_total += score
                student_passed_lessons += 1
                completed_tests_count += 1
        
        # Әр студенттің жеке орташа пайызы
        student_avg = int(student_total / student_passed_lessons) if student_passed_lessons > 0 else 0
        total_group_score += student_avg

        student_scores_data.append({
            'name': student.first_name or student.username,
            'avatar_letter': (student.first_name[0] if student.first_name else student.username[0]).upper(),
            'current_order': student.current_lesson_order,
            'avg_score': student_avg,
            'scores': scores  
        })

    # Топтың жалпы орташа көрсеткіші
    group_average = int(total_group_score / students.count()) if students.count() > 0 else 0

    # Sidebar үшін активтілік күнтізбесі
    activity_data = get_user_activity_data(request.user)

    return render(request, 'group_progress.html', {
        'lesson_labels': json.dumps(lesson_labels),
        'student_scores_data': student_scores_data,
        'group_average': group_average,
        'active_students_count': students.count(),
        'completed_tests_count': completed_tests_count,
        'activity_data': activity_data,
    })

@login_required
def lesson_list(request):
    """Сабақтар тізімі мен прогресс пайызын шығару"""
    activity_data = get_user_activity_data(request.user)
    
    lessons = Lesson.objects.all().order_by('order')
    total_count = lessons.count()
    
    # Қолданушының қазіргі нақты деңгейі (Бастапқыда 1 болады)
    current_order = request.user.current_lesson_order
    
    # Егер қолданушы 1-сабақта тұрса, бірақ бұрын ешқандай сабақты бітірмесе completed_count = 0 болады.
    # Бірақ біз оның өткен сабақтарын нақты базадағы жетістігімен санауымыз керек:
    completed_count = LessonProgress.objects.filter(user=request.user, best_score__gte=70).count()
    
    progress_percent = int((completed_count / total_count) * 100) if total_count > 0 else 0
    
    # Қолданушыға қазір өту керек сабағын анықтау
    current_lesson = lessons.filter(order=current_order).first()
    if not current_lesson and total_count > 0:
        # Егер ол барлық сабақтан асып кетсе, ең соңғы ашық сабақты көрсетеміз
        current_lesson = lessons.last()

    # Әр сабаққа студенттің ең үздік нәтижесін қосып шығу
    for lesson in lessons:
        progress = LessonProgress.objects.filter(user=request.user, lesson_order=lesson.order).first()
        lesson.best_score = progress.best_score if progress else None

    return render(request, 'lesson_list.html', {
        'lessons': lessons,
        'activity_data': activity_data,
        'progress_percent': progress_percent,
        'completed_count': completed_count,
        'total_count': total_count,
        'current_lesson_id': current_lesson.id if current_lesson else None
    })

@login_required
def homework(request):
    return render(request, 'homework.html')

@login_required
def check_test(request, lesson_id):
    """Тестті тексеру және 70%-дан асса келесі сабақты ашу логикасы"""
    if request.method == 'POST':
        lesson = get_object_or_404(Lesson, id=lesson_id)
        questions = lesson.questions.all()
        total_questions = questions.count()
        
        if total_questions == 0:
            return JsonResponse({'status': 'error', 'message': 'Бұл сабаққа тест қосылмаған!'}, status=400)

        correct_answers_count = 0
        for question in questions:
            selected_choice_id = request.POST.get(f'question_{question.id}')
            if selected_choice_id:
                try:
                    choice = Choice.objects.get(id=selected_choice_id, question=question)
                    if choice.is_correct:
                        correct_answers_count += 1
                except Choice.DoesNotExist:
                    continue

        score_percent = int((correct_answers_count / total_questions) * 100)

        # Прогресс жазбасын сақтау
        progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson_order=lesson.order
        )
        
        if score_percent > progress.best_score:
            progress.best_score = score_percent
            progress.save()

        # 70% Шектік мәннен асқанда:
        if score_percent >= 70:
            today_date = timezone.now().date()
            
            activity_exists = UserActivity.objects.filter(user=request.user, date=today_date).exists()
            if not activity_exists:
                try:
                    UserActivity.objects.create(user=request.user, date=today_date)
                except Exception:
                    # Егер басқа қатарлас сұраныс осы секундта жасап үлгерсе, қателікті елемей өтіп кетеміз
                    pass
            
            # Егер оқушы өзінің ең соңғы ашық деңгейіндегі сабақты сәтті тапсырса ғана деңгейін өсіреміз
            if lesson.order == request.user.current_lesson_order:
                next_lesson_exists = Lesson.objects.filter(order=lesson.order + 1).exists()
                if next_lesson_exists:
                    request.user.current_lesson_order = lesson.order + 1
                else:
                    request.user.current_lesson_order = lesson.order + 1
                
                request.user.save(update_fields=['current_lesson_order'])
            
            return JsonResponse({
                'status': 'passed',
                'score': score_percent,
                'best_score': progress.best_score,
                'message': f'Құттықтаймыз! Сіз {score_percent}% жинап, тесттен өттіңіз.'
            })
        else:
            return JsonResponse({
                'status': 'failed',
                'score': score_percent,
                'message': f'Шектік мәннен өте алмадыңыз. Нәтижеңіз: {score_percent}%. (Кемінде 70% қажет)'
            })

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if lesson.order > request.user.current_lesson_order:
        return redirect('lesson_list')

    # Осы сабақтың прогресін алу
    progress = LessonProgress.objects.filter(user=request.user, lesson_order=lesson.order).first()
    best_score = progress.best_score if progress else 0

    # Сабақтың ішкі бетінде де Sidebar-да күнтізбе жанып тұруы керек
    activity_data = get_user_activity_data(request.user)

    return render(request, 'lesson_detail.html', {
        'lesson': lesson,
        'best_score': best_score,
        'activity_data': activity_data,  # Sidebar үшін
    })



def signup_view(request):
    if request.method == 'POST':
        email = request.POST.get('username')
        otp = str(random.randint(100000, 999999))
        
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

        send_mail('Растау коды', f'Код: {otp}', None, [email])
        
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