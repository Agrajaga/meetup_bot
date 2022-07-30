import os

import django
from functools import partial
from dotenv import load_dotenv
from telegram import (KeyboardButton, LabeledPrice, ReplyKeyboardMarkup,
                      Update)
from telegram.ext import (CallbackContext, CommandHandler, ConversationHandler,
                          Filters, MessageHandler, Updater, PreCheckoutQueryHandler)

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
    NEXT_QUESTION, \
    INPUT_DONATE, \
    CHECK_PAYMENT = range(11)

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
    keyboard.append([KeyboardButton('Задонатить')])
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
    buttons = [[KeyboardButton(group.title) for group in groups], [
        KeyboardButton(MAIN_MENU_BUTTON_CAPTION)]]
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Какая секция?', reply_markup=markup)

    return EVENT_GROUP_CHOICE


def split_buttons(arr, size):
    arrs = []
    while len(arr) > size:
        pice = arr[:size]
        arrs.append(KeyboardButton(pice))
        arr = arr[size:]
    arrs.append(arr)
    return arrs


def choose_event(update: Update, context: CallbackContext) -> int:
    """Ask the user to select an event"""
    events = Event.objects \
        .filter(event_group__title=update.message.text) \
        .order_by('time_from')
    if not events:
        return start(update, context)
    num_cols = 2
    buttons = []
    row = []
    for event in events:
        row.append(
            KeyboardButton(
                f'{event.time_from:%H:%M} {event.title}'
            )
        )
        if len(row) == num_cols:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([KeyboardButton(BACK_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True)
    update.message.reply_text('Какое мероприятие?', reply_markup=markup)

    return EVENT_CHOICE


def show_event(update: Update, context: CallbackContext) -> int:
    """Show event description"""
    title_position = 6
    event_title = update.message.text[title_position:]
    presentations = Presentation.objects \
        .filter(event__title=event_title)
    if not presentations:
        return start(update, context)

    text_blocks = [
        f'<b><i>{presentations[0].event}</i></b>\n',
    ]
    for presentation in presentations:
        text_blocks.append(
            f'<b>{presentation.title}</b>\n{presentation.speaker}\n',
        )
    update.message.reply_html('\n'.join(text_blocks))

    return EVENT_CHOICE


def choose_event_group_for_ask(update, context):
    groups = EventGroup.objects.all()
    group_titles = [group.title for group in groups]
    divided_buttons = split_buttons(group_titles, 3)
    divided_buttons.append([KeyboardButton(MAIN_MENU_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=divided_buttons, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Какая секция?', reply_markup=markup)

    return CHOOSE_EVENT_TIME


def choose_event_time(update, context):
    events = Event.objects.filter(
        event_group__title=update.message.text, is_presentation=True)
    if not events:
        return start(update, context)
    event_times = {}
    for event in events:
        event_times[f'{event.time_from}-{event.time_to}'] = event.presentations.all()
    context.chat_data['event_times'] = event_times
    buttons = split_buttons(event_times, 3)
    buttons.append([KeyboardButton(BACK_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Выберите время', reply_markup=markup)

    return CHOOSE_EVENT_SPEAKERS


def choose_event_speakers(update, context):
    if 'speaker_and_presentation' not in context.user_data:
        event_presentations = context.chat_data['event_times'][update.message.text]
        speaker_and_presentation = {}
        for presentation in event_presentations:
            speaker_and_presentation[presentation.speaker.name] = presentation
        context.user_data['speaker_and_presentation'] = speaker_and_presentation
    buttons = split_buttons(context.user_data['speaker_and_presentation'], 2)
    buttons.append([KeyboardButton(BACK_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Выберите спикера', reply_markup=markup)

    return QUESTION


def ask_question(update, context):
    text = 'Задайте вопрос спикеру'
    context.user_data['asked_speaker'] = update.message.text
    context.user_data['questioner_id'] = update.message.chat.id
    update.message.reply_text(text)

    return SAVE_QUESTION


def save_question(update, context):
    text = 'Ваш вопрос направлен спикеру'
    asked_speaker = context.user_data['asked_speaker']
    speaker_event = context.user_data['speaker_and_presentation'][asked_speaker]
    Question.objects.get_or_create(
        presentation=speaker_event,
        text=update.message.text,
        listener=Profile.objects.get(
            telegram_id=context.user_data['questioner_id'])
    )
    buttons = [
        KeyboardButton('Задать новый вопрос'),
        KeyboardButton(MAIN_MENU_BUTTON_CAPTION)
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[buttons],
        resize_keyboard=True,
        one_time_keyboard=True)
    update.message.reply_text(
        text,
        reply_markup=reply_markup
    )

    return CHOOSE_EVENT_SPEAKERS


def new_question_from_the_speaker(update:Update, context: CallbackContext, next=False)-> int:
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
        result_request, question = get_questions_from_the_speaker(
            speaker_id, question_number)
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
    try:
        question = Question.objects.filter(
            is_active=True, presentation__speaker=speaker)[question_number]
        return True, question
    except IndexError:
        question = Question.objects.filter(
            is_active=True, presentation__speaker=speaker)
        if len(question) > 0:
            return False, question[0]
        return False, False


def answer_the_question(update:Update, context: CallbackContext)-> int:
    question = context.user_data['question']
    answer = update.message.text
    listener_id = question.listener.telegram_id

    question.answer = answer
    question.is_active = False
    question.save()

    context.bot.send_message(chat_id=listener_id, text=answer)
    update.message.reply_text(
        "Ответ отправлен. Нажмите на кнопку 'Следующий вопрос'")

    return NEXT_QUESTION


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('SOS!')


def ask_donate_amount(update: Update, context: CallbackContext) -> int:
    """Ask the user to enter the donation amount"""
    buttons = [KeyboardButton(BACK_BUTTON_CAPTION)]
    text = '💰💰💰 Укажите сумму доната в рублях (от 10 руб) 💰💰💰'
    markup = ReplyKeyboardMarkup(
        keyboard=[buttons],
        resize_keyboard=True,
        one_time_keyboard=True)
    update.message.reply_text(text, reply_markup=markup)

    return INPUT_DONATE


def pay_donate(update: Update, context: CallbackContext) -> int:
    """Sends an invoice."""
    donate_amount = int(update.message.text)
    chat_id = update.message.chat_id
    title = "Донателло!"
    description = "Поддержим проведение таких митапов"
    payload = "Donate Meetup-BOT"
    provider_token = os.getenv("TG_PAY_TOKEN")
    currency = "RUB"
    prices = [LabeledPrice("На развитие", donate_amount * 100)]

    context.bot.send_invoice(
        chat_id, title, description, payload, provider_token, currency, prices
    )

    return CHECK_PAYMENT


def precheckout_callback(update: Update, context: CallbackContext) -> None:
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    if query.invoice_payload != 'Donate Meetup-BOT':
        query.answer(ok=False, error_message="Что-то пошло не так...")
    else:
        query.answer(ok=True)


def successful_payment(update: Update, context: CallbackContext) -> int:
    """Confirms the successful payment."""
    update.message.reply_text('💰💰💰 Спасибо за Вашу поддержку! 💰💰💰')
    return start(update, context)


def unsuccessful_payment(update: Update, context: CallbackContext) -> int:
    """Notify about failed payment."""
    update.message.reply_text("Что-то пошло не так! Давайте попробуем еще раз")
    return ask_donate_amount(update, context)


def main() -> None:
    """Start the bot."""
    tg_token = os.getenv("TG_TOKEN")

    updater = Updater(tg_token)
    dispatcher = updater.dispatcher

    precheckout_handler = PreCheckoutQueryHandler(precheckout_callback)

    conv_handler = ConversationHandler(
        entry_points=[
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
                MessageHandler(Filters.regex('^Задонатить$'),
                               ask_donate_amount),
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
                MessageHandler(Filters.regex(f'^{MAIN_MENU_BUTTON_CAPTION}$'),
                               start),
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
                MessageHandler(Filters.regex(f'^{MAIN_MENU_BUTTON_CAPTION}$'),
                               start),
                MessageHandler(Filters.regex('^Следующий вопрос$'),
                               partial(
                                   new_question_from_the_speaker, next=True),
                               ),
                MessageHandler(Filters.text, answer_the_question)
            ],
            NEXT_QUESTION: [
                MessageHandler(Filters.regex('^Следующий вопрос$'),
                               partial(new_question_from_the_speaker, next=True)),
            ],
            INPUT_DONATE: [
                MessageHandler(Filters.regex('^\d$'), pay_donate),
                MessageHandler(Filters.regex(f'^{BACK_BUTTON_CAPTION}$'),
                               start),
                MessageHandler(Filters.text | ~Filters.command,
                               ask_donate_amount),
            ],
            CHECK_PAYMENT: [
                MessageHandler(Filters.successful_payment, successful_payment),
                MessageHandler(~Filters.successful_payment, unsuccessful_payment),
            ],
        },
        fallbacks=[
            CommandHandler('start', start),
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True
    )

    dispatcher.add_handler(precheckout_handler)
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler("help", help_command))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
