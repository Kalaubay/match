from django.db import models

from django.contrib.auth.models import AbstractUser
from django.conf import settings # Осыны пайдаланамыз

class UserActivity(models.Model):
    # 'get_user_model()' орнына тікелей settings.AUTH_USER_MODEL қолдану 
    # импорттау кезіндегі қателердің (circular import) алдын алады
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user} - {self.date}"



class User(AbstractUser):
    # Аты-жөні стандартты түрде Django-да бар (first_name, last_name)
    phone_number = models.CharField(max_length=15, verbose_name="Телефон нөмірі")
    is_verified = models.BooleanField(default=False, verbose_name="Расталған ба?")
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    # Қолданушының рұқсаты бар ең соңғы сабақтың реттік нөмірі
    current_lesson_order = models.PositiveIntegerField(default=1, verbose_name="Ашық сабақ реті")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

class Lesson(models.Model):
    title = models.CharField(max_length=255, verbose_name="Сабақ тақырыбы")
    
    # help_text арқылы админкада нұсқаулық шығарамыз
    video_iframe = models.TextField(
        verbose_name="YouTube IFrame коды", 
        help_text=(
            "МАҢЫЗДЫ НҰСҚАУЛЫҚ: <br>"
            "1. YouTube-тен 'Embed' кодын көшіріп алыңыз.<br>"
            "2. Кодтың ішіне <b>id='player'</b> қосыңыз.<br>"
            "3. Сілтеме (src) соңына <b>?enablejsapi=1</b> қосыңыз.<br>"
            "Мысалы: &lt;iframe <b>id='player'</b> ... src='.../embed/ID<b>?enablejsapi=1</b>' ...&gt;&lt;/iframe&gt;"
        )
    )
    
    order = models.PositiveIntegerField(unique=True, verbose_name="Сабақ реті")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}-сабақ: {self.title}"

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}-сабақ: {self.title}"
    

class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson_order = models.IntegerField() # Қай сабаққа өткені
    date_completed = models.DateField(auto_now_add=True) # Қай күні

    class Meta:
        ordering = ['date_completed']
    

