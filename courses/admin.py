from django.contrib import admin
import nested_admin  # Дұрыс импорттау осылай
from .models import User, Lesson, Question, Choice, UserActivity, LessonProgress

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

# Басқа модельдерді стандартты түрде тіркеу
admin.site.register(User)
admin.site.register(UserActivity)
admin.site.register(LessonProgress)