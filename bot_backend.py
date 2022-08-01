import os
import textwrap

import django
from functools import partial
from telegram import (KeyboardButton, LabeledPrice, ReplyKeyboardMarkup,
                      Update)
from telegram.ext import (CallbackContext, CommandHandler, ConversationHandler,
                          Filters, MessageHandler, Updater,
                          PreCheckoutQueryHandler)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup.settings')
django.setup()

from bot.models import Event, EventGroup, Profile, Question, Presentation

SURVEY_INPUT_NAME, \
SURVEY_INPUT_COMPANY, \
SURVEY_INPUT_JOB, \
SURVEY_CONFIRM = range(4)

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
CHECK_PAYMENT, \
MEET_CHOICE = range(12)

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
    context.user_data['profile'] = user_profile
    keyboard = [
        [KeyboardButton('Программа'), KeyboardButton('Задать вопрос')],
        [KeyboardButton('Задонатить'), KeyboardButton('Познакомиться')],
    ]
    if user_profile.is_speaker:
        keyboard.append([KeyboardButton('Ответить на вопрос')])
    markup = ReplyKeyboardMarkup(
        keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

    text = 'Вы находитесь в главном меню'
    if created:
        text = f'Привет {user_profile.name}'

    update.message.reply_text(text, reply_markup=markup)

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


def split_keyboard(captions, num_cols):
    """Create structure of keyboard with several columns"""
    buttons, row = [], []
    for caption in captions:
        row.append(KeyboardButton(caption))
        if len(row) == num_cols:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons


def choose_event(update: Update, context: CallbackContext) -> int:
    """Ask the user to select an event"""
    events = Event.objects \
        .filter(event_group__title=update.message.text) \
        .order_by('time_from')
    if not events:
        return start(update, context)
    buttons = split_keyboard(
        captions=[f'{event.time_from:%H:%M} {event.title}' for event in events],
        num_cols=2,
    )
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
    """Ask the user to select an event group"""
    choose_event_group(update, context)

    return CHOOSE_EVENT_TIME


def choose_event_time(update, context):
    """Ask the user to select the time interval of events"""
    events = Event.objects.filter(
        event_group__title=update.message.text, is_presentation=True)
    if not events:
        return start(update, context)
    event_times = {}
    for event in events:
        time_interval = f'{event.time_from:%H:%M}-{event.time_to:%H:%M}'
        event_times[time_interval] = event.presentations.all()
    context.chat_data['event_times'] = event_times
    buttons = split_keyboard(list(sorted(event_times.keys())), 2)
    buttons.append([KeyboardButton(BACK_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Выберите время', reply_markup=markup)

    return CHOOSE_EVENT_SPEAKERS


def choose_event_speakers(update, context):
    """Ask the user to select the speaker"""
    event_presentations = context.chat_data['event_times'][update.message.text]
    speaker_and_presentation = {}
    for presentation in event_presentations:
        speaker_and_presentation[presentation.speaker.name] = presentation
    context.user_data['speaker_and_presentation'] = speaker_and_presentation
    buttons = split_keyboard(
        captions=list(speaker_and_presentation.keys()),
        num_cols=2
    )
    buttons.append([KeyboardButton(BACK_BUTTON_CAPTION)])
    markup = ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Выберите спикера', reply_markup=markup)

    return QUESTION


def ask_question(update, context):
    """Ask the user to enter a question"""
    text = 'Задайте свой вопрос спикеру'
    keyboard = [[KeyboardButton(MAIN_MENU_BUTTON_CAPTION)], [KeyboardButton('Показать вопросы')]]
    markup = ReplyKeyboardMarkup(
        keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)
    if update.message.text not in list(context.user_data['speaker_and_presentation'].keys()):
        buttons = split_keyboard(
            captions=list(context.user_data['speaker_and_presentation'].keys()),
            num_cols=2
        )
        buttons.append([KeyboardButton(BACK_BUTTON_CAPTION)])
        markup = ReplyKeyboardMarkup(
            keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text('Выберите спикера', reply_markup=markup)
        return QUESTION

    context.user_data['asked_speaker'] = update.message.text
    update.message.reply_text(text, reply_markup=markup)

    return SAVE_QUESTION


def save_question(update, context):
    """Confirm the successful submission of the question"""
    if update.message.text == 'Показать вопросы':
        speaker = context.user_data['asked_speaker']
        answered_questions = Question.objects.filter(presentation__speaker__name=speaker,
                                                     is_active=False)
        text = 'Еще нет вопросов с ответами'
        if answered_questions.exists():
            text = 'Если вы не нашли ответ на ваш вопрос, то задайте свой \n'
            for question in answered_questions:
                text += textwrap.dedent(
                    f'''
                    
                    Вопрос {question.id}: 
                    {question.text}
                    
                    Ответ: 
                    {question.answer}
                    '''
                    )
        update.message.reply_text(text)

        return ask_question(update, context)

    text = 'Ваш вопрос направлен спикеру'
    asked_speaker = context.user_data['asked_speaker']
    speaker_event = context.user_data['speaker_and_presentation'][asked_speaker]
    Question.objects.create(
        presentation=speaker_event,
        text=update.message.text,
        listener=context.user_data['profile'],
    )
    buttons = [
        KeyboardButton('Задать новый вопрос'),
        KeyboardButton(MAIN_MENU_BUTTON_CAPTION),
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


def new_question_from_the_speaker(
        update: Update,
        context: CallbackContext,
        next=False
) -> int:
    """Show the question to the speaker and ask him to enter the answer"""
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
            message_text = 'Вопросов нет'
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
            message_text = 'Вопросов нет'
        else:
            context.user_data['question'] = question
            message_text = question.text
    update.message.reply_text(
        message_text,
        reply_markup=reply_markup
    )

    return ANSWER


def get_questions_from_the_speaker(speaker_id: str, question_number=0):
    """Get a speaker question"""
    speaker = Profile.objects.get(telegram_id=speaker_id)
    try:
        question = Question.objects.filter(
            is_active=True, presentation__speaker=speaker)[question_number]
        return True, question
    except IndexError:
        questions = Question.objects.filter(
            is_active=True, presentation__speaker=speaker)
        if questions:
            return False, questions[0]
        return False, False


def answer_the_question(update: Update, context: CallbackContext) -> int:
    """Send, save the answer and confirm for speaker"""
    question = context.user_data['question']
    answer = update.message.text
    listener_id = question.listener.telegram_id

    question.answer = answer
    question.is_active = False
    question.save()
    text = textwrap.dedent(
        f'''
        
        Получен ответ на вопрос:
        {question}
        
        Ответ:
        {answer}
        
        '''
     )

    context.bot.send_message(chat_id=listener_id, text=text)
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
    title = 'Донателло!'
    description = 'Поддержим проведение таких митапов'
    payload = 'Donate Meetup-BOT'
    provider_token = os.getenv('TG_PAY_TOKEN')
    currency = 'RUB'
    prices = [LabeledPrice('На развитие', donate_amount * 100)]

    context.bot.send_invoice(
        chat_id, title, description, payload, provider_token, currency, prices
    )

    return CHECK_PAYMENT


def precheckout_callback(update: Update, context: CallbackContext) -> None:
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    if query.invoice_payload != 'Donate Meetup-BOT':
        query.answer(ok=False, error_message='Что-то пошло не так...')
    else:
        query.answer(ok=True)


def successful_payment(update: Update, context: CallbackContext) -> int:
    """Confirms the successful payment."""
    update.message.reply_text('💰💰💰 Спасибо за Вашу поддержку! 💰💰💰')
    return start(update, context)


def unsuccessful_payment(update: Update, context: CallbackContext) -> int:
    """Notify about failed payment."""
    update.message.reply_text('Что-то пошло не так! Давайте попробуем еще раз')
    return ask_donate_amount(update, context)


def start_meet(update: Update, context: CallbackContext) -> int:
    """Ask the user to select action."""
    buttons = [
        [
            KeyboardButton('Заполнить анкету'),
            KeyboardButton('Подобрать знакомство'),
        ],
        [KeyboardButton(MAIN_MENU_BUTTON_CAPTION)],
    ]
    markup = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
    )
    update.message.reply_text(
        'Знакомьтесь с интересными людьми',
        reply_markup=markup,
    )

    return MEET_CHOICE


def show_person(update: Update, context: CallbackContext) -> int:
    """Show random person, exclude shown people."""
    profile = context.user_data['profile']
    if not profile.ready_meet:
        update.message.reply_text(
            'Для знакомства заполните свою анкету'
        )
        return start_meet(update, context)
    showed_persons = context.user_data.get('showed_persons', [])
    person = Profile.objects \
        .exclude(id=profile.id) \
        .exclude(id__in=showed_persons) \
        .filter(ready_meet=True) \
        .order_by('?') \
        .first()
    if not person and not showed_persons:
        update.message.reply_text(
            'Пока знакомиться не с кем.\nКак кто-то появится, я Вам сообщу.'
        )
        context.bot_data['lonely_user'] = update.effective_user.id
        return start(update, context)
    if not person:
        context.user_data['showed_persons'] = []
        return show_person(update, context)

    showed_persons.append(person.id)
    context.user_data['showed_persons'] = showed_persons

    text_blocks = [
        f'<b>{person.name}</b>\n',
        f'Компания: <i>{person.company}</i>',
        f'Должность: <i>{person.job}</i>',
        f'@{person.telegram_username}\n',
    ]
    update.message.reply_html('\n'.join(text_blocks))

    return MEET_CHOICE


def start_survey(update: Update, context: CallbackContext) -> int:
    """Ask the user to enter full name."""
    text = 'Начнем знакомство.\nКак Вас зовут? Обычно указывают имя и фамилию.'
    update.message.reply_text(text)
    return SURVEY_INPUT_NAME


def input_name(update: Update, context: CallbackContext) -> int:
    """Ask the user to enter company name"""
    name = update.message.text
    context.user_data['survey_name'] = name
    text = f'Очень приятно, {name}.\nКак называется Ваша компания?'
    update.message.reply_text(text)
    return SURVEY_INPUT_COMPANY


def input_company(update: Update, context: CallbackContext) -> int:
    """Ask the user to enter job title."""
    company = update.message.text
    context.user_data['survey_company'] = company
    text = f'Ваша компания - {company}.\nКак называется Ваша должность?'
    update.message.reply_text(text)
    return SURVEY_INPUT_JOB


def input_job(update: Update, context: CallbackContext) -> int:
    """Ask the user to confirm the entered data."""
    job = update.message.text
    context.user_data['survey_job'] = job
    buttons = [
        KeyboardButton('Да, всё верно'),
        KeyboardButton('Нет, давай заново'),
    ]
    markup = ReplyKeyboardMarkup(
        keyboard=[buttons],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    text_blocks = [
        'Вот мы и закончили!',
        'Ваша анкета будет выглядеть так:\n\n',
        f'<b>{context.user_data["survey_name"]}</b>\n',
        f'Компания: <i>{context.user_data["survey_company"]}</i>',
        f'Должность: <i>{job}</i>',
        f'@{context.user_data["profile"].telegram_username}\n',
    ]
    update.message.reply_html('\n'.join(text_blocks), reply_markup=markup)

    return SURVEY_CONFIRM


def save_survey(update: Update, context: CallbackContext) -> int:
    """Save the entered data to the user profile."""
    profile = context.user_data['profile']
    profile.name = context.user_data['survey_name']
    profile.company = context.user_data['survey_company']
    profile.job = context.user_data['survey_job']
    profile.ready_meet = True
    profile.save()

    lonely_user = context.bot_data.get('lonely_user', None)
    if lonely_user and lonely_user != update.effective_user.id:
        context.bot_data['lonely_user'] = None
        context.bot.send_message(lonely_user, '🤝 Появились новые анкеты 🤝')

    start_meet(update, context)
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    tg_token = os.getenv('TG_TOKEN')

    updater = Updater(tg_token)
    dispatcher = updater.dispatcher

    precheckout_handler = PreCheckoutQueryHandler(precheckout_callback)

    survey_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex('^Заполнить анкету$'), start_survey),
        ],
        states={
            SURVEY_INPUT_NAME: [
                MessageHandler(Filters.text | ~Filters.command, input_name),
            ],
            SURVEY_INPUT_COMPANY: [
                MessageHandler(Filters.text | ~Filters.command, input_company),
            ],
            SURVEY_INPUT_JOB: [
                MessageHandler(Filters.text | ~Filters.command, input_job),
            ],
            SURVEY_CONFIRM: [
                MessageHandler(Filters.regex('^Да, всё верно$'),
                               save_survey),
                MessageHandler(Filters.regex('^Нет, давай заново$'),
                               start_survey),
            ],
        },
        fallbacks=[
            MessageHandler(Filters.regex('^Заполнить анкету$'), start_survey),
        ],
        map_to_parent={
            ConversationHandler.END: MEET_CHOICE,
        }
    )

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
                MessageHandler(Filters.regex('^Познакомиться$'),
                               start_meet),
            ],
            MEET_CHOICE: [
                survey_conv_handler,
                MessageHandler(Filters.regex('^Подобрать знакомство$'),
                               show_person),
                MessageHandler(Filters.regex(f'^{MAIN_MENU_BUTTON_CAPTION}$'),
                               start),
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
                MessageHandler(Filters.regex(
                    '^Задать новый вопрос$'), ask_question),
                MessageHandler(Filters.regex(f'^{MAIN_MENU_BUTTON_CAPTION}$'),
                               start),
                MessageHandler(Filters.text,
                               choose_event_speakers),
            ],
            QUESTION: [
                MessageHandler(Filters.regex(f'^{BACK_BUTTON_CAPTION}$'),
                               choose_event_group_for_ask),
                MessageHandler(Filters.text, ask_question),
            ],
            SAVE_QUESTION: [
                MessageHandler(Filters.regex(f'^{MAIN_MENU_BUTTON_CAPTION}$'),
                               start),
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
                MessageHandler(Filters.regex('^Следующий вопрос$'), partial(
                    new_question_from_the_speaker, next=True)),
            ],
            INPUT_DONATE: [
                MessageHandler(Filters.regex('^[1-9][0-9]+$'), pay_donate),
                MessageHandler(Filters.regex(f'^{BACK_BUTTON_CAPTION}$'),
                               start),
                MessageHandler(Filters.text | ~Filters.command,
                               ask_donate_amount),
            ],
            CHECK_PAYMENT: [
                MessageHandler(Filters.successful_payment, successful_payment),
                MessageHandler(~Filters.successful_payment,
                               unsuccessful_payment),
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
    dispatcher.add_handler(CommandHandler('help', help_command))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
