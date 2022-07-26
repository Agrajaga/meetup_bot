from django.contrib import admin

from .models import Presentation, Profile, Question

admin.site.register(Presentation)
admin.site.register(Question)
admin.site.register(Profile)