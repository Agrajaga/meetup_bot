import os

from dotenv import load_dotenv
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (CallbackContext, CommandHandler, Updater)

from api_functions import user_auth


def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_profile = user_auth(user)
    keys = [KeyboardButton('Меню участника')]
    if user_profile.is_speaker:
        keys.append(KeyboardButton('Меню докладчика'))
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[keys], resize_keyboard=True, one_time_keyboard=True)

    update.message.reply_text(
        f'Привет {user_profile.name}', reply_markup=reply_markup)


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('SOS!')


def main() -> None:
    """Start the bot."""
    load_dotenv()
    tg_token = os.getenv("TG_TOKEN")

    updater = Updater(tg_token)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
