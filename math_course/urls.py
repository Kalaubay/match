from django.contrib import admin
from django.urls import path
from courses.views import signup_view, verify_otp_view
from django.contrib.auth import views as auth_views
from courses.views import lesson_list, lesson_detail, complete_lesson, group_progress

urlpatterns = [
    path('admin/', admin.site.urls),
    path('signup/', signup_view, name='signup'),
    path('verify/', verify_otp_view, name='verify_otp'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('lessons/', lesson_list, name='lesson_list'),
    path('lesson/<int:lesson_id>/', lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_id>/complete/', complete_lesson, name='complete_lesson'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('group_progress/', group_progress, name='group_progress')
]