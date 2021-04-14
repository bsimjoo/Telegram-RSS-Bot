<p align="center">
 <img src="Docs/logo.png">
 <h1 align="center">Telegram RSS Bot</h1>
 <p align="center">
 <a href="http://de1.hashbang.sh:7191">
  <img alt="" src="https://img.shields.io/badge/dynamic/json?url=http://de1.hashbang.sh:7191/json&label=build&query=$.build_state&color=white">
  <img alt="Reported bugs from pcworms_bot project" src="https://img.shields.io/badge/dynamic/json?url=http://de1.hashbang.sh:7191/json&label=Bugs+found&query=$.bugs_count&color=red">
 </a>
 <a href="https://github.com/bsimjoo/Telegram-RSS-Bot/labels/bug">
  <img alt="Bug issue" src="https://img.shields.io/github/issues-raw/bsimjoo/Telegram-RSS-Bot/bug?color=red">
 </a>
 <a href="https://github.com/bsimjoo/Telegram-RSS-Bot/labels/todo">
  <img src="https://img.shields.io/github/issues-raw/bsimjoo/Telegram-RSS-Bot/todo?color=orange&label=TODOs">
 </a>
 <a href="https://github.com/bsimjoo/Telegram-RSS-Bot/releases">
  <img src="https://img.shields.io/github/v/release/bsimjoo/Telegram-RSS-Bot">
  <img alt="GitHub release (latest SemVer including pre-releases)" src="https://img.shields.io/github/v/release/bsimjoo/Telegram-RSS-Bot?include_prereleases&label=pre-release">
 </a>
 <a href="LICENSE.md">
  <img src="https://img.shields.io/github/license/bsimjoo/Telegram-RSS-Bot">
 </a>
 <img src="https://img.shields.io/badge/Python-v3.8-blue">
 <a href="https://core.telegram.org/bots/api-changelog">
  <img src="https://img.shields.io/badge/Bot%20API-5.1-blue?logo=telegram">
 </a>
 </p>
 <p align="center">
 A simple telegram bot that read RSS Feeds and send newest feed to all chats(in this article chats = [all PVs, all GPs and all channels]).
Administrators can also send photos, html or simple text messages to chats and ...</p>
</p>

## Owner
The person who runs bot-server and has telegram-bot token. He usually has access to source code and Databases.

*Owner can change source of feeds but default source is `http://pcworms.blog.ir/rss` read [Installation](#installation)*

### How the owner is identified
Owner (bot call him as lord!) can identify himself using the token he got from @botfather like this: `/start {bot-token}`

### Owner can:
- Generate one-time tokens and add admins. (No remove option at now)
- Get muted notification of bot join/kick from a GP or channel.
- Get notification of Errors and Exceptions (useful for report to me).
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
- Get a list of all chats with username, full-name and ... (except profile photo and phone number)
- Change the interval between each check for a new post

### Users can:
- Get last feed
- *No more option*

---
`/help` command will give you a list of all available command related to your access.

# Languages
Available languages:
 - en-US
 - fa-IR
 - [*+Add more+*](https://github.com/bsimjoo/Telegram_RSS_bot/edit/main/default-strings.json)
You can translate [default-strings.json](default-strings.json) file to add more languages but this bot will use same language for all users, I will make it multilingual for users in future. Owner and admin interface is hardcoded in english (except `/help` command) and [strings.json](strings.json) use to comunicating with users.

**Notice** Rename you custom strings file to `strings.json` to prevent git pull errors. (`strings.json` is ignored for your custom version)

# Installation:
First of all admin need to create a new bot using telegram @BotFather and keep Bot-Token safe. then Download Compressed Source or use git clone
```bash
git clone https://github.com/bsimjoo/Telegram_RSS_bot.git
```

Change working directory to source directory and install requirements using this commands:
```bash
cd ./Telegram_RSS_Bot
python3 -m pip install --user -r requirements.txt
```
wait until installation finish without any error. (You can report errors to me)

Then configure server. this repository may update `config-example.conf`, but `user-config.conf` is ignored and it is for users
```bash
cp config-example.conf user-config.conf
```
Edit `user-config.conf` with a text editor, if you want to know about Bug-Reporter [see Bug reporter below](#bug-reporter--)

Then run server
```bash
python3 main.py
```
Identify yourself as owner to bot. you can start a chat with your bot and then use this:
```
/start {bot-token}
```

# Reset databases
If your about to reset database you can use `-r {database}` to reset `chats`, `data` or `all` databases.

<b>:warning: <font color="orange">This action can not be undone</font></b>

# Bug Reporter [![Bugs](https://img.shields.io/badge/dynamic/json?url=http://de1.hashbang.sh:7191/json&label=Bugs+found&query=$.Telegram_RSS_Bot.bugs_count&color=red) ![build](https://img.shields.io/badge/dynamic/json?url=http://de1.hashbang.sh:7191/json&label=build&query=$.Telegram_RSS_Bot.build&color=white)](http://de1.hashbang.sh:7191)
I wrote a module that reports exceptions or any custom message and counts them, then I can show the number of bugs of a running server and then track and fix them. The bug reporter is off by default, but if you are interested you can save the bugs to a local file `bugs.json` in offline mode, or run the bug report http server in online mode to see them through an http server (click on [![Bugs](https://img.shields.io/badge/dynamic/json?url=http://de1.hashbang.sh:7191/json&label=Bugs+found&query=$.Telegram_RSS_Bot.bugs_count&color=red) or ![build](https://img.shields.io/badge/dynamic/json?url=http://de1.hashbang.sh:7191/json&label=build&query=$.Telegram_RSS_Bot.build&color=white)](http://de1.hashbang.sh:7191) badge to see an example). The default configuration of the http bug reporter is saved in `Bug-reporter.conf` but you can config server to use your own config file.

**Notice** Don't forget to install `cherrypy` before using http bug reporter. use `python3 -m pip install cherrypy`

---
Using [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) api

###### this is my first telegram bot!
this project began for [pcworms.blog.ir](http://pcworms.blog.ir) weblog, but now it is available for everyone. you can see customized version at [pcworms/PCworms_Bot](https://github.com/pcworms/PCworms_Bot)
