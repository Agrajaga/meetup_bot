from django.contrib import admin

from .models import Event, EventGroup, Presentation, Profile, Question

admin.site.register(Event)
admin.site.register(EventGroup)
admin.site.register(Question)
admin.site.register(Profile)
admin.site.register(Presentation)
