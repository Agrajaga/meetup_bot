from email import message
from turtle import update
from django.contrib import admin
import os
from telegram import Bot

from .models import Event, EventGroup, Presentation, Profile, Question, MailingList


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
                bot.send_message(chat_id=recipient, text=message)


admin.site.register(Event)
admin.site.register(EventGroup)
admin.site.register(Question)
admin.site.register(Profile)
admin.site.register(Presentation)
