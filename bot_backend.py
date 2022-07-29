import os
import textwrap

import django
from django.core.exceptions import ObjectDoesNotExist
from functools import partial
from dotenv import load_dotenv
from telegram import (KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
                      Update)
from telegram.ext import (CallbackContext, CommandHandler, ConversationHandler,
                          Filters, MessageHandler, Updater)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup.settings')
django.setup()

from bot.models import Event, EventGroup, Profile, Question, Presentation

MAIN_MENU_CHOICE, \
EVENT_GROUP_CHOICE, \
EVENT_CHOICE, \
CHOOSE_EVENT_TIME, \
CHOOSE_EVENT_SPEAKERS, \
QUESTION, \
SAVE_QUESTION, \
ANSWER, \
NEXT_QUESTION = range(9)

MAIN_MENU_BUTTON_CAPTION = 'Главное меню'
BACK_BUTTON_CAPTION = 'Назад'


def start(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /start is issued."""
    tg_user = update.effective_user
    user_profile, created = Profile.objects.get_or_create(
        telegram_id=tg_user['id'],
        defaults={
            'name': tg_user['first_name'],
            'telegram_username': tg_user['username'],
        })

    keyboard = [[KeyboardButton('Программа'), KeyboardButton('Задать вопрос')]]
    if user_profile.is_speaker:
        keyboard.append([KeyboardButton('Ответить на вопрос')])
    markup = ReplyKeyboardMarkup(
        keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)
    if not created:
        update.message.reply_text(
            'Вы находитесь в главном меню', reply_markup=markup)
    else:
        update.message.reply_text(
            f'Привет {user_profile.name}', reply_markup=markup)

    return MAIN_MENU_CHOICE


def choose_event_group(update: Update, context: CallbackContext) -> int:
    """Ask the user to select an event group"""
    groups = EventGroup.objects.all()
    buttons = [[KeyboardButton(group.title)] for group in groups]
    buttons.append([KeyboardButton(MAIN_MENU_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Какая секция?', reply_markup=markup)

    return EVENT_GROUP_CHOICE


def choose_event(update: Update, context: CallbackContext) -> int:
    """Ask the user to select an event"""
    events = Event.objects.filter(event_group__title=update.message.text)
    if not events:
        return start(update, context)
    context.chat_data['events'] = events
    buttons = [[KeyboardButton(event.title)] for event in events]
    buttons.append([KeyboardButton(BACK_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True)
    update.message.reply_text('Какое мероприятие?', reply_markup=markup)

    return EVENT_CHOICE


def show_event(update: Update, context: CallbackContext) -> int:
    """Show event description"""
    events = context.chat_data['events']
    try:
        event = events.get(title=update.message.text)
    except ObjectDoesNotExist:
        return start(update, context)
    text = textwrap.dedent(
        f'''
        Название презентации:
        {event}

        Описание презентации:
        {event.description}

        Спикер:
        {event.speaker.name}
        '''
    )
    update.message.reply_text(text)

    return EVENT_CHOICE


def choose_event_group_for_ask(update, context):
    groups = EventGroup.objects.all()
    buttons = [[KeyboardButton(group.title)] for group in groups]
    buttons.append([KeyboardButton(MAIN_MENU_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Какая секция?', reply_markup=markup)

    return CHOOSE_EVENT_TIME


def choose_event_time(update, context):
    events = Event.objects.filter(event_group__title=update.message.text, is_presentation=True)
    print(events)
    if not events:
        return start(update, context)
    event_times = {}
    for event in events:
        event_times[f'{event.time_from}-{event.time_to}'] = event.presentations.all()
    print(event_times)
    context.chat_data['event_times'] = event_times
    buttons = [[KeyboardButton(event_time)] for event_time in event_times]
    buttons.append([KeyboardButton(BACK_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True)
    update.message.reply_text('Выберите время', reply_markup=markup)

    return CHOOSE_EVENT_SPEAKERS


def choose_event_speakers(update, context):
    if 'speaker_and_presentation' not in context.user_data:
        event_presentations = context.chat_data['event_times'][update.message.text]
        speaker_and_presentation = {}
        for presentation in event_presentations:
            speaker_and_presentation[presentation.speaker.name] = presentation
        print(speaker_and_presentation)
        context.user_data['speaker_and_presentation'] = speaker_and_presentation
    buttons = [[KeyboardButton(speaker)] for speaker in context.user_data['speaker_and_presentation']]
    buttons.append([KeyboardButton(BACK_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True)
    update.message.reply_text('Выберите спикера', reply_markup=markup)

    return QUESTION


def ask_question(update, context):
    print('question')
    text = 'Задайте вопрос спикеру'
    context.user_data['asked_speaker'] = update.message.text
    context.user_data['questioner_id'] = update.message.chat.id
    update.message.reply_text(text)

    return SAVE_QUESTION


def save_question(update, context):
    text = 'Ваш вопрос направлен спикеру'
    asked_speaker = context.user_data['asked_speaker']
    print(asked_speaker)
    speaker_event = context.user_data['speaker_and_presentation'][asked_speaker]
    Question.objects.get_or_create(
        presentation=speaker_event,
        text=update.message.text,
        listener=Profile.objects.get(
            telegram_id=context.user_data['questioner_id'])
    )
    buttons = [KeyboardButton('Задать новый вопрос')]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[buttons],
        resize_keyboard=True,
        one_time_keyboard=True)
    update.message.reply_text(
        text,
        reply_markup=reply_markup
    )

    return CHOOSE_EVENT_SPEAKERS


def new_question_from_the_speaker(update, context, next=False):
    speaker_id = update.message.chat.id
    buttons = [
        KeyboardButton('Следующий вопрос'),
        KeyboardButton(MAIN_MENU_BUTTON_CAPTION),
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[buttons],
        resize_keyboard=True,
        one_time_keyboard=True)
    if not next:
        result_request, question = get_questions_from_the_speaker(speaker_id)
        context.user_data['question_number'] = 0
        if not question:
            message_text = "Вопросов нет"
        else:
            context.user_data['question'] = question
            message_text = question.text
    else:
        question_number = context.user_data['question_number'] + 1
        result_request, question = get_questions_from_the_speaker(speaker_id, question_number)
        if result_request:
            context.user_data['question_number'] += 1
        else:
            context.user_data['question_number'] = 0
        if not question:
            message_text = "Вопросов нет"
        else:
            context.user_data['question'] = question
            message_text = question.text
    update.message.reply_text(
        message_text,
        reply_markup=reply_markup
    )

    return ANSWER


def get_questions_from_the_speaker(speaker_id: str, question_number=0):
    speaker = Profile.objects.get(telegram_id=speaker_id)
    presentation = Presentation.objects.get(speaker=speaker)
    try:
        question = Question.objects.filter(presentation=presentation).filter(is_active=True)[question_number]
        return True, question
    except IndexError:
        question = Question.objects.filter(presentation=presentation).filter(is_active=True)
        if len(question) > 0:
            return False, question[0]
        else:
            return False, False


def answer_the_question(update, context):
    question = context.user_data['question']
    answer = update.message.text
    listener_id = question.listener.telegram_id

    question.answer = answer
    question.is_active = False
    question.save()

    context.bot.send_message(chat_id=listener_id, text=answer)
    update.message.reply_text("Ответ отправлен. Нажмите на кнопку 'Следующий вопрос'")

    return NEXT_QUESTION


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('SOS!')


def main() -> None:
    """Start the bot."""
    load_dotenv()
    tg_token = os.getenv("TG_TOKEN")

    updater = Updater(tg_token)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start, filters=Filters.regex('^.{7,99}$')),
            CommandHandler('start', start),
        ],
        states={
            MAIN_MENU_CHOICE: [
                MessageHandler(Filters.regex('^Программа$'),
                               choose_event_group),
                MessageHandler(Filters.regex('^Задать вопрос$'),
                               choose_event_group_for_ask),
                MessageHandler(Filters.regex('^Ответить на вопрос$'),
                               new_question_from_the_speaker),
            ],
            EVENT_GROUP_CHOICE: [
                MessageHandler(Filters.regex(f'^{MAIN_MENU_BUTTON_CAPTION}$'),
                               start),
                MessageHandler(Filters.text,
                               choose_event),
            ],
            EVENT_CHOICE: [
                MessageHandler(Filters.regex(f'^{BACK_BUTTON_CAPTION}$'),
                               choose_event_group),
                MessageHandler(Filters.text,
                               show_event),
            ],
            CHOOSE_EVENT_TIME: [
                MessageHandler(Filters.regex(f'^{BACK_BUTTON_CAPTION}$'),
                               choose_event_group_for_ask),
                MessageHandler(Filters.text,
                               choose_event_time),
            ],
            CHOOSE_EVENT_SPEAKERS: [
                MessageHandler(Filters.regex(f'^{BACK_BUTTON_CAPTION}$'),
                               choose_event_group_for_ask),
                MessageHandler(Filters.text,
                               choose_event_speakers),
                MessageHandler(Filters.regex(
                    '^Задать новый вопрос$'), choose_event_speakers),
            ],
            QUESTION: [
                MessageHandler(Filters.text, ask_question),
            ],
            SAVE_QUESTION: [
                MessageHandler(Filters.text, save_question),
            ],
            ANSWER: [
                MessageHandler(Filters.regex('^Главное меню$'), start),
                MessageHandler(Filters.regex('^Следующий вопрос$'),
                               partial(new_question_from_the_speaker, next=True),
                               ),
                MessageHandler(Filters.text, answer_the_question)
            ],
            NEXT_QUESTION: [
                MessageHandler(Filters.regex('^Следующий вопрос$'),
                               partial(new_question_from_the_speaker, next=True)),
            ]
        },
        fallbacks=[
            CommandHandler('start', start),
            MessageHandler(Filters.regex('^Начать$'), start),
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler("help", help_command))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
