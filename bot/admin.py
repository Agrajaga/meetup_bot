import os

from django.contrib import admin
from telegram import Bot,error


from .models import (Event, EventGroup, MailingList, Presentation, Profile,
                     Question)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_filter = ['is_presentation']


@admin.register(Presentation)
class PresentationAdmin(admin.ModelAdmin):
    list_filter = ['event__event_group__title', 'event__is_presentation', 'speaker']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_speaker')


@admin.register(MailingList)
class MailingListAdmin(admin.ModelAdmin):
    actions = ['send_newsletter']

    @admin.action(description='Рассылка уведомлений')
    def send_newsletter(self, request, queryset):
        tg_token = os.getenv("TG_TOKEN")
        bot = Bot(tg_token)
        recipients = [profile.telegram_id for profile in Profile.objects.all()]
        for newsletter in queryset:
            message = newsletter.message
            for recipient in recipients:
                try:
                    bot.send_message(chat_id=recipient, text=message)
                except error.BadRequest:
                    print(f"Пользователь {recipient} не найден")


admin.site.register(EventGroup)
admin.site.register(Question)
