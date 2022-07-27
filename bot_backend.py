import os
import textwrap

import django
from django.core.exceptions import ObjectDoesNotExist
from dotenv import load_dotenv
from telegram import (KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
                      Update)
from telegram.ext import (CallbackContext, CommandHandler, ConversationHandler,
                          Filters, MessageHandler, Updater)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup.settings')
django.setup()

from bot.models import Event, EventGroup, Profile, Question

MAIN_MENU_CHOICE, \
    EVENT_GROUP_CHOICE, \
    EVENT_CHOICE, \
    QUESTION, \
    SAVE_QUESTION = range(5)

MAIN_MENU_BUTTON_CAPTION = 'Главное меню'
BACK_BUTTON_CAPTION = 'Назад'


def start(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /start is issued."""
    tg_user = update.effective_user
    user_profile, _ = Profile.objects.get_or_create(
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


def ask_question(update, context):
    text = 'Задайте вопрос спикеру'
    context.user_data['questioner_id'] = update.message.chat.id
    context.user_data['question'] = update.message.text
    update.message.reply_text(text)

    return SAVE_QUESTION


def save_question(update, context):
    print(context.user_data['event'])
    text = 'Ваш вопрос направлен спикеру'
    Question.objects.get_or_create(
        event=context.user_data['event'],
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

    return QUESTION


def answer_question(update: Update, context: CallbackContext) -> int:
    pass


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
                               ask_question),
                MessageHandler(Filters.regex('^Ответить на вопрос$'),
                               answer_question),
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
            QUESTION: [
                MessageHandler(Filters.regex('^Задать вопрос$'), ask_question),
                MessageHandler(Filters.regex(
                    '^Задать новый вопрос$'), ask_question),
            ],
            SAVE_QUESTION: [
                MessageHandler(Filters.text, save_question),
            ],
        },
        fallbacks=[CommandHandler('start', start), MessageHandler(
            Filters.regex('^Начать$'), start)],
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
