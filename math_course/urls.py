from django.contrib import admin
from django.urls import path
from django.urls import path, include
from django.contrib.auth import views as auth_views
from courses.views import (
    signup_view, 
    verify_otp_view, 
    lesson_list, 
    lesson_detail, 
    check_test,      # Жаңа қосқан тест тексеру функциямыз
    group_progress
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('_nested_admin/', include('nested_admin.urls')),
    path('signup/', signup_view, name='signup'),
    path('verify/', verify_otp_view, name='verify_otp'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Сабақтар мен Прогресс бағыттары
    path('', lesson_list, name='lesson_list'),
    path('lesson/<int:lesson_id>/', lesson_detail, name='lesson_detail'),
    path('group_progress/', group_progress, name='group_progress'),
    
    # Видео бітірудің орнына енді Тестті тексеру урл-і жұмыс істейді
    path('lesson/<int:lesson_id>/check_test/', check_test, name='check_test'),
]