from telegram import ChatAction, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters, BaseFilter
from telegram.error import TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError
import configparser
import logging
import time
import os
import sys
from subprocess import Popen, PIPE
from threading import Thread

config = configparser.ConfigParser()
config.read('config.ini')

bot_api = config['General']['api_key']
admins = list(map(int, config['General']['admins'].split(',')))
path = config['General']['path']

updater = Updater(token=bot_api)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='log.log', level=logging.INFO)


class FilterAdmins(BaseFilter):
    def filter(self, message):
        return message.from_user.id in admins


def start(bot, update):
    query = update.effective_message
    user_id = query.from_user.id
    user_name = query.from_user.username
    query.reply_text('\n'.join([
            "Welcome to the Spam Terminator Bot!",
            "Add me to a new group and grant me with admin right.",
            "I'll make sure no spam bots will join your group ever again."
        ]))
    logging.info(
        "User %s (ID: %s) started using the bot! Hooray!",
        user_name, user_id)


def new_user(bot, update):
    query = update.effective_message
    chat_id = query.chat_id
    new_chat_members = query.new_chat_members
    group_name = query.chat.title

    for member in new_chat_members:
        if member.is_bot:
            try:
                bot.kick_chat_member(chat_id, member.id)
                query.reply_text('\n'.join([
                    "{} was terminated.",
                    "No bots allowed when Spam terminator bot is around 😈"]).format(
                        member.username))
                logging.info(
                    "%s bot has infiltrated %s group and was terminated.",
                    member.username, group_name)
            except TelegramError:
                admins = query.chat.get_administrators()
                failed = []
                for admin in admins:
                    try:
                        admin.user.send_message('\n'.join([
                            "Bot @{} joined *{}* but I couldn't terminate it.",
                            "Grant me with admin rights to terminate new bots that join this channel."
                            ]).format(member.username, group_name),
                            parse_mode="Markdown")
                    except Unauthorized:
                        failed.append(admin.user.username)

                logging.info((
                    "%s bot has infiltrated %s group and couldn't be terminated. "
                    "A message was sent to %d admins, out of which %d failed (%s)"),
                    member.username, group_name, len(admins), len(failed),
                    ', '.join(failed))


def help(bot, update):
    query = update.effective_message
    query.reply_text('\n'.join([
        "Spam Terminator by @wallace.",
        "Check out the source code @ http://github.com/wallace11/telegram-bot-spam-terminator",
        "Bot version: 0.1 beta"]))


def logfile(bot, update):
    query = update.effective_message
    user_id = query.from_user.id
    user_name = query.from_user.username
    
    file_name = 'spam-terminator-log_{}.log'.format(time.strftime('%Y-%m-%d_%H-%M-%S'))
    with open('log.log', 'rb') as log:
        query.reply_document(log, filename=file_name)
    logging.info("%s requested the log file.", user_name)


def restart(bot, update):
    def stop_and_restart():
        updater.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)

    query = update.effective_message
    user_name = query.from_user.username
    
    query.reply_text("♻ Restarting...")
    Thread(target=stop_and_restart).start()
    logging.info("%s restarted the bot", user_name)


def upgrade(bot, update):
    query = update.effective_message
    user_name = query.from_user.username
    
    git_command = ['/usr/bin/git', 'pull']
    repository  = os.path.dirname(path) or os.getcwd()  # Fallback
    
    logging.info("%s initiated bot upgrade", user_name)
    git_query = Popen(git_command, cwd=repository, stdout=PIPE, stderr=PIPE)
    (git_status, error) = git_query.communicate()

    if git_query.poll() == 0:
        query.reply_text(
            '🗒 `{}`'.format(git_status.decode('UTF-8')), parse_mode="Markdown")
        logging.info("Bot upgrade completed successfully")
        restart(bot, update)
    else:
        query.reply_text(
            '`{}`'.format(error.decode('UTF-8')), parse_mode="Markdown")
        logging.info(
            "An error occured during upgrade: \"%s\"",
            error.decode('UTF-8').strip())


if __name__ == '__main__':
    filter_admins = FilterAdmins()
    
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('log', logfile, filters=filter_admins))
    dispatcher.add_handler(CommandHandler('restart', restart, filters=filter_admins))
    dispatcher.add_handler(CommandHandler('upgrade', upgrade, filters=filter_admins))
    dispatcher.add_handler(
        MessageHandler(Filters.status_update.new_chat_members, new_user))
        
    logging.info("Bot started.")
    updater.start_polling()
    updater.idle()