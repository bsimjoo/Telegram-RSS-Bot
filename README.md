# Telegram_RSS_bot
A simple telegram bot started for [pcworms.blog.ir](http://pcworms.blog.ir) weblog that read RSS Feeds and send newest feed to all chats(in this article chats = [all PVs, all GPs and all channels]).
Administrators can also send photos, markdown or simple text messages to chats.

*(Who runs server (call as Owner) can change source of feeds but default source is `http://pcworms.blog.ir/rss`)*

## Owner
The person who runs bot-server and has telegram-bot token. He usually has access to source code and Databases.

### How the owner is identified
Owner (bot call him as lord!) can identify himself using the token he got from @botfather like this: `/start {bot-token}`

### Owner can:
- Generate one-time tokens and add admins. (No remove option at now)
- Get muted notification of bot join/kick from a GP or channel.
- Get notification of Errors and Exceptions (usefull for report to me).
- What Others (Admins and users) can do.

## Admin
A user can promote as admin just if Owner give him a one-time token who got from bot;
then user can use one-time token for promotion like this:
```
/start {token}
```
Then Owner Receive a message with admin information and accept/decline button.

### Admins can:
- Send photo, markdown or simple text messages to all chats
- Send last feed to all chats
- Get bot statistics (chats, members and admins count)
- Get a list of all chats with username, fullname and ... (except profile photo and phone number)
- Change the interval between each check for a new post

### Users can:
- Get last feed
- *No more option*

---
`/help` command will give you a list of all available command related to user level.

# Languages
Available languages:
 - en-US
 - fa-IR
 - [*+Add more+*](https://github.com/bsimjoo/Telegram_RSS_bot/edit/main/default-strings.json)
You can translate [default-strings.json](default-strings.json) file to add more languages but this bot will use same language for all users, I will make it multilingual for users in future. Owner and admin interface is hardcoded in english (except `/help` command) and [strings.json](strings.json) use to comunicating with users.

**Notice** Rename you custom strings file to `strings.json` to prevent git pull errors. (`strings.json` is ignored for your custom version)

# Installtion:
First of all admin need to create a new bot using telegram @BotFather and keep Bot-Token safe. then Download Comprressed Source or use git clone
```bash
git clone https://github.com/bsimjoo/Telegram_RSS_bot.git
```

Change working directory to source directory and install requirements using this commands:
```
cd ./pcworms_bot
python3 -m pip install --user -r requirements.txt
```
wait until installation finish without any error. (You can report errors to me)

Then configure and run the server for first use.
```
python3 main.py -t {bot-token-here} -s {source-here} -l {language}
```
The program will save the configurations for reuse in the database, so you do not need to reconfigure the server for the next run, unless you need to change them.

Identify yourself as owner to bot. you can start a chat with your bot and then use this:
```
/start {bot-token}
```

# Reset databases
If your about to reset database you can user `-r {database}` to reset `chats`, `config` or `all` databases.

**:warning: This action can not be undone**

---
Using [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) api

###### this is my first telegram bot!
this project began for [pcworms.blog.ir](http://pcworms.blog.ir) weblog, but now it is available for everyone
