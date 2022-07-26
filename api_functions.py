import os

import django
from django.db import models

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup.settings')
django.setup()

from bot.models import Presentation, Profile, Question


def user_auth(tg_user):
    print(tg_user)
    if tg_user['id']:
        profile, _ = Profile.objects.get_or_create(
            telegram_id=tg_user['id'],
            defaults={
                'name': tg_user['first_name'],
                'telegram_username': tg_user['username'],
            })
        print(profile)
        return profile
