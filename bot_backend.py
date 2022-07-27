import os
import textwrap

from dotenv import load_dotenv
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (CallbackContext, CommandHandler,
                          Updater, MessageHandler, Filters, ConversationHandler)

from api_functions import user_auth
from bot.models import Presentation, Question, Profile

PROGRAMM, PRESENTATION, QUESTION, SAVE_QUESTION, ANSWER = range(5)


def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_profile = user_auth(user)
    keys = [KeyboardButton('Задать вопрос'), KeyboardButton('Программа')]
    if user_profile.is_speaker:
        keys.append(KeyboardButton('Ответить на вопрос'))
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[keys], resize_keyboard=True, one_time_keyboard=True)

    update.message.reply_text(
        f'Привет {user_profile.name}', reply_markup=reply_markup)

    return PROGRAMM


def chose_presentation(update, context):
    text = 'Выберите презентацию'
    presentations = Presentation.objects.all()
    buttons = [KeyboardButton(presentation.title)
               for presentation in presentations]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[buttons], resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        text,
        reply_markup=reply_markup
    )

    return PRESENTATION


def get_presentation(update, context):
    presentation = Presentation.objects.get(title=update.message.text)
    context.user_data['presentation'] = presentation
    text = textwrap.dedent(
        f'''
        Название презентации:
        {presentation}
        
        Описание презентации:
        {presentation.description}
        
        Спикер:
        {presentation.speaker.name}
        '''
    )
    buttons = [KeyboardButton('Задать вопрос'), KeyboardButton('Программа')]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[buttons],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    update.message.reply_text(
        text,
        reply_markup=reply_markup
    )

    return QUESTION


def ask_question(update, context):
    text = 'Задайте вопрос спикеру'
    context.user_data['questioner_id'] = update.message.chat.id
    context.user_data['question'] = update.message.text
    update.message.reply_text(text)

    return SAVE_QUESTION


def save_question(update, context):
    print(context.user_data['presentation'])
    text = 'Ваш вопрос направлен спикеру'
    Question.objects.get_or_create(
        presentation=context.user_data['presentation'],
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


def new_question_from_the_speaker(update, context):
    speaker_id = update.message.chat.id
    question = get_questions_from_the_speaker(speaker_id)
    context.user_data['question'] = question
    buttons = [KeyboardButton('Пропустить'), KeyboardButton('Главное меню')]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[buttons],
        resize_keyboard=True,
        one_time_keyboard=True)
    update.message.reply_text(
        question.text,
        reply_markup=reply_markup
    )
    return ANSWER


def get_questions_from_the_speaker(speaker_id: str) -> list:
    speaker = Profile.objects.get(telegram_id=speaker_id)
    presantation = Presentation.objects.get(speaker=speaker)
    question = Question.objects.filter(presentation=presantation).filter(is_active=True)[0]
    return question


def answer_the_question(update, context):
    listener_id = context.user_data['question'].listener.telegram_id
    context.bot.send_message(chat_id=listener_id, text=update.message.text)


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
            PROGRAMM: [
                CommandHandler(
                    "start", start, filters=Filters.regex('^.{7,20}$')),
                MessageHandler(Filters.regex('^Программа$'),
                               chose_presentation),
            ],
            PRESENTATION: [
                MessageHandler(Filters.regex('^.{1,99}$'), get_presentation),
                MessageHandler(Filters.text, get_presentation),
                MessageHandler(Filters.regex('^Программа$'),
                               chose_presentation),
            ],
            QUESTION: [
                MessageHandler(Filters.regex('^Задать вопрос$'), ask_question),
                MessageHandler(Filters.regex(
                    '^Задать новый вопрос$'), ask_question),
            ],
            SAVE_QUESTION: [
                MessageHandler(Filters.text, save_question),
                MessageHandler(Filters.regex('^Программа$'),
                               chose_presentation),
            ],

        },
        fallbacks=[CommandHandler('start', start), MessageHandler(
            Filters.regex('^Начать$'), start)],
        per_user=True,
        per_chat=True,
        allow_reentry=True
    )

    answer_to_questions_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex('^Ответить на вопрос$'), new_question_from_the_speaker)
        ],
        states={
            ANSWER: [
                MessageHandler(Filters.text, answer_the_question)
            ],

        },
        fallbacks=[],
        per_user=True,
        per_chat=True,
        allow_reentry=True
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(answer_to_questions_handler)
    dispatcher.add_handler(CommandHandler("help", help_command))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
