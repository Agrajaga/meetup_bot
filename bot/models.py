from django.contrib import admin
from django.db import models


class Profile(models.Model):
    name = models.CharField('имя пользователя', max_length=150)
    telegram_id = models.CharField('телеграм ИД', max_length=20)
    telegram_username = models.CharField('телеграм имя', max_length=50)
    company = models.CharField(
        'компания', max_length=150, blank=True, null=True)
    job = models.CharField('должность', max_length=150, blank=True, null=True)
    ready_meet = models.BooleanField('готов знакомиться', default=False)

    @admin.display(description='Докладчик')
    def is_speaker(self):
        return self.presentations.exists()

    class Meta:
        verbose_name = 'профиль'
        verbose_name_plural = 'профили'

    def __str__(self) -> str:
        return f'{self.name} @{self.telegram_username}'


class EventGroup(models.Model):
    title = models.CharField('название', max_length=250)

    class Meta:
        verbose_name = 'группа события'
        verbose_name_plural = 'группы событий'

    def __str__(self) -> str:
        return f'{self.title}'


class Event(models.Model):
    title = models.CharField('название', max_length=250)
    time_from = models.TimeField('время начала')
    time_to = models.TimeField('время окончания')
    event_group = models.ForeignKey(
        EventGroup,
        on_delete=models.CASCADE,
        related_name='events',
    )
    is_presentation = models.BooleanField('это доклад')

    class Meta:
        verbose_name = 'событие'
        verbose_name_plural = 'события'

    def __str__(self) -> str:
        return f'{self.time_from:%H:%M}-{self.time_to:%H:%M} {self.title}'


class Presentation(models.Model):
    title = models.CharField('название', max_length=250)
    description = models.TextField('описание')
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='presentations')
    speaker = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='presentations',
    )

    class Meta:
        verbose_name = 'презентация'
        verbose_name_plural = 'презентации'

    def __str__(self) -> str:
        return f'{self.title}'


class Question(models.Model):
    presentation = models.ForeignKey(
        Presentation, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField('текст вопроса')
    listener = models.ForeignKey(Profile, on_delete=models.CASCADE)
    answer = models.TextField('ответ на вопрос', blank=True)
    is_active = models.BooleanField('актуальный', default=True)

    class Meta:
        verbose_name = 'вопрос'
        verbose_name_plural = 'вопросы'

    def __str__(self) -> str:
        return f'{self.presentation} - {self.listener}'


class MailingList(models.Model):
    name = models.CharField('название', max_length=250)
    message = models.TextField('сообщение')

    class Meta:
        verbose_name = 'рассылка'
        verbose_name_plural = 'рассылки'

    def __str__(self) -> str:
        return f'{self.name}'
