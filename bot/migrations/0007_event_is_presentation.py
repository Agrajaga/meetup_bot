# Generated by Django 4.0.4 on 2022-07-29 06:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0006_alter_question_answer'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='is_presentation',
            field=models.BooleanField(default='False', verbose_name='это доклад'),
            preserve_default=False,
        ),
    ]
