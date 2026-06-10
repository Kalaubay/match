from django.contrib import admin
import nested_admin
from django.core.mail import send_mail
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib import messages
from django import forms
from .models import User, Lesson, Question, Choice, UserActivity, LessonProgress

# =====================================================================
# 📨 ПАЙДАЛАНУШЫЛАРҒА ПОЧТА АРҚЫЛЫ ХАБАРЛАМА ЖІБЕРУ БӨЛІМІ
# =====================================================================

class SendEmailForm(forms.Form):
    subject = forms.CharField(
        label="Тақырыбы (Subject)", 
        max_length=255, 
        widget=forms.TextInput(attrs={'style': 'width: 100%; padding: 8px;'})
    )
    message = forms.CharField(
        label="Хабарлама мәтіні", 
        widget=forms.Textarea(attrs={'style': 'width: 100%; height: 200px; padding: 8px;'})
    )

@admin.action(description="Таңдалған қолданушылардың почтасына хабарлама жіберу")
def send_email_to_users(modeladmin, request, queryset):
    # Егер админ "Жіберу" батырмасын басса:
    if 'apply' in request.POST:
        form = SendEmailForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            email_count = 0
            # 🔒 Әр студентке хатты жеке-жеке, өзгелердің почтасын көрсетпей жіберу
            for user in queryset:
                if user.email:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=None,
                        recipient_list=[user.email],  # Әр хатта тек 1 адам болады
                        fail_silently=False,
                    )
                    email_count += 1
            
            if email_count > 0:
                modeladmin.message_user(request, f"Хабарлама {email_count} пайдаланушыға ЖЕКЕ ТҮРДЕ сәтті жіберілді!", messages.SUCCESS)
            else:
                modeladmin.message_user(request, "Таңдалған пайдаланушыларда email мекенжайы көрсетілмеген!", messages.WARNING)
                
            return HttpResponseRedirect(request.get_full_path())

    # Егер админ жаңадан басса, хабарлама жазатын форма парақшасын көрсетеміз
    form = SendEmailForm()
    return render(request, 'admin/send_email_form.html', {
        'users': queryset,
        'form': form,
        'title': 'Почтаға хабарлама дайындау'
    })

# =====================================================================
# 👥 USER (ҚОЛДАНУШЫЛАРДЫ) АДМИНГЕ ТІРКЕУ
# =====================================================================

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'current_lesson_order', 'is_active')
    # Хат жіберу функциясын осы жерге қосамыз
    actions = [send_email_to_users]


# =====================================================================
# 📚 САБАҚТАР МЕН ТЕСТТЕР БӨЛІМІ (NESTED ADMIN)
# =====================================================================

# 1. Жауаптар деңгейі (NestedTabularInline)
class ChoiceNestedInline(nested_admin.NestedTabularInline):
    model = Choice
    extra = 4
    max_num = 10

# 2. Сұрақтар деңгейі (NestedStackedInline)
class QuestionNestedInline(nested_admin.NestedStackedInline):
    model = Question
    extra = 1
    inlines = [ChoiceNestedInline]
    fk_name = 'lesson'

# 3. Сабақтар деңгейі (NestedModelAdmin)
@admin.register(Lesson)
class LessonAdmin(nested_admin.NestedModelAdmin):
    list_display = ['order', 'title']
    inlines = [QuestionNestedInline]


# =====================================================================
# 📊 БАСҚА МОДЕЛЬДЕРДІ ТІРКЕУ
# =====================================================================
admin.site.register(UserActivity)
admin.site.register(LessonProgress)