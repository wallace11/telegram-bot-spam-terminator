# Telegram Bot Spam Terminator
A [Telegram](https://telegram.org/) bot that automatically terminates other bots.
Based on the wonderful [python-telegram-bot](https://python-telegram-bot.org/).

### Requirements
* Python 3
* [python-telegram-bot](https://python-telegram-bot.org/)

### Setting up
* Edit config.ini to include your bot API key obtained from [@BotFather](https://t.me/botfather).
* Optionally add your user ID as an admin (talk to [@get_id_bot](https://t.me/get_id_bot) to find out yours). Multiple admins should be separated by a comma.
* In case the bot is running as a service or as part of a script (and it should...), it may be a good idea to add the full path to where it resides.
* Since version 0.2 a captcha option is added to cope with spammers that aren't bots. The captcha word is mandatory.