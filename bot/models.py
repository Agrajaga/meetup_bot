from django.db import models


class Profile(models.Model):
    name = models.CharField('имя пользователя', max_length=150)
    telegram_id = models.CharField('телеграм ИД', max_length=20)
    telegram_username = models.CharField('телеграм имя', max_length=50)
    is_speaker = models.BooleanField('докладчик', default=False)

    def __str__(self) -> str:
        return f'{self.name} @{self.telegram_username}'


class Presentation(models.Model):
    speaker = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="presentations")
    title = models.CharField('название', max_length=250)
    description = models.TextField('описание')

    def __str__(self) -> str:
        return f'{self.title}'


class Question(models.Model):
    presentation = models.ForeignKey(
        Presentation, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField('текст вопроса')
    listener = models.ForeignKey(Profile, on_delete=models.CASCADE)
    is_active = models.BooleanField('актуальный', default=True)

    def __str__(self) -> str:
        return f'{self.presentation} - {self.listener}'
