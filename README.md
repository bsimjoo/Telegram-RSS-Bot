<p align="center">
 <img alt="Telegram-RSS-Bot" src="docs/logo.png">
 <p align="center">
 <a href="http://de1.hashbang.sh:7191">
  <img alt="" src="https://img.shields.io/badge/dynamic/json?url=http://de1.hashbang.sh:7191/json&label=build&query=$.build_state&color=white">
  <img alt="Reported bugs from pcworms_bot project" src="https://img.shields.io/badge/dynamic/json?url=http://de1.hashbang.sh:7191/json&label=%F0%9F%90%9E+Bugs&query=$.bugs_count&color=red">
 </a>
 <a href="https://github.com/bsimjoo/Telegram-RSS-Bot/labels/bug">
  <img alt="Bug issue" src="https://img.shields.io/github/issues-raw/bsimjoo/Telegram-RSS-Bot/bug?color=red">
 </a>
 <a href="https://github.com/bsimjoo/Telegram-RSS-Bot/labels/todo">
  <img src="https://img.shields.io/github/issues-raw/bsimjoo/Telegram-RSS-Bot/todo?color=orange&label=TODOs">
 </a>
 <a href="https://www.codefactor.io/repository/github/bsimjoo/telegram-rss-bot">
  <img alt="CodeFactor Grade" src="https://img.shields.io/codefactor/grade/github/bsimjoo/Telegram-RSS-Bot">
 </a>
 <a href="https://github.com/bsimjoo/Telegram-RSS-Bot/releases">
  <img src="https://img.shields.io/github/v/release/bsimjoo/Telegram-RSS-Bot">
  <img alt="GitHub release (latest SemVer including pre-releases)" src="https://img.shields.io/github/v/release/bsimjoo/Telegram-RSS-Bot?include_prereleases&label=pre-release">
 </a>
 <a href="LICENSE.md">
  <img src="https://img.shields.io/github/license/bsimjoo/Telegram-RSS-Bot">
 </a>
 <img src="https://img.shields.io/badge/Python-v3.8+-3776AB?logo=python&logoColor=white">
 <a href="https://core.telegram.org/bots/api-changelog">
  <img src="https://img.shields.io/badge/Bot%20API-5.1-blue?logo=telegram">
 </a>
 <a href="https://bsimjoo.github.io/Telegram-RSS-Bot/donate">
  <img alt="Donate" src="https://img.shields.io/badge/Donate-green">
 </a>
 </p>
 <p align="center">
# [Telegram-RSS-Bot](https://bsimjoo.github.io/Telegram-RSS-Bot)
 A simple telegram bot that read RSS Feeds and send newest feed to all chats(in this article chats = [all PVs, all GPs and all channels]).
Administrators can also send photos, html or simple text messages to chats and ...</p>
</p>

# :rocket: Getting started
Follow Telegram instructions to [create a new bot user](https://core.telegram.org/bots#3-how-do-i-create-a-bot) and get your Bot-Token. keep your Bot-Token safe.

Then download latest release or use git clone.
```bash
git clone https://github.com/bsimjoo/Telegram_RSS_bot.git
```
Note: Telegram-RSS-Bot is always under active development, so if you're looking for a stable and safe release, use the compressed packages or checkout to release branch.

use this:
```bash
git checkout release
```
OR just run this command instead of the one above:
```bash
git clone https://github.com/bsimjoo/Telegram_RSS_bot.git --branch release
```

### Update
Highly recommended to keep your server up to date. if you are using `git` you can do an update with `git pull`

## :arrow_down: Installation
First install python. I recommend Python v3.8+ because this project developed and tested with this version. So if you had any problem you can [create an issue](https://github.com/bsimjoo/Telegram-RSS-Bot/issues)

change dir to source directory and install requirements with
```bash
cd Telegram-RSS-Bot
python3 -m pip install {--user} -r requirements.txt
```

*`--user` flag is optional and may needed in some situation*
## :gear: Configuration
Read [docs/Configuration-guide.md](docs/configuration-guide.md)

Copy default configuration example [config-example.conf](config-example.conf) to `user-config.conf` and add token to config file under `main` section
```config
[main]
token = {your bot token}
```

**Note** that `config-example.conf` may be updated, so check for changes to each update. `user-config.conf` is ignored by git to prevent git pull problems
## :running: Run server
use `python main.py` to run server, you can also run server with a new config file with `python main.py -c {config file path}` (Default configurations are `user-config.conf` or `config-example.conf`).
run `python main.py -h` to get help about available arguments.

# :busts_in_silhouette: Access levels
There are three levels of access for the bot. (Owner, Admins, Users)

## :princess: Owner
The person who runs bot-server and has telegram-bot token. He usually has access to source code and Databases.
Owner can also change source of feeds but default source is `http://pcworms.blog.ir/rss` read [Installation at top](arrow_down-installation)

### How the owner is identified
Owner (bot call him as lord!) can identify himself using the token he received previously from @botfather as follow
```
/start {bot-token}
```

### Owner can:
- Generate one-time tokens and add admins. (No remove option at now)
- Get muted notification of bot join/kick from a GP or channel.
- Get notification of Errors and Exceptions (useful for report to me).
- What Others (Admins and users) can do.

## :sunglasses: Admin
A user can only be promoted as an administrator if the owner generates a one-time token with the `/gentoken` command and gives it to the user (this token is not the token previously received from BOTFATHER during the setup process). The user can then request once using the token they received, and the robot notifies its owner that the user is requesting a promotion, then the administrator can accept or decline the request. If the owner accepts the request, the user will be promoted and recognized as an administrator.
```
/start {one-time token generated by this bot}
```
Owner will Receive a message with admin information and accept/decline buttons.

### Admins can:
- Send photo, HTML or simple text messages to all chats
- Send last feed to all chats
- Get bot statistics (chats, members and admins count)
- Get a list of all chats with username, full-name and ... (except profile photo and phone number)
- Change the interval between each check for a new post

### Users can:
- Get last feed
- *No more option*

`/help` command will give you a list of all available command related to your access level.

# :tongue: Languages
Available languages are:
 - en-US
 - fa-IR
 - [![*+Add more+*](https://img.shields.io/badge/Add_a_language-blue)](https://github.com/bsimjoo/Telegram-RSS-Bot/edit/main/default-strings.json)

You can translate [default-strings.json](default-strings.json) file to add more languages but this bot will use same language for all users. Owner and admin interface is hardcoded in english (except `/help` command).

**Notice** set your custom strings file path in configuration.

# :arrows_clockwise: Reseting databases
If you're about to reset database you can use `-r {database}` argument to reset `chats`, `data` or `all` databases.

<b>:warning: <font color="orange">This action can not be undone</font></b>

# :beetle: Bug Reporter ![](https://img.shields.io/badge/dynamic/json?url=http://de1.hashbang.sh:7191/json&label=Bugs+found&query=$.bugs_count&color=red)
I wrote a module that reports exceptions or any custom message and counts them, then I can show the number of bugs of a running server and also build state and then track and fix bugs. The bug reporter is off by default, but if you are interested you can save the bugs to a local file `bugs.json` in offline mode, or run the bug report http server in online mode to see them through a http server (click on [bugs or build at top](http://de1.hashbang.sh:7191) to see an example). The default configuration of the http bug reporter is saved in `Bug-reporter.conf` but you can add your own config file to server config file (`user-config.conf`).

**Notice** Don't forget to install `cherrypy` before using http bug reporter. use `python3 -m pip install cherrypy`

# :vertical_traffic_light: License [![GPL-v3](https://img.shields.io/github/license/bsimjoo/Telegram-RSS-Bot)](LICENSE.md)
This project [licensed under GPL-v3](LICENSE.md)
### The Telegram-RSS-Bot logo
the "Telegram-RSS-Bot" logo and any parts thereof are Copyright (©) 2021 by BSimjoo. All rights reserved.

---
Using [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) api
this project began for [pcworms.blog.ir](http://pcworms.blog.ir) weblog, but now it is available for everyone. you can see customized version at [pcworms/PCworms_Bot](https://github.com/pcworms/PCworms_Bot)
###### this is my first telegram bot!
