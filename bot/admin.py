from django.contrib import admin

from .models import Event, EventGroup, Profile, Question, Presentation

admin.site.register(Event)
admin.site.register(EventGroup)
admin.site.register(Question)
admin.site.register(Profile)
admin.site.register(Presentation)