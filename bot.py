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

bot_api = config['General']['bot_api']
admins = list(map(int, config['General']['admins'].split(',')))
path = config['General']['path'] or os.getcwd()  # Fallback
captcha = config['Custom']['captcha']

updater = Updater(token=bot_api, request_kwargs={'read_timeout': 10, 'connect_timeout': 10})
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='log.log', level=logging.INFO)


class FilterAdmins(BaseFilter):
    def filter(self, message):
        return message.from_user.id in admins


class FilterFollowingUsers(BaseFilter):
    def filter(self, message):
        return message.from_user.id in following


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
        if member.is_bot and member.username != 'zona_bot':
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
                inform_admins(query.chat.get_administrators(), member.username, group_name)
        else:
            query.reply_text('\n'.join([
                "Hi {}, welcome to {}!",
                "Spam bots are rising lately and threatening to take over humanity!",
                "As a precaution, we're checking the humanity of each new member.",
                "Please include \"{}\" in your next message to show us you mean peace :)"
                ]).format(member.username, group_name, captcha))
            follow_user(member.id)
            logging.info(
                "New member %s (UID %s) joined %s and is now being followed.",
                member.username, member.id, group_name)


def check_message(bot, update):
    query = update.effective_message
    user_id = query.from_user.id
    user_name = query.from_user.username
    chat_id = query.chat_id
    group_name = query.chat.title
    
    try:
        if query.text and captcha in query.text.lower():
            query.reply_text("Horray! You're now officially one of us!")
            logging.info("%s (UID %s) is now one of us!", user_name, user_id)
        else:
            query.reply_text(
                "I had my eyes on you from the beginning! You've been terminated. Buh-bye 😈")
            bot.kick_chat_member(chat_id, user_id)
            logging.info("%s has infiltrated %s group and was terminated.",
                        user_name, group_name)
    except TelegramError:
        inform_admins(query.chat.get_administrators(), user_name, group_name)
        
    unfollow_user(user_id)


def inform_admins(admins, user, group):
    failed = []
    for admin in admins:
        try:
            admin.user.send_message('\n'.join([
                "@{} joined *{}* but I couldn't terminate it.",
                "Grant me with admin rights to terminate new spammers that join this group."
                ]).format(user, group),
                parse_mode="Markdown")
        except Unauthorized:
            failed.append(admin.user.username)

    logging.warning((
        "%s has infiltrated %s group and couldn't be terminated. "
        "A message was sent to %d admins, out of which %d failed (%s)"),
        user, group, len(admins), len(failed),
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
    with open(os.path.join(path, 'log.log'), 'rb') as log:
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
    
    logging.info("%s initiated bot upgrade", user_name)
    git_query = Popen(git_command, cwd=path, stdout=PIPE, stderr=PIPE)
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


def follow_user(uid):
    with open(os.path.join(path, 'users.txt'), "a") as f:
        f.write(str(uid))
        
    update_following_users()


def unfollow_user(uid):
    with open(os.path.join(path, 'users.txt'), "w+") as f:
        for line in f.readlines():
            if line != str(uid):
                f.write(line)

    update_following_users()


def update_following_users():
    global following
    
    try:
        with open(os.path.join(path, 'users.txt'), "r") as f:
            following = [int(user) for user in f.readlines()]
    except FileNotFoundError:
        following = []
    

if __name__ == '__main__':
    update_following_users()
    
    filter_admins = FilterAdmins()
    filter_following = FilterFollowingUsers()
    
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('log', logfile, filters=filter_admins))
    dispatcher.add_handler(CommandHandler('restart', restart, filters=filter_admins))
    dispatcher.add_handler(CommandHandler('upgrade', upgrade, filters=filter_admins))
    dispatcher.add_handler(
        MessageHandler(Filters.status_update.new_chat_members, new_user))    
    dispatcher.add_handler(
        MessageHandler(filter_following, check_message))

        
    logging.info("Bot started.")
    updater.start_polling()
    updater.idle()