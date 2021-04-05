import json
import lmdb
import pickle
import logging
import sys
import typing
import string
import random
import re
import os
import traceback
from urllib.request import urlopen
from bs4 import BeautifulSoup, Comment
import html
from telegram import *
from telegram.error import BadRequest
from telegram.utils.helpers import DEFAULT_NONE
from telegram.bot import Bot
from telegram.ext import *
from dateutil.parser import parse
from datetime import datetime, timedelta
from threading import Timer

DB_PATH = './db'
STRINGS_PATH = './strings.json'

#All supported tags (Telegram + script image handler) seprated by '|'
SUPPORTED_HTML_TAGS = '|'.join(('a','b','strong','i','em','code','pre','s','strike','del','u','img'))
SUPPORTED_TAG_ATTRS = {'a':'href', 'img':'src', 'pre':'language'}

STATE_ADD, STATE_EDIT, STATE_DELETE, STATE_CONFIRM = range(4)


class BotHandler:

    # --------------------[Decorators]--------------------

    def message_handler(self, filter: BaseFilter):
        def decorator(func):
            self.dispatcher.add_handler(MessageHandler(filter, func))
            return func
        return decorator

    def command(self, f = None, name = None):
        "add a command handler"
        def decorator(func = f):
            self.dispatcher.add_handler(CommandHandler(
                (name if name else func.__name__), func))
            return func
        if not name:
            return(decorator(f))
        return decorator

    def adminCommand(self, f = None, skip_register = False):
        def decorator(func = f):
            def auth_and_run(u: Update, c: CallbackContext):
                if u.effective_user.id in self.adminID:
                    return func(u, c)
                else:
                    return self.__unknown__(u, c)
            if not skip_register:
                self.dispatcher.add_handler(
                    CommandHandler(func.__name__, auth_and_run))
            return auth_and_run

        if skip_register:
            return decorator
        return decorator()

    def ownerCommand(self, f = None, skip_register = False):
        def decorator(func = f):
            def auth_and_run(u: Update, c: CallbackContext):
                if u.effective_user.id == self.ownerID:
                    return func(u, c)
                else:
                    return self.__unknown__(u, c)
            if not skip_register:
                self.dispatcher.add_handler(
                    CommandHandler(func.__name__, auth_and_run))
            return auth_and_run

        if skip_register:
            return decorator
        return decorator()

    # ----------------------------------------------------
    # ----------------------[Init]------------------------

    def __init__(self, logger: logging, Token, source, env, chats_db, config_db, strings: dict, bug_reporter = None):
        #----[USE SOCKES]----
        #import socks
        #s = socks.socksocket()
        #s.set_proxy(socks.SOCKS5, "localhost", 9090)
        #self.updater = Updater(Token, request_kwargs = {'proxy_url': 'socks5h://127.0.0.1:9090/'})
        #-----[NO PROXY]-----
        self.updater = Updater(Token)
        #--------------------
        self.bot = self.updater.bot
        self.dispatcher = self.updater.dispatcher
        self.token = Token
        self.logger = logger
        self.env = env
        self.chats_db = chats_db
        self.config_db = config_db
        self.adminID = self.__get_data__('adminID', [], DB = config_db)
        self.ownerID = self.__get_data__('ownerID', DB = config_db)
        self.admins_pendding = {}
        self.admin_token = []
        self.strings = strings
        self.source = source
        self.interval = self.__get_data__('interval', 5*60, config_db)
        self.__check__ = True
        self.reporter = bug_reporter if bug_reporter else None

        @self.command
        def start(update: Update, _: CallbackContext):
            chat = update.effective_chat
            message = update.message
            user = update.effective_user
            data = chat.to_dict()
            data['members-count'] = chat.get_members_count()-1
            if chat.type == Chat.PRIVATE:
                data.update(user.to_dict())
                message.reply_markdown_v2(self.get_string('wellcome'))
                if len(_.args) == 1:
                    if _.args[0] == self.token:
                        if user.id in self.adminID:
                            message.reply_text(
                                f'My dear {user.full_name}, I already know you as my lord!')
                        else:
                            message.reply_text(
                                f'Hi my dear {user.full_name}\nFrom now on, I know you as my lord\nyour id is: "{user.id}"')
                            self.adminID.append(user.id)
                            self.__set_data__(
                                'adminID', self.adminID, DB = config_db)

                            self.ownerID = user.id
                            self.__set_data__(
                                'ownerID', self.ownerID, DB = config_db)
                    elif _.args[0] in self.admin_token:
                        if user.id in self.adminID:
                            message.reply_text(
                                f'My dear {user.full_name}, I already know you as my admin!')
                        else:
                            message.reply_text(
                                'Owner must accept your request.\n⏳ please wait...')
                            self.admins_pendding[user.id] = _.args[0]
                            self.bot.send_message(
                                self.ownerID,
                                'Hi, A user wants to be admin:\n' +
                                f'tel-id:\t{user.id}\n' +
                                f'user-id:\t{user.username}\n' +
                                f'name:\t{user.full_name}',
                                reply_markup = InlineKeyboardMarkup(
                                    [[
                                        InlineKeyboardButton(
                                            '✅ Accept', callback_data = f'accept-{user.id}'),
                                        InlineKeyboardButton(
                                            '❌ Decline', callback_data = f'decline-{user.id}')
                                    ]])
                            )

            else:
                update.message.reply_markdown_v2(
                    self.get_string('group-intro'))

            self.__set_data__(key = str(chat.id), value = data)

        # --------------[owner commands]-----------------

        @self.ownerCommand
        def gentoken(u: Update, c: CallbackContext):
            if u.effective_user.id == self.ownerID:
                admin_token = ''.join(
                    [random.choice(string.ascii_letters+string.digits) for x in range(32)])
                self.admin_token.append(admin_token)
                u.message.reply_text(
                    admin_token
                )
            else:
                self.__unknown__(u, c)

        # --------------[admin commands]-----------------

        @self.adminCommand
        def my_level(u: Update, c: CallbackContext):
            if u.effective_user.id == self.ownerID:
                u.message.reply_text(
                    'Oh, my lord. I respect you. new version2!')
            elif u.effective_user.id in self.adminID:
                u.message.reply_text('Oh, my admin. Hi, How are you?')

        @self.adminCommand
        def state(u: Update, c: CallbackContext):
            members, chats = 0, 0
            msg = u.message.reply_text('⏳ Please wait, counting members...')
            with env.begin(self.chats_db) as txn:
                chats = int(txn.stat()["entries"])
                for key, value in txn.cursor():
                    v = pickle.loads(value)
                    members += v['members-count']
            msg.edit_text(
                f'👥chats:\t{chats}\n' +
                f'👤members:\t{members}\n' +
                f'🤵admins:\t{len(self.adminID)}'
                )

        @self.adminCommand
        def listchats(u: Update, c: CallbackContext):
            res = ''
            with env.begin(self.chats_db) as txn:
                res = 'total: '+str(txn.stat()["entries"])+'\n'
                for key, value in txn.cursor():
                    chat = pickle.loads(value)
                    if 'username' in chat:
                        chat['username'] = '@'+chat['username']
                    res += html.escape(json.dumps(chat,
                                       indent = 2, ensure_ascii = False))
            u.message.reply_html(res)

        def add_keyboard (c:CallbackContext):
            keys = ['❌Cancel']
            if len(c.user_data['messages']):
                keys = ['✅Send', '👁Preview', '❌Cancel']
            markdown = c.user_data['parser'] == ParseMode.MARKDOWN_V2
            return ReplyKeyboardMarkup(
                [
                    [('✅ Markdown Enabled' if markdown else '◻️ Markdown Disabled')],
                    keys
                ],
                resize_keyboard=True
            )

        @self.adminCommand(skip_register = True)
        def sendall(u: Update, c: CallbackContext):
            if u.effective_chat.type != Chat.PRIVATE:
                u.message.reply_text(
                    '❌ ERROR\nthis command only is available in private')
                return ConversationHandler.END
            c.user_data['last-message'] = u.message.reply_text('You can send text or photo.',disable_notification = True)
            c.user_data['messages'] = []
            c.user_data['parser'] = DEFAULT_NONE
            u.message.reply_text(
                'OK, Send a message to forward it to all users',
                reply_markup = add_keyboard(c))
            
            
            return STATE_ADD

        @self.adminCommand
        def send_feed_toall(u: Update, c: CallbackContext):
            self.send_feed(*self.read_feed(), self.get_string('last-feed'), self.iter_all_chats())

        @self.adminCommand
        def set_interval(u: Update, c: CallbackContext):
            if len(c.args) == 1:
                if c.args[0].isdigit():
                    self.interval = int(c.args[0])
                    self.__set_data__(
                        'interval', self.interval, self.config_db)
                    u.message.reply_text('✅ Interval changed to'+self.interval)
                    return
            u.message.reply_text('❌ Bad command')

        # ----------------[User Commands]----------------

        @self.command
        def last_feed(u: Update, c: CallbackContext):
            if u.effective_user.id not in self.adminID and 'time' in c.user_data:
                if c.user_data['time'] > datetime.now():
                    u.message.reply_text(self.get_string('time-limit-error'))
                    return
            self.send_feed(*self.read_feed(),msg_header = self.get_string('last-feed'),chat_ids = [u.effective_chat.id])
            c.user_data['time'] = datetime.now() + timedelta(minutes = 2)      #The next request is available 2 minutes later

        @self.command
        def help(u: Update, c: CallbackContext):
            if u.effective_chat.id == self.ownerID:
                u.message.reply_text(self.get_string('owner-help'))
            if u.effective_chat.id in self.adminID:
                u.message.reply_text(self.get_string('admin-help'))
            u.message.reply_text(self.get_string('help'))

        @self.command
        def stop(u: Update, c: CallbackContext):
            logger.info(
                f'I had been removed from a chat. chat-id:{u.effective_chat.id}')
            with self.env.begin(self.chats_db, write = True) as txn:
                if txn.get(str(u.effective_chat.id).encode()):  # check exist
                    txn.delete(str(u.effective_chat.id).encode())

        # ----------[Conversation handlers]-------------

        def toggle_markdown(u: Update, c:CallbackContext):
            if c.user_data['parser'] == ParseMode.MARKDOWN_V2:
                c.user_data['parser'] = DEFAULT_NONE
                u.message.reply_text('◻️ Markdown Disabled', reply_markup=add_keyboard(c))
            else:
                c.user_data['parser'] = ParseMode.MARKDOWN_V2
                u.message.reply_text('✅ Markdown Enabled', reply_markup=add_keyboard(c))

        def add_text(u:Update, c:CallbackContext):
            c.user_data['messages'].append(
                {
                    'type':'text',
                    'text': u.effective_message.text,
                    'parser': c.user_data['parser']
                }
            )
            c.user_data['last-message'].delete()
            c.user_data['last-message'] = u.message.reply_text('OK, I received your message now what? (send a message to add)', 
            reply_markup = add_keyboard(c))
            return STATE_ADD

        def add_photo(u:Update, c:CallbackContext):
            c.user_data['messages'].append(
                {
                    'type': 'photo',
                    'photo': u.message.photo[-1],
                    'caption': u.message.caption,
                    'parser': c.user_data['parser']
                }
            )
            c.user_data['last-message'].delete()
            c.user_data['last-message'] = u.message.reply_text(
                'OK, I received photo%s now what? (send a message to add)'%('s' if len(u.message.photo)>1 else ''),
                reply_markup = add_keyboard(c))
            return STATE_ADD

        text_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton('✏️Edit', callback_data = 'edit'),
                InlineKeyboardButton('❌Delete', callback_data = 'delete')
            ]
        ])

        photo_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton('✏️Edit', callback_data = 'edit'),
                InlineKeyboardButton('📝Edit caption', callback_data = 'edit-cap'),
                InlineKeyboardButton('❌Delete', callback_data = 'delete')
            ]
        ])

        parse_error = r'😟 there is a problem, can not parse message\(s\)\. your message\(s\) may contain unescaped chars\.'+\
                        "\nplease escape all chars below with `'\\\\'`:\n"+\
                        "`'_', '*', '[', ']', '(', ')', '~', '\\`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'`\n"+\
                        "And also escape all `'\\`'` and `'\\\\'` inside pre and code entities\n"+\
                        "please fix this problem\\."

        def cleanup_last_preview(chat_id, c: CallbackContext):
            if 'prev-dict' in c.user_data:
                for msg_id in c.user_data['prev-dict']:
                    c.bot.edit_message_reply_markup(
                        chat_id,
                        msg_id,
                    )

        def preview(u: Update, c: CallbackContext):
            cleanup_last_preview(u.effective_chat.id, c)
            c.user_data['prev-dict'] = dict()
            chat = u.effective_chat
            for msg in c.user_data['messages']:
                if msg['type'] == 'text':
                    try:
                        msg_id = chat.send_message(
                            msg['text'],
                            parse_mode = msg['parser'],
                            reply_markup = text_markup
                        ).message_id
                    except BadRequest:
                        msg_id = chat.send_message(
                            msg['text']+'\n\n⚠️ CAN NOT PARSE.',
                            reply_markup = text_markup
                        ).message_id
                        c.user_data['had-error'] = True

                    c.user_data['prev-dict'][msg_id] = msg
                elif msg['type'] == 'photo':
                    try:
                        msg_id = chat.send_photo(
                            msg['photo'],
                            msg['caption'],
                            parse_mode = msg['parser'],
                            reply_markup = photo_markup
                        ).message_id
                    except BadRequest:
                        msg_id = chat.send_photo(
                            msg['photo'],
                            caption = msg['caption']+'\n\n⚠️ CAN NOT PARSE.',
                            reply_markup = photo_markup
                        ).message_id
                        c.user_data['had-error'] = True

                    c.user_data['prev-dict'][msg_id] = msg
                else:
                    logger.error('UNKNOWN MSG TYPE FOUND\n'+str(msg))
                    c.bot.send_message(self.ownerID, 'UNKNOWN MSG TYPE FOUND\n'+str(msg))

            if c.user_data.get('had-error'):
                c.user_data['last-message'] = u.message.reply_text(
                    parse_error,
                    parse_mode = ParseMode.MARKDOWN_V2,
                    reply_markup = add_keyboard(c))
            else:
                c.user_data['last-message'] = u.message.reply_text('OK, now what?  (send a message to add)',
                reply_markup = add_keyboard(c))
            return STATE_ADD

        def edit(u: Update, c: CallbackContext):
            query = u.callback_query
            edit_cap = query.data == 'edit-cap'
            query.answer()
            c.user_data['last-message'].delete()
            c.user_data['last-message'] = self.bot.send_message(u.effective_chat.id,
                '✏️ EDITING CAPTION\nSend new caption.' if edit_cap else '✏️ EDITING\nSend new edition.',
                reply_markup = ReplyKeyboardMarkup([['❌Cancel']],resize_keyboard = True))
            c.user_data['editing-prev-id'] = query.message.message_id
            c.user_data['edit-cap'] = edit_cap
            return STATE_EDIT

        def text_edited(u: Update, c:CallbackContext):
            if not u.message:
                return STATE_EDIT
            preview_msg_id = c.user_data['editing-prev-id']                             #id of the message that bot sent as preview
            msg = c.user_data['prev-dict'][preview_msg_id]                              #get msg by searcing preview message id in prev-dict
            edited_txt = u.message.text
            if msg.get('had-error'):
                del(msg['had-error'])
            if c.user_data.get('had-error'):
                del(c.user_data['had-error'])
            msg['parser'] = c.user_data['parser']
            if msg['type'] == 'text':
                msg['text'] = edited_txt                                                #change message text
                try:
                    c.bot.edit_message_text(                                            #edit preview message text
                        edited_txt,
                        u.effective_chat.id,
                        preview_msg_id,
                        parse_mode = msg['parser'],
                        reply_markup = text_markup
                    )
                except:
                    c.bot.edit_message_text(
                        edited_txt+'\n\n⚠️ CAN NOT PARSE.',
                        u.effective_chat.id,
                        preview_msg_id,
                        reply_markup = text_markup
                    )
                    msg['had-error'] = True
                    c.user_data['had-error'] = True
            elif msg['type'] == 'photo':
                if c.user_data['edit-cap']:
                    msg['caption'] = u.message.text
                    try:
                        c.bot.edit_message_caption(
                            u.effective_chat.id,
                            preview_msg_id,
                            caption = edited_txt,
                            parse_mode = msg['parser'],
                            reply_markup = photo_markup
                        )
                    except:
                        c.bot.edit_message_caption(
                            u.effective_chat.id,
                            preview_msg_id,
                            caption = edited_txt+'\n\n⚠️ CAN NOT PARSE.',
                            reply_markup = photo_markup
                        )
                        msg['had-error'] = True
                        c.user_data['had-error'] = True
                else:
                    #change message type from photo to text
                    msg['type'] = 'text'
                    del(msg['photo'], msg['caption'])
                    msg['text'] = edited_txt
                    c.bot.edit_message_caption(
                        caption = '⚠️ This message type had been changed from photo to text. '+\
                        'You can request for a new preview to see this message.',
                        chat_id = u.effective_chat.id,
                        message_id = preview_msg_id
                    )
            else:
                #Log this bug
                logger.error('UNKNOWN MSG TYPE FOUND\n'+str(msg))
                c.bot.send_message(self.ownerID, 'UNKNOWN MSG TYPE FOUND\n'+str(msg))

            if c.user_data.get('had-error'):
                c.user_data['last-message'] = u.message.reply_text(
                    parse_error,
                    parse_mode = ParseMode.MARKDOWN_V2,
                reply_markup = add_keyboard(c))
            else:
                c.user_data['last-message'] = u.message.reply_text('✅ Message edited; now you can add more messages or send it',
                reply_markup = add_keyboard(c))
            return STATE_ADD

        def photo_edited(u: Update, c: CallbackContext):
            preview_msg_id = c.user_data['editing-prev-id']                             #id of the message that bot sent as preview
            msg = c.user_data['prev-dict'][preview_msg_id]                              #get msg by searcing preview message id in prev-dict
            if msg.get('had-error'):
                del(msg['had-error'])
            if c.user_data.get('had-error'):
                del(c.user_data['had-error'])
            msg['parser'] = c.user_data['parser']
            if msg['type'] == 'photo':
                msg['photo'] = u.message.photo[-1]
                msg['caption'] = u.message.caption
                try:
                    c.bot.edit_message_media(
                        u.effective_chat.id,
                        preview_msg_id,
                        media = InputMediaPhoto(
                            media = msg['photo'],
                            caption = msg['caption'],
                            parse_mode = msg['parser'])
                    )
                except:
                    c.bot.edit_message_media(
                        u.effective_chat.id,
                        preview_msg_id,
                        media = InputMediaPhoto(
                            media = msg['photo'],
                            caption = msg['caption']+'\n\n⚠️ CAN NOT PARSE.')
                    )
                    msg['had-error'] = True
                    c.user_data['had-error'] = True
            elif msg['type'] == 'text':
                #change message type to photo
                msg['type'] = 'photo'
                del(msg['text'])
                msg['photo'] = u.message.photo[-1]
                msg['caption'] = u.message.caption
                c.bot.edit_message_text(
                    '⚠️ This message type had been changed from text to photo. '+\
                    'You can request for a new preview to see this message.',
                    u.effective_chat.id,
                    preview_msg_id,
                )
            else:
                #report bug
                logger.error('UNKNOWN MSG TYPE FOUND\n'+str(msg))
                c.bot.send_message(self.ownerID, 'UNKNOWN MSG TYPE FOUND\n'+str(msg))

            if c.user_data.get('had-error'):
                c.user_data['last-message'] = u.message.reply_text(
                    parse_error,
                    parse_mode = ParseMode.MARKDOWN_V2,
                reply_markup = add_keyboard(c))
            else:
                c.user_data['last-message'] = u.message.reply_text('✅ Message edited; now you can add more messages or send it',
                reply_markup = add_keyboard(c))
            return STATE_ADD

        def delete(u: Update, c: CallbackContext):
            query = u.callback_query
            query.answer('✅ Deleted')
            preview_msg_id = query.message.message_id
            msg = c.user_data['prev-dict'][preview_msg_id]
            c.user_data['messages'].remove(msg)
            del(c.user_data['prev-dict'][preview_msg_id])
            query.edit_message_text('❌')
            c.user_data['last-message'].delete()
            c.user_data['last-message'] = self.bot.send_message(
                u.effective_chat.id, 'OK, now you can send message to add', reply_markup = add_keyboard(c))
            return STATE_ADD

        def deleting(u: Update, c: CallbackContext):
            query = u.callback_query
            query.answer()
            query.edit_message_reply_markup(
                InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        '🛑 Are you sure?', callback_data = 'None')],
                    [InlineKeyboardButton('🔴 Yes', callback_data = 'yes'), InlineKeyboardButton(
                        '🟢 No', callback_data = 'no')]
                ])
            )
            c.user_data['last-message'].delete()
            c.user_data['last-message'] = self.bot.send_message(
                u.effective_chat.id, '⏳ Deleting a message...', reply_markup = ReplyKeyboardRemove())
            return STATE_DELETE

        def confirm(u: Update, c: CallbackContext):
            c.user_data['last-message'].delete()
            c.user_data['last-message'] = self.bot.send_message(u.effective_chat.id,
                'Are you sure, you want to send message' +
                ('s' if len(c.user_data['messages']) > 1 else '') +
                'to all users, goups and channels?',
                reply_markup = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("👍Yes, that's OK!", callback_data = 'yes'),
                            InlineKeyboardButton("✋No, stop!", callback_data = 'no')
                        ]
                    ]
                ))
            return STATE_CONFIRM

        def send(u: Update, c: CallbackContext):
            query = u.callback_query
            if c.user_data.get('had-error'):
                query.answer()
                u.effective_chat.send_message(
                    parse_error,
                    parse_mode = ParseMode.MARKDOWN_V2,
                    reply_markup = add_keyboard(c)
                )
                return STATE_ADD
            query.answer(
                '✅ Done\nSending message to all users, goups and channels', show_alert = True)
            self.logger.info('Sending message to chats')
            c.user_data['last-message'].delete()
            c.user_data['last-message'] = self.bot.send_message(u.effective_chat.id,
            '✅ Done\nSending message to all users, goups and channels')

            def send_message(chat_id):
                chat = c.bot.get_chat(chat_id)
                for msg in c.user_data['messages']:
                    #send message to admin for a debug!
                    if msg['type'] == 'text':
                        try:
                            chat.send_message(
                                msg['text'],
                                parse_mode = msg['parser']
                            ).message_id
                        except BadRequest:
                            chat.send_message(
                                msg['text']+'\n\n⚠️ CAN NOT PARSE.',
                                reply_markup = text_markup
                            )
                            c.user_data['had-error'] = True
                            msg['had-error'] = True
                            return STATE_ADD
                    elif msg['type'] == 'photo':
                        try:
                            chat.send_photo(
                                msg['photo'],
                                msg['caption'],
                                parse_mode = msg['parser']
                            ).message_id
                        except BadRequest:
                            chat.send_photo(
                                msg['photo'],
                                caption = msg['caption']+'\n\n⚠️ CAN NOT PARSE.'
                            ).message_id
                            c.user_data['had-error'] = True
                            msg['had-error'] = True
                            return STATE_ADD

            res = send_message(u.effective_chat.id)
            if res:
                u.effective_chat.send_message(
                    parse_error,
                    parse_mode = ParseMode.MARKDOWN_V2,
                    reply_markup = add_keyboard(c)
                )
                return res

            for chat_id in self.iter_all_chats():
                if chat_id == u.effective_chat.id:
                    send_message(chat_id)
            
            cleanup_last_preview(u.effective_chat.id, c)
            for key in ('messages', 'prev-dict', 'had-error', 'edit-cap', 'editing-prev-id'):
                if key in c.user_data:
                    del(c.user_data[key])
            return ConversationHandler.END

        def confirm_admin(u: Update, c: CallbackContext):
            query = u.callback_query
            if u.effective_user.id == self.ownerID:
                new_admin_id = int(query.data[7:])
                self.bot.send_message(
                    new_admin_id,
                    f'✅ Accepted, From now on, I know you as my admin')
                self.adminID.append(new_admin_id)
                self.__set_data__('adminID', self.adminID, DB = config_db)
                self.admin_token.remove(self.admins_pendding[new_admin_id])
                del(self.admins_pendding[new_admin_id])
                query.answer('✅ Accepted')
                query.message.edit_text(query.message.text+'\n\n✅ Accepted')
            else:
                query.answer()

        def decline_admin(u: Update, c: CallbackContext):
            query = u.callback_query
            if u.effective_user.id == self.ownerID:
                new_admin_id = int(query.data[8:])
                self.bot.send_message(
                    new_admin_id,
                    f"❌ Declined, Owner didn't accepted your request")
                self.admin_token.remove(self.admins_pendding[new_admin_id])
                del(self.admins_pendding[new_admin_id])
                query.answer('❌ Declined')
                query.message.edit_text(query.message.text+'\n\n❌ Declined')
            else:
                query.answer()

        def unknown_query(u: Update, c: CallbackContext):
            query = u.callback_query
            self.logger.warning('unknown query, query data:'+query.data)
            query.answer("❌ ERROR\nUnknown answer", show_alert = True,)

        def cancel(state) -> typing.Callable:
            _cancel = None
            if state in (STATE_ADD, STATE_CONFIRM):
                def _cancel(u: Update, c: CallbackContext):
                    for key in ('messages', 'prev-dict', 'had-error', 'edit-cap', 'editing-prev-id'):
                        if key in c.user_data:
                            del(c.user_data[key])

                    c.user_data['last-message'].delete()
                    c.user_data['last-message'] = self.bot.send_message(u.effective_chat.id,
                        'Canceled', reply_markup = ReplyKeyboardRemove())
                    return ConversationHandler.END
            elif state == STATE_EDIT:
                def _cancel(u: Update, c: CallbackContext):
                    for key in ('edit-cap', 'editing-prev-id'):
                        if key in c.user_data:
                            del(c.user_data[key])
                    return STATE_ADD
            elif state == STATE_DELETE:
                def _cancel(u: Update, c: CallbackContext):
                    query = u.callback_query
                    query.answer('❌ Canceled')
                    query.edit_message_reply_markup(
                        InlineKeyboardMarkup([
                            [InlineKeyboardButton('✏️Edit', callback_data = 'edit'), InlineKeyboardButton(
                                '❌Delete', callback_data = 'delete')]
                        ]))
                    c.user_data['last-message'].delete()
                    c.user_data['last-message'] = self.bot.send_message(
                        u.effective_chat.id, 
                        'OK, now what?  (send a message to add)',
                        reply_markup = add_keyboard(c))
                    return STATE_ADD
            return _cancel

        send_all_conv_handler = ConversationHandler(
            entry_points = [CommandHandler('sendall', sendall)],
            states = {
                STATE_ADD: [
                    MessageHandler(Filters.regex("^✅Send$"), confirm),
                    MessageHandler(Filters.regex("^👁Preview$"), preview),
                    MessageHandler(Filters.regex(
                        "^❌Cancel$"), cancel(STATE_ADD)),
                    MessageHandler(Filters.regex("^✅ Markdown Enabled$")|Filters.regex("^◻️ Markdown Disabled$"), toggle_markdown),
                    MessageHandler(Filters.text, add_text),
                    MessageHandler(Filters.photo, add_photo)
                ],
                STATE_EDIT: [
                    MessageHandler(Filters.regex(
                        "^❌Cancel$"), cancel(STATE_EDIT)),
                    MessageHandler(Filters.regex("^✅ Markdown Enabled$")|Filters.regex("^◻️ Markdown Disabled$"), toggle_markdown),
                    MessageHandler(Filters.text, text_edited),
                    MessageHandler(Filters.photo, photo_edited)
                ],
                STATE_DELETE: [
                    CallbackQueryHandler(cancel(STATE_DELETE), pattern = '^no$'),
                    CallbackQueryHandler(delete, pattern = '^yes$'),
                ],
                STATE_CONFIRM: [
                    CallbackQueryHandler(send, pattern = '^yes$'),
                    CallbackQueryHandler(cancel(STATE_CONFIRM), pattern = '^no$')
                ]
            },
            fallbacks = [
                CallbackQueryHandler(edit, pattern = '^edit(-cap)?$'),
                CallbackQueryHandler(deleting, pattern = '^delete$'),
                CallbackQueryHandler(unknown_query, pattern = '.*')
            ],
            per_user = True
        )
        self.dispatcher.add_handler(send_all_conv_handler)
        self.dispatcher.add_handler(CallbackQueryHandler(
            confirm_admin, pattern = 'accept-.*'))
        self.dispatcher.add_handler(CallbackQueryHandler(
            decline_admin, pattern = 'decline-.*'))

        def onjoin(u: Update, c: CallbackContext):
            for member in u.message.new_chat_members:
                if member.username == self.bot.username:
                    data = u.effective_chat.to_dict()
                    data['members-count'] = u.effective_chat.get_members_count()-1
                    self.__set_data__(key = str(u.effective_chat.id), value = data)
                    self.bot.send_message(
                        self.ownerID,
                        '<i>Joined to a chat:</i>\n' +
                            html.escape(json.dumps(
                                data, indent = 2, ensure_ascii = False)),
                        ParseMode.HTML,
                        disable_notification = True)
                    if u.effective_chat.type != Chat.CHANNEL:
                        u.message.reply_markdown_v2(
                            self.get_string('group-intro'))

        def onkick(u: Update, c: CallbackContext):
            if u.message.left_chat_member['username'] == self.bot.username:
                data = self.__get_data__(str(u.effective_chat.id))
                if data:
                    self.bot.send_message(
                        self.ownerID,
                        '<i>Kicked from a chat:</i>\n' +
                            html.escape(json.dumps(
                                data, indent = 2, ensure_ascii = False)),
                        ParseMode.HTML,
                        disable_notification = True)
                    with self.env.begin(self.chats_db, write = True) as txn:
                        txn.delete(str(u.effective_chat.id).encode())

        self.dispatcher.add_handler(MessageHandler(
            Filters.status_update.new_chat_members, onjoin))
        self.dispatcher.add_handler(MessageHandler(
            Filters.status_update.left_chat_member, onkick))

        @self.message_handler(Filters.command)
        def unknown(u: Update, c: CallbackContext):
            logging.warning('Unknown handeled command: "'+u.message.text+'"')
            u.message.reply_text(self.get_string('unknown'))

        self.__unknown__ = unknown

        # unknown commands and messages handler (register as last handler)
        @self.message_handler(Filters.all)
        def unknown_msg(u: Update, c: CallbackContext):
            u.message.reply_text(self.get_string('unknown-msg'))

        def error_handler(update: object, context: CallbackContext) -> None:
            """Log the error and send a telegram message to notify the developer."""
            # Log the error before we do anything else, so we can see it even if something breaks.
            logger.error(msg = "Exception while handling an update:",
                         exc_info = context.error)

            # traceback.format_exception returns the usual python message about an exception, but as a
            # list of strings rather than a single string, so we have to join them together.
            tb_list = traceback.format_exception(
                None, context.error, context.error.__traceback__)
            tb_string = ''.join(tb_list)
            line_no = context.error.__traceback__.tb_lineno
            exception_type = type(context.error).__name__
            if self.reporter:
                self.reporter.bug(f'{line_no}: {exception_type}',tb_string)

            # Build the message with some markup and additional information about what happened.
            # You might need to add some logic to deal with messages longer than the 4096 character limit.
            update_str = update.to_dict() if isinstance(update, Update) else str(update)
            message = (
                f'An exception was raised while handling an update\n'
                f'<pre>update = {html.escape(json.dumps(update_str, indent = 2, ensure_ascii = False))}'
                '</pre>\n\n'
                f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
                f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
                f'<pre>{html.escape(tb_string)}</pre>'
            )

            # Finally, send the message
            context.bot.send_message(
                chat_id = self.ownerID, text = message, parse_mode = ParseMode.HTML)

        self.dispatcher.add_error_handler(error_handler)

    # ----------------------------------------------------

    def read_feed(self):
        feeds_xml = None
        with urlopen(self.source) as f:
            feeds_xml = f.read().decode('utf-8')
        if feeds_xml:
            soup_page = BeautifulSoup(feeds_xml, 'xml')
            feeds_list = soup_page.findAll("item")
            purge = re.compile(r'</?(?!(?:%s)\b)\w+[^>]*/?>'%SUPPORTED_HTML_TAGS).sub      #This regex will purge any unsupported tag
            skip = re.compile(r'</?[^>]*name = "skip"[^>]*>').match               #This regex will search for a tag named as "skip" like: <any name = "skip">
            for feed in feeds_list:
                description = str(feed.description.text)
                if not skip(description):     #if regex found something skip this post
                    soup = BeautifulSoup(purge('', description), 'html.parser')
                    for tag in soup.descendants:
                        #Remove any unsupported attribute
                        if tag.name in SUPPORTED_TAG_ATTRS:
                            attr = SUPPORTED_TAG_ATTRS[tag.name]
                            if attr in tag.attrs:
                                tag.attrs = {attr: tag[attr]}
                        else:
                            tag.attrs = dict()
                    #End for tag
                    description = str(soup)
                    messages = [{'type': 'text', 'text': description, 'markup': None}]
                    #Handle images
                    images = soup.find_all('img')
                    first = True
                    if images:
                        for img in images:
                            sep = str(img)
                            have_link = img.parent.name == 'a'
                            if have_link:
                                sep = str(img.parent)
                            first_part, description = description.split(sep, 1)
                            if first:   #for first message
                                if first_part != '':
                                    messages[0] = {'type': 'text', 'text': first_part, 'markup': None}
                                    msg = {'type': 'image',
                                    'src': img['src'], 'markup': None}
                                    if have_link:
                                        msg['markup'] = [[InlineKeyboardButton('Open image link', img.parent['href'])]]
                                    messages.append(msg)
                                else:
                                    msg = {'type': 'image', 'src': img['src'], 'markup': None}
                                    if have_link:
                                        msg['markup'] = [[InlineKeyboardButton('Open image link', img.parent['href'])]]
                                    messages[0] = msg
                                first = False
                            else:
                                messages[-1]['text'] = first_part
                                msg = {'type': 'image',
                                    'src': img['src'], 'markup': None}
                                if have_link:
                                    msg['markup'] = [[InlineKeyboardButton('Open image link', img.parent['href'])]]
                                messages.append(msg)
                        #End for img
                        messages[-1]['text'] = description
                    #End if images
                    return feed, messages
        else:
            return None

    def send_feed(self, feed, messages, msg_header, chat_ids):
        if len(messages) != 0:
            if messages[-1]['markup']:
                messages[-1]['markup'].append(
                    [InlineKeyboardButton('View post', str(feed.link.text))])
            else:
                messages[-1]['markup'] = [[InlineKeyboardButton('View post', str(feed.link.text))]]
            
            msg_header = '<i>%s</i>\n\n<b><a href = "%s">%s</a></b>\n' % (
                msg_header, feed.link.text, feed.title.text)
            messages[0]['text'] = msg_header+messages[0]['text']
            for chat_id in chat_ids:
                for msg in messages:
                    if msg['type'] == 'text':
                        self.bot.send_message(
                            chat_id,
                            msg['text'],
                            parse_mode = ParseMode.HTML,
                            reply_markup = InlineKeyboardMarkup(msg['markup']) if msg['markup'] else None
                        )
                    elif msg['type'] == 'image':
                        if msg['text'] == '':
                            msg['text'] = None
                        self.bot.send_photo(
                            chat_id,
                            msg['src'],
                            msg['text'],
                            parse_mode = ParseMode.HTML,
                            reply_markup = InlineKeyboardMarkup(msg['markup']) if msg['markup'] else None
                        )

    def iter_all_chats(self):
        self.logger.info('sending last feed to users')
        with env.begin(self.chats_db) as txn:
            for key, value in txn.cursor():
                yield key.decode()

    def check_new_feed(self):
        feed, messages = self.read_feed()
        if feed:
            date = self.__get_data__('last-feed-date', DB = self.config_db)
            if date:
                feed_date = parse(feed.pubDate.text)
                if feed_date > date:
                    self.__set_data__('last-feed-date',
                                      feed_date, DB = self.config_db)
                    self.send_feed(feed, messages, self.get_string('new-feed'), self.iter_all_chats())
            else:
                feed_date = parse(feed.pubDate.text)
                self.__set_data__('last-feed-date',
                                  feed_date, DB = self.config_db)
                self.send_feed(feed, messages, self.get_string('new-feed'), self.iter_all_chats())
        if self.__check__:
            self.check_thread = Timer(self.interval, self.check_new_feed)
            self.check_thread.start()


    def __get_data__(self, key, default = None, DB = None, do = lambda data: pickle.loads(data)):
        DB = DB if DB else self.chats_db
        data = None
        with self.env.begin(DB) as txn:
            data = txn.get(key.encode(), default)
        if data is not default and callable(do):
            return do(data)
        else:
            return data

    def __set_data__(self, key, value, over_write = True, DB = None, do = lambda data: pickle.dumps(data)):
        DB = DB if DB else self.chats_db
        if not callable(do):
            do = lambda data: data
        with self.env.begin(DB, write = True) as txn:
            return txn.put(key.encode(), do(value), overwrite = over_write)

    def get_string(self, string_name):
        return ''.join(self.strings[string_name])

    def run(self):
        self.updater.start_polling()
        # check for new feed
        self.check_new_feed()

    def idle(self):
        self.updater.idle()
        self.updater.stop()
        self.__check__ = False
        self.check_thread.cancel()
        if self.check_thread.is_alive():
            self.check_thread.join()


if __name__ == '__main__':
    argv = sys.argv
    if '-h' in argv:
        print(
            """PCWorms RSS telegram bot usage
\t-t <token>\tspecify bot token for first use. Token will save in db/config/token for future use.
\t-s <feeds url>\tdetermine feeds source url. (for first time)
""")
    logging.basicConfig(
        format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)
    logger = logging.getLogger()
    env = lmdb.open(DB_PATH, max_dbs = 3)

    if '-r' in argv and len(argv) > 1:
        db_to_drop = argv[argv.index('-r')+1]
        if db_to_drop in ('config', 'chats', 'all'):
            answer = input(f'Are you sure you want to Remove "{db_to_drop}" databases?(yes/any)')
            if answer != 'yes':
                exit()
            elif db_to_drop != 'all':
                db = env.open_db(db_to_drop.encode())
                with env.begin(db, write = True) as txn:
                    d = env.open_db()
                    txn.drop(d)
            else:
                for db_to_drop in ('config', 'chats'):
                    db = env.open_db(db_to_drop.encode())
                    with env.begin(db, write = True) as txn:
                        d = env.open_db()
                        txn.drop(d)
            exit()

    config_db = env.open_db(b'config')
    chats_db = env.open_db(b'chats')
    token = ''
    source = ''
    language = 'en-us'
    strings = None
    if not os.path.exists(STRINGS_PATH):
        STRINGS_PATH = 'default-strings.json'
    with open(STRINGS_PATH, encoding = 'utf8') as fp:
        strings = json.load(fp)

    bug_reporter = None
    reporter = None
    web_reporter = False

    if '-b' in argv:
        port = None
        if len(argv)>1:
            next_arg = argv[argv.index('-b')+1]
            if not next_arg.startswith('-'):
                if next_arg.isdigit():
                    port = int(next_arg)
                    port = port if 1023 < port < 65354 else None
        import BugReporter
        bug_reporter = BugReporter.BugReporter()
        reporter = bug_reporter('Telegram_RSS_Bot')
        
        if port:
            import cherrypy #user can ignore installing this mudole if now need for http reporting
            conf = {'global':
                {
                    "server.socket_host": '0.0.0.0',
                    "server.socket_port": port
                },
                'log.screen': False
            }
            import cherrypy
            class root:
                def __init__(self, reporter):
                    self.reporter = reporter

                @cherrypy.expose
                def index(self):
                    res = '''<html style="weidth:100%"><body><h1>Bugs</h1><hr>
                    <b>what is this page?</b> this project is using a simple 
                    web server to report bugs(exceptions) that found in a running program.
                    <h2>Bug logs</h2><pre language="json" style="weidth:100%;overflow:auto">'''+html.escape(self.reporter.dumps())+'</pre></body></html>'
                    return res

                @cherrypy.expose
                @cherrypy.tools.json_out()
                def json(self):
                    return self.reporter.reports

            cherrypy.config.update(conf)
            cherrypy.tree.mount(root(bug_reporter),'/')
            cherrypy.engine.start()
            web_reporter = True
            
            logger.info(f'reporting bugs at {port} and saving them in bugs.json')
        else:
            logger.info(f'saving bugs in {path}')

    with env.begin(config_db, write = True) as txn:
        if '-t' in argv and len(argv) > 1:
            token = argv[argv.index('-t')+1]
            txn.put(b'token', token.encode())
        else:
            token = txn.get(b'token', b'').decode()
        
        if '-l' in argv and len(argv) > 1:
            language = argv[argv.index('-l')+1].lower()
            txn.put(b'language', token.encode())
        else:
            language = txn.get(b'language', b'').decode()

        if '-s' in argv and len(argv) > 1:
            source = argv[argv.index('-s')+1]
            txn.put(b'source', source.encode())
        else:
            source = txn.get(
                b'source', b'https://pcworms.blog.ir/rss/').decode()
                

    if token == '':
            logger.error("No Token, exiting")
            sys.exit()

    if language in strings:
        strings = strings[language]
    else:
        logger.warning('Specified language is not supported, using "en-us" language.')
        logger.info('You can find all strings in "strings.json" file for available languages or translating')
        strings = strings['en-us']

    bot_handler = BotHandler(logger, token, source, env,
                             chats_db, config_db, strings, reporter)
    bot_handler.run()
    bot_handler.idle()
    if bug_reporter:
        logger.info('saving bugs report')
        bug_reporter.dump()
    if web_reporter:
        logger.info('stoping web reporter')
        cherrypy.engine.stop()
    env.close()
    
