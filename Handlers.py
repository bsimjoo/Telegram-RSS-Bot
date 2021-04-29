import html
import json
import logging
import pickle
import random
import string
import BugReporter
from datetime import datetime, timedelta

from dateutil.parser import parse
from telegram import (Chat, ChatMember, InlineKeyboardButton,
                      InlineKeyboardMarkup, InputMediaPhoto, ParseMode,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.bot import Bot
from telegram.error import BadRequest, NetworkError, Unauthorized
from telegram.ext import (BaseFilter, CallbackContext, CallbackQueryHandler,
                          ChatMemberHandler, CommandHandler,
                          ConversationHandler, Filters, MessageHandler,
                          Updater)
from telegram.utils.helpers import DEFAULT_NONE

from decorators import (CommandHandlerDecorator, ConversationDecorator,
                        DispatcherDecorators, HandlerDecorator, auth, MessageHandlerDecorator)
from main import BotHandler

# pylint: disable=unused-variable

def add_owner_handlers(server: BotHandler):

    def unknown_query(u: Update, c: CallbackContext):
        query = u.callback_query
        logging.debug('unknown query, query data:'+query.data)
        query.answer("❌ ERROR\nUnknown answer", show_alert = True,)

    def unknown_command(u: Update, c: CallbackContext):
        u.message.reply_text(server.get_string('unknown'))

    dispatcher_decorators = DispatcherDecorators(server.dispatcher)

    @dispatcher_decorators.commandHandler
    @auth(server.ownerID, unknown_command)
    def gentoken(u: Update, c: CallbackContext):
        admin_token = ''.join(
            [random.choice(string.ascii_letters+string.digits) for x in range(32)])
        server.admin_token.append(admin_token)
        u.message.reply_html((
            'one-time admin token:\n<pre>'
            f'{admin_token}'
            '</pre>\n<i>Send this token to anyone you want to promote as admin'
        ))

    # TODO:availability of removing admins feature
    # labels: enhancement

    @dispatcher_decorators.addHandler
    @HandlerDecorator(CallbackQueryHandler,pattern = 'accept-.*')
    @auth(server.ownerID, unknown_query)
    def confirm_admin(u: Update, c: CallbackContext):
        query = u.callback_query
        if u.effective_user.id == server.ownerID:
            new_admin_id = int(query.data[7:])
            server.bot.send_message(
                new_admin_id,
                f'✅ Accepted, From now on, I know you as my admin')
            server.adminID.append(new_admin_id)
            server.__set_data__('adminID', server.adminID, DB = server.data_db)
            server.admin_token.remove(server.admins_pendding[new_admin_id])
            del(server.admins_pendding[new_admin_id])
            query.answer('✅ Accepted')
            query.message.edit_text(query.message.text+'\n\n✅ Accepted')
        else:
            query.answer()

    @dispatcher_decorators.addHandler
    @HandlerDecorator(CallbackQueryHandler,pattern = 'decline-.*')
    @auth(server.ownerID, unknown_query)
    def decline_admin(u: Update, c: CallbackContext):
        query = u.callback_query
        if u.effective_user.id == server.ownerID:
            new_admin_id = int(query.data[8:])
            server.bot.send_message(
                new_admin_id,
                f"❌ Declined, Owner didn't accepted your request")
            server.admin_token.remove(server.admins_pendding[new_admin_id])
            del(server.admins_pendding[new_admin_id])
            query.answer('❌ Declined')
            query.message.edit_text(query.message.text+'\n\n❌ Declined')
        else:
            query.answer()

def add_debuging_handlers(server: BotHandler):
    def unknown_command(u: Update, c: CallbackContext):
        u.message.reply_text(server.get_string('unknown'))

    dispatcher_decorators = DispatcherDecorators(server.dispatcher)

    @dispatcher_decorators.messageHandler(Filters.update, group=0)
    def log_update(u: Update, c: CallbackContext):
        message = (
            'Received a new update event from telegram\n'
            f'update = {json.dumps(u.to_dict(), indent = 2, ensure_ascii = False)}\n'
            f'user_data = {json.dumps(c.user_data, indent = 2, ensure_ascii = False)}\n'
            f'chat_data = {json.dumps(c.chat_data, indent = 2, ensure_ascii = False)}'
        )
        logging.info(message)
        if server.debug:
            try:
                server.bot.send_message(server.ownerID, html.escape(
                    message), parse_mode=ParseMode.HTML)
            except BaseException as e:
                server.log_bug(e, 'Exception while sending update log to owner',
                               ownerID=server.ownerID, message=html.escape(message))

    @dispatcher_decorators.commandHandler
    @auth(server.ownerID, unknown_command)
    def log_updates(u: Update, c: CallbackContext):
        server.debug = not server.debug
        if server.debug:
            u.message.reply_text(
                'Debug enabled. now bot sends all updates for you')
        else:
            u.message.reply_text('Debug disabled.')

def add_admin_handlers(server: BotHandler):
    def unknown_msg(u: Update, c: CallbackContext):
        u.message.reply_text(server.get_string('unknown-msg'))

    def unknown_command(u: Update, c: CallbackContext):
        u.message.reply_text(server.get_string('unknown'))

    dispatcher_decorators = DispatcherDecorators(server.dispatcher)
    admin_auth = auth(server.adminID, unknown_command)

    @dispatcher_decorators.commandHandler
    @admin_auth
    def my_level(u: Update, c: CallbackContext):
        if u.effective_user.id == server.ownerID:
            u.message.reply_text(
                'Oh, my lord. I respect you.')
        elif u.effective_user.id in server.adminID:
            u.message.reply_text('Oh, my admin. Hi, How are you?')

    @dispatcher_decorators.commandHandler
    @admin_auth
    def state(u: Update, c: CallbackContext):
        members, chats = 0, 0
        msg = u.message.reply_text('⏳ Please wait, counting members...')
        with server.env.begin(server.chats_db) as txn:
            chats = int(txn.stat()["entries"])
            for key, value in txn.cursor():
                v = pickle.loads(value)
                members += v['members-count']
        msg.edit_text(
            f'👥chats:\t{chats}\n' +
            f'👤members:\t{members}\n' +
            f'🤵admins:\t{len(server.adminID)}'
        )

    @dispatcher_decorators.commandHandler
    @admin_auth
    def listchats(u: Update, c: CallbackContext):
        res = ''
        with server.env.begin(server.chats_db) as txn:
            res = 'total: '+str(txn.stat()["entries"])+'\n'
            for key, value in txn.cursor():
                chat = pickle.loads(value)
                if type(chat) is not type(dict()):
                    res += html.escape(
                        f'\n bad data type; type:{type(chat)}, value:{chat}\n')
                    continue
                if 'username' in chat:
                    chat['username'] = '@'+chat['username']
                res += html.escape(json.dumps(chat,
                                              indent=2, ensure_ascii=False))
        u.message.reply_html(res)

    @dispatcher_decorators.commandHandler
    @admin_auth
    def send_feed_toall(u: Update, c: CallbackContext):
        server.send_feed(
            *server.read_feed(), server.get_string('last-feed'), server.iter_all_chats())

    @dispatcher_decorators.commandHandler
    @admin_auth
    def set_interval(u: Update, c: CallbackContext):
        if len(c.args) == 1:
            if c.args[0].isdigit():
                server.interval = int(c.args[0])
                server.set_data(
                    'interval', server.interval, server.data_db)
                u.message.reply_text(
                    '✅ Interval changed to'+str(server.interval))
                return
        u.message.reply_markdown_v2(
            '❌ Bad command, use `/set_interval {new interval in seconds}`')

    def add_keyboard(c: CallbackContext):
        'A function that create keyboard that needed in send_all conversation'
        keys = ['❌Cancel']
        if len(c.user_data['messages']):
            keys = ['✅Send', '👁Preview', '❌Cancel']
        markdown = c.user_data['parser'] == ParseMode.HTML
        return ReplyKeyboardMarkup(
            [
                [('✅ HTML Enabled' if markdown else '◻️ HTML Disabled')],
                keys
            ],
            resize_keyboard=True
        )

    STATE_ADD, STATE_EDIT, STATE_DELETE, STATE_CONFIRM = range(4)

    @CommandHandlerDecorator
    @admin_auth
    def sendall(u: Update, c: CallbackContext):
        if u.effective_chat.type != Chat.PRIVATE:
            u.message.reply_text(
                '❌ ERROR\nthis command only is available in private')
            return ConversationHandler.END
        c.user_data['last-message'] = u.message.reply_text(
            'You can send text or photo.', disable_notification=True)
        c.user_data['messages'] = []
        c.user_data['parser'] = DEFAULT_NONE
        u.message.reply_text(
            'OK, Send a message to forward it to all users',
            reply_markup=add_keyboard(c))

        return STATE_ADD

    sendall_conv_handler = ConversationDecorator([sendall], per_user=True)

    @sendall_conv_handler.state(STATE_ADD)
    @MessageHandlerDecorator(Filters.regex("^✅Send$"))
    def confirm(u: Update, c: CallbackContext):
        c.user_data['last-message'].delete()
        c.user_data['last-message'] = server.bot.send_message(
            u.effective_chat.id,
            'Are you sure, you want to send message' +
            ('s' if len(c.user_data['messages']) > 1 else '') +
            'to all users, groups and channels?',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "👍Yes, that's OK!", callback_data='yes'),
                        InlineKeyboardButton(
                            "✋No, stop!", callback_data='no')
                    ]
                ]
            )
        )
        return STATE_CONFIRM

    text_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✏️Edit', callback_data='edit'),
            InlineKeyboardButton('❌Delete', callback_data='delete')
        ]
    ])

    photo_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✏️Edit', callback_data='edit'),
            InlineKeyboardButton('📝Edit caption', callback_data='edit-cap'),
            InlineKeyboardButton('❌Delete', callback_data='delete')
        ]
    ])

    def cleanup_last_preview(chat_id, c: CallbackContext):
        if 'prev-dict' in c.user_data:
            for msg_id in c.user_data['prev-dict']:
                c.bot.edit_message_reply_markup(
                    chat_id,
                    msg_id,
                )

    def cancel(state) -> callable:
        _cancel = None
        if state in (STATE_ADD, STATE_CONFIRM):
            def _cancel(u: Update, c: CallbackContext):
                for key in ('messages', 'prev-dict', 'had-error', 'edit-cap', 'editing-prev-id'):
                    if key in c.user_data:
                        del(c.user_data[key])

                c.user_data['last-message'].delete()
                c.user_data['last-message'] = server.bot.send_message(u.effective_chat.id,
                                                                      'Canceled', reply_markup=ReplyKeyboardRemove())
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
                        [InlineKeyboardButton('✏️Edit', callback_data='edit'), InlineKeyboardButton(
                            '❌Delete', callback_data='delete')]
                    ]))
                c.user_data['last-message'].delete()
                c.user_data['last-message'] = server.bot.send_message(
                    u.effective_chat.id,
                    'OK, now what?  (send a message to add)',
                    reply_markup=add_keyboard(c))
                return STATE_ADD
        return _cancel

    @sendall_conv_handler.state(STATE_ADD)
    @MessageHandlerDecorator(Filters.regex("^👁Preview$"))
    def preview(u: Update, c: CallbackContext):
        cleanup_last_preview(u.effective_chat.id, c)
        c.user_data['prev-dict'] = dict()
        chat = u.effective_chat
        for msg in c.user_data['messages']:
            if msg['type'] == 'text':
                try:
                    msg_id = chat.send_message(
                        msg['text'],
                        parse_mode=msg['parser'],
                        reply_markup=text_markup
                    ).message_id
                except BadRequest as ex:
                    msg_id = chat.send_message(
                        msg['text']+'\n\n⚠️ CAN NOT PARSE.\n'+ex.message,
                        reply_markup=text_markup
                    ).message_id
                    c.user_data['had-error'] = True

                c.user_data['prev-dict'][msg_id] = msg
            elif msg['type'] == 'photo':
                try:
                    msg_id = chat.send_photo(
                        msg['photo'],
                        msg['caption'],
                        parse_mode=msg['parser'],
                        reply_markup=photo_markup
                    ).message_id
                except BadRequest as ex:
                    msg_id = chat.send_photo(
                        msg['photo'],
                        caption=msg['caption'] +
                        '\n\n⚠️ CAN NOT PARSE.\n'+ex.message,
                        reply_markup=photo_markup
                    ).message_id
                    c.user_data['had-error'] = True

                c.user_data['prev-dict'][msg_id] = msg
            else:
                logging.error('UNKNOWN MSG TYPE FOUND\n'+str(msg))
                c.bot.send_message(
                    server.ownerID, 'UNKNOWN MSG TYPE FOUND\n'+str(msg))
                BugReporter.bug('unknown type message in preview',
                                'UNKNOWN MSG TYPE FOUND\n'+str(msg))

        if c.user_data.get('had-error'):
            c.user_data['last-message'] = u.message.reply_text(
                '🛑 there is a problem with your messages, please fix them.',
                reply_markup=add_keyboard(c))
        else:
            c.user_data['last-message'] = u.message.reply_text('OK, now what?  (send a message to add)',
                                                               reply_markup=add_keyboard(c))
        return STATE_ADD

    sendall_conv_handler.state(STATE_ADD)(
        MessageHandler(Filters.regex("^❌Cancel$"), cancel(STATE_ADD))
    )

    @sendall_conv_handler.state(STATE_ADD, STATE_EDIT)
    @MessageHandlerDecorator(Filters.regex("^✅ HTML Enabled$") | Filters.regex("^◻️ HTML Disabled$"))
    def toggle_markdown(u: Update, c: CallbackContext):
        if c.user_data['parser'] == ParseMode.HTML:
            c.user_data['parser'] = DEFAULT_NONE
            u.message.reply_text('◻️ HTML Disabled',
                                 reply_markup=add_keyboard(c))
        else:
            c.user_data['parser'] = ParseMode.HTML
            u.message.reply_text(
                '✅ HTML Enabled', reply_markup=add_keyboard(c))

    @sendall_conv_handler.state(STATE_ADD)
    @MessageHandlerDecorator(Filters.text)
    def add_text(u: Update, c: CallbackContext):
        text = u.message.text
        if c.user_data['parser'] == ParseMode.HTML:
            text = str(server.purge(text, False))

        c.user_data['messages'].append(
            {
                'type': 'text',
                'text': text,
                'parser': c.user_data['parser']
            }
        )
        c.user_data['last-message'].delete()
        c.user_data['last-message'] = u.message.reply_text('OK, I received your message now what? (send a message to add)',
                                                           reply_markup=add_keyboard(c))
        return STATE_ADD

    @sendall_conv_handler.state(STATE_ADD)
    @MessageHandlerDecorator(Filters.photo)
    def add_photo(u: Update, c: CallbackContext):
        text = u.message.caption
        if c.user_data['parser'] == ParseMode.HTML:
            text = str(server.purge(text, False))
        c.user_data['messages'].append(
            {
                'type': 'photo',
                'photo': u.message.photo[-1],
                'caption': text,
                'parser': c.user_data['parser']
            }
        )
        c.user_data['last-message'].delete()
        c.user_data['last-message'] = u.message.reply_text(
            'OK, I received photo%s now what? (send a message to add)' % (
                's' if len(u.message.photo) > 1 else ''),
            reply_markup=add_keyboard(c))
        return STATE_ADD

    sendall_conv_handler.state(STATE_EDIT)(
        MessageHandler(Filters.regex("^❌Cancel$"), cancel(STATE_EDIT))
    )

    @sendall_conv_handler.fallback
    @HandlerDecorator(CallbackQueryHandler, pattern='^edit(-cap)?$')
    def edit(u: Update, c: CallbackContext):
        query = u.callback_query
        edit_cap = query.data == 'edit-cap'
        query.answer()
        c.user_data['last-message'].delete()
        c.user_data['last-message'] = server.bot.send_message(u.effective_chat.id,
                                                              '✏️ EDITING CAPTION\nSend new caption.' if edit_cap else '✏️ EDITING\nSend new edition.',
                                                              reply_markup=ReplyKeyboardMarkup([['❌Cancel']], resize_keyboard=True))
        c.user_data['editing-prev-id'] = query.message.message_id
        c.user_data['edit-cap'] = edit_cap
        return STATE_EDIT

    @sendall_conv_handler.state(STATE_EDIT)
    @MessageHandlerDecorator(Filters.text)
    def text_edited(u: Update, c: CallbackContext):
        if not u.message:
            return STATE_EDIT
        # id of the message that bot sent as preview
        preview_msg_id = c.user_data['editing-prev-id']
        # get msg by searching preview message id in prev-dict
        msg = c.user_data['prev-dict'][preview_msg_id]
        edited_txt = u.message.text
        if c.user_data['parser'] == ParseMode.HTML:
            edited_txt = str(server.purge(edited_txt, False))
        if msg.get('had-error'):
            del(msg['had-error'])
        if c.user_data.get('had-error'):
            del(c.user_data['had-error'])
        msg['parser'] = c.user_data['parser']
        if msg['type'] == 'text':
            msg['text'] = edited_txt  # change message text
            try:
                c.bot.edit_message_text(  # edit preview message text
                    edited_txt,
                    u.effective_chat.id,
                    preview_msg_id,
                    parse_mode=msg['parser'],
                    reply_markup=text_markup
                )
            except BadRequest as ex:
                c.bot.edit_message_text(
                    edited_txt+'\n\n⚠️ CAN NOT PARSE.\n'+ex.message,
                    u.effective_chat.id,
                    preview_msg_id,
                    reply_markup=text_markup
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
                        caption=edited_txt,
                        parse_mode=msg['parser'],
                        reply_markup=photo_markup
                    )
                except BadRequest as ex:
                    c.bot.edit_message_caption(
                        u.effective_chat.id,
                        preview_msg_id,
                        caption=edited_txt+'\n\n⚠️ CAN NOT PARSE.\n'+ex.message,
                        reply_markup=photo_markup
                    )
                    msg['had-error'] = True
                    c.user_data['had-error'] = True
            else:
                # change message type from photo to text
                msg['type'] = 'text'
                del(msg['photo'], msg['caption'])
                msg['text'] = edited_txt
                c.bot.edit_message_caption(
                    caption='⚠️ This message type had been changed from photo to text. ' +
                    'You can request for a new preview to see this message.',
                    chat_id=u.effective_chat.id,
                    message_id=preview_msg_id
                )
        else:
            # Log this bug
            logging.error('UNKNOWN MSG TYPE FOUND\n'+str(msg))
            c.bot.send_message(
                server.ownerID, 'UNKNOWN MSG TYPE FOUND\n'+str(msg))

        if c.user_data.get('had-error'):
            c.user_data['last-message'] = u.message.reply_text(
                '🛑 there is a problem with your messages, please fix them.',
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=add_keyboard(c))
        else:
            c.user_data['last-message'] = u.message.reply_text('✅ Message edited; now you can add more messages or send it',
                                                               reply_markup=add_keyboard(c))
        return STATE_ADD

    @sendall_conv_handler.state(STATE_EDIT)
    @MessageHandlerDecorator(Filters.photo)
    def photo_edited(u: Update, c: CallbackContext):
        # id of the message that bot sent as preview
        preview_msg_id = c.user_data['editing-prev-id']
        # get msg by searching preview message id in prev-dict
        msg = c.user_data['prev-dict'][preview_msg_id]
        if msg.get('had-error'):
            del(msg['had-error'])
        if c.user_data.get('had-error'):
            del(c.user_data['had-error'])
        msg['parser'] = c.user_data['parser']
        msg['photo'] = u.message.photo[-1]
        msg['caption'] = u.message.caption
        if c.user_data['parser'] == ParseMode.HTML:
            msg['caption'] = str(server.purge(msg['caption'], False))
        if c.user_data['parser'] == ParseMode.MARKDOWN_V2:
            msg['caption'] = u.message.caption_markdown_v2

        if msg['type'] == 'photo':
            try:
                c.bot.edit_message_media(
                    u.effective_chat.id,
                    preview_msg_id,
                    media=InputMediaPhoto(
                        media=msg['photo'],
                        caption=msg['caption'],
                        parse_mode=msg['parser'])
                )
            except BadRequest as ex:
                c.bot.edit_message_media(
                    u.effective_chat.id,
                    preview_msg_id,
                    media=InputMediaPhoto(
                        media=msg['photo'],
                        caption=msg['caption']+'\n\n⚠️ CAN NOT PARSE.\n'+ex.message)
                )
                msg['had-error'] = True
                c.user_data['had-error'] = True
        elif msg['type'] == 'text':
            # change message type to photo
            msg['type'] = 'photo'
            del(msg['text'])
            c.bot.edit_message_text(
                '⚠️ This message type had been changed from text to photo. ' +
                'You can request for a new preview to see this message.',
                u.effective_chat.id,
                preview_msg_id,
            )
        else:
            # report bug
            logging.error('UNKNOWN MSG TYPE FOUND\n'+str(msg))
            c.bot.send_message(
                server.ownerID, 'UNKNOWN MSG TYPE FOUND\n'+str(msg))

        if c.user_data.get('had-error'):
            c.user_data['last-message'] = u.message.reply_text(
                '🛑 there is a problem with your messages, please fix them.',
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=add_keyboard(c))
        else:
            c.user_data['last-message'] = u.message.reply_text('✅ Message edited; now you can add more messages or send it',
                                                               reply_markup=add_keyboard(c))
        return STATE_ADD

    @sendall_conv_handler.fallback
    @HandlerDecorator(CallbackQueryHandler, pattern='^delete$')
    def deleting(u: Update, c: CallbackContext):
        query = u.callback_query
        query.answer()
        query.edit_message_reply_markup(
            InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    '🛑 Are you sure?', callback_data='None')],
                [InlineKeyboardButton('🔴 Yes', callback_data='yes'), InlineKeyboardButton(
                    '🟢 No', callback_data='no')]
            ])
        )
        c.user_data['last-message'].delete()
        c.user_data['last-message'] = server.bot.send_message(
            u.effective_chat.id, '⏳ Deleting a message...', reply_markup=ReplyKeyboardRemove())
        return STATE_DELETE

    sendall_conv_handler.state(STATE_DELETE)(
        CallbackQueryHandler(cancel(STATE_DELETE), pattern='^no$')
    )

    @sendall_conv_handler.state(STATE_DELETE)
    @HandlerDecorator(CallbackQueryHandler, pattern='^yes$')
    def delete(u: Update, c: CallbackContext):
        query = u.callback_query
        query.answer('✅ Deleted')
        preview_msg_id = query.message.message_id
        msg = c.user_data['prev-dict'][preview_msg_id]
        c.user_data['messages'].remove(msg)
        del(c.user_data['prev-dict'][preview_msg_id])
        query.edit_message_text('❌')
        c.user_data['last-message'].delete()
        c.user_data['last-message'] = server.bot.send_message(
            u.effective_chat.id, 'OK, now you can send message to add', reply_markup=add_keyboard(c))
        return STATE_ADD

    def send_message(chat_id, c: CallbackContext):
        chat = server.bot.get_chat(chat_id)
        for msg in c.user_data['messages']:
            # send message to admin for a debug!
            if msg['type'] == 'text':
                try:
                    chat.send_message(
                        msg['text'],
                        parse_mode=msg['parser']
                    ).message_id
                except BadRequest as ex:
                    chat.send_message(
                        msg['text']+'\n\n⚠️ CAN NOT PARSE.\n'+ex.message,
                        reply_markup=text_markup
                    )
                    c.user_data['had-error'] = True
                    msg['had-error'] = True
                    return STATE_ADD
            elif msg['type'] == 'photo':
                try:
                    chat.send_photo(
                        msg['photo'],
                        msg['caption'],
                        parse_mode=msg['parser']
                    ).message_id
                except BadRequest as ex:
                    chat.send_photo(
                        msg['photo'],
                        caption=msg['caption'] +
                        '\n\n⚠️ CAN NOT PARSE.\n'+ex.message
                    ).message_id
                    c.user_data['had-error'] = True
                    msg['had-error'] = True
                    return STATE_ADD

    @sendall_conv_handler.state(STATE_CONFIRM)
    @HandlerDecorator(CallbackQueryHandler, pattern='^yes$')
    def send(u: Update, c: CallbackContext):
        query = u.callback_query
        if c.user_data.get('had-error'):
            query.answer()
            u.effective_chat.send_message(
                '🛑 there is a problem with your messages, please fix them.',
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=add_keyboard(c)
            )
            return STATE_ADD
        query.answer(
            '✅ Done\nSending message to all users, groups and channels', show_alert=True)
        logging.info('Sending message to chats')
        c.user_data['last-message'].delete()
        c.user_data['last-message'] = server.bot.send_message(u.effective_chat.id,
                                                              '✅ Done\nSending message to all users, groups and channels')

        res = send_message(u.effective_chat.id, c)
        if res:
            u.effective_chat.send_message(
                '🛑 there is a problem with your messages, please fix them.',
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=add_keyboard(c)
            )
            return res

        remove_ids = []
        for chat_id, chat_data in server.iter_all_chats():
            if chat_id != u.effective_chat.id:
                try:
                    send_message(chat_id, c)
                except Unauthorized as e:
                    server.log_bug(e, 'handled an exception while trying to send message to a chat. removing chat',
                                   report=False, chat_id=chat_id, chat_data=chat_data)
                    try:
                        with server.env.begin(server.chats_db, write=True) as txn:
                            txn.delete(str(chat_id).encode())
                    except Exception as e2:
                        server.log_bug(
                            e2, 'exception while trying to remove chat')
                        remove_ids.append(chat_id)
                except Exception as e:
                    server.log_bug(
                        e, 'exception while trying to send message to a chat', chat_id=chat_id, chat_data=chat_data)

        for chat_id in remove_ids:
            with server.env.begin(server.chats_db, write=True) as txn:
                txn.delete(str(chat_id).encode())

        cleanup_last_preview(u.effective_chat.id, c)
        for key in ('messages', 'prev-dict', 'had-error', 'edit-cap', 'editing-prev-id'):
            if key in c.user_data:
                del(c.user_data[key])
        return ConversationHandler.END

    sendall_conv_handler.state(STATE_CONFIRM)(
        CallbackQueryHandler(cancel(STATE_CONFIRM), pattern='^no$')
    )

    server.dispatcher.add_handler(sendall_conv_handler.get_handler(), group = 1)

def add_users_handlers(server: BotHandler):
    def unknown_msg(u: Update, c: CallbackContext):
        u.message.reply_text(server.get_string('unknown-msg'))

    def unknown_command(u: Update, c: CallbackContext):
        u.message.reply_text(server.get_string('unknown'))

    dispatcher_decorators = DispatcherDecorators(server.dispatcher)

    @dispatcher_decorators.commandHandler
    def start(u: Update, c: CallbackContext):
        chat = u.effective_chat
        message = u.message
        user = u.effective_user
        data = chat.to_dict()
        data['members-count'] = chat.get_members_count()-1
        if chat.type == Chat.PRIVATE:
            data.update(user.to_dict())
            message.reply_markdown_v2(server.get_string('welcome'))
            if len(c.args) == 1:
                if c.args[0] == server.token:
                    if user.id in server.adminID:
                        message.reply_text(
                            f'My dear {user.full_name}, I already know you as my lord!')
                    else:
                        message.reply_text(
                            f'Hi my dear {user.full_name}\nFrom now on, I know you as my lord\nyour id is: "{user.id}"')
                        server.adminID.append(user.id)
                        server.set_data(
                            'adminID', server.adminID, DB=server.data_db)

                        server.ownerID = user.id
                        server.set_data(
                            'ownerID', server.ownerID, DB=server.data_db)
                elif c.args[0] in server.admin_token:
                    if user.id in server.adminID:
                        message.reply_text(
                            f'My dear {user.full_name}, I already know you as my admin!')
                    else:
                        message.reply_text(
                            'Owner must accept your request.\n⏳ please wait...')
                        server.admins_pendding[user.id] = c.args[0]
                        server.bot.send_message(
                            server.ownerID,
                            'Hi, A user wants to be admin:\n' +
                            f'tel-id:\t{user.id}\n' +
                            f'user-id:\t{user.username}\n' +
                            f'name:\t{user.full_name}',
                            reply_markup=InlineKeyboardMarkup(
                                [[
                                    InlineKeyboardButton(
                                        '✅ Accept', callback_data=f'accept-{user.id}'),
                                    InlineKeyboardButton(
                                        '❌ Decline', callback_data=f'decline-{user.id}')
                                ]])
                        )

        else:
            u.message.reply_markdown_v2(
                server.get_string('group-intro'))

        server.set_data(key=str(chat.id), value=data)

    @dispatcher_decorators.commandHandler
    def last_feed(u: Update, c: CallbackContext):
        if u.effective_user.id not in server.adminID and 'time' in c.user_data:
            if c.user_data['time'] > datetime.now():
                u.message.reply_text(server.get_string('time-limit-error'))
                return
        server.send_feed(*server.read_feed(),msg_header = server.get_string('last-feed'),chats = [(u.effective_chat.id, c.chat_data)])
        c.user_data['time'] = datetime.now() + timedelta(minutes = 2)      #The next request is available 2 minutes later
    
    @dispatcher_decorators.commandHandler(command = 'help')
    def help_(u: Update, c: CallbackContext):
        if u.effective_chat.id == server.ownerID:
            u.message.reply_text(server.get_string('owner-help'))
        if u.effective_chat.id in server.adminID:
            u.message.reply_text(server.get_string('admin-help'))
        u.message.reply_text(server.get_string('help'))

    @dispatcher_decorators.messageHandler(Filters.update.edited_message)
    def handle_edited_msg(u: Update, c:CallbackContext):
        #TODO: Handle editing messages
        # Handle messages editing in /send_all could be usefull
        # labels: enhancement
        u.edited_message.reply_text(server.strings['edited-message'])

    dispatcher_decorators.addHandler(MessageHandler(Filters.command, unknown_command))
    dispatcher_decorators.addHandler(MessageHandler(Filters.all, unknown_msg))

def add_other_handlers(server: BotHandler):
    dispatcher_decorators = DispatcherDecorators(server.dispatcher)

    @dispatcher_decorators.addHandler
    @HandlerDecorator(ChatMemberHandler)
    def onBotBlocked(u: Update, c:CallbackContext):
        if (u.my_chat_member.new_chat_member.user.id == server.bot.id):
            status = u.my_chat_member.new_chat_member.status
            if status in (ChatMember.KICKED, ChatMember.LEFT, ChatMember.RESTRICTED):
                logging.info('Bot had been kicked or blocked by a user')
                with server.env.begin(server.chats_db, write = True) as txn:
                    txn.delete(str(u.my_chat_member.chat.id).encode())

    @dispatcher_decorators.messageHandler(Filters.status_update.new_chat_members)
    def onjoin(u: Update, c: CallbackContext):
        for member in u.message.new_chat_members:
            if member.username == server.bot.username:
                data = u.effective_chat.to_dict()
                data['members-count'] = u.effective_chat.get_members_count()-1
                server.set_data(key = str(u.effective_chat.id), value = data)
                server.bot.send_message(
                    server.ownerID,
                    '<i>Joined to a chat:</i>\n' +
                        html.escape(json.dumps(
                            data, indent = 2, ensure_ascii = False)),
                    ParseMode.HTML,
                    disable_notification = True)
                if u.effective_chat.type != Chat.CHANNEL:
                    u.message.reply_markdown_v2(
                        server.get_string('group-intro'))

    @dispatcher_decorators.messageHandler(Filters.status_update.left_chat_member)
    def onkick(u: Update, c: CallbackContext):
        if u.message.left_chat_member['username'] == server.bot.username:
            data = server.get_data(str(u.effective_chat.id))
            if data:
                server.bot.send_message(
                    server.ownerID,
                    '<i>Kicked from a chat:</i>\n' +
                        html.escape(json.dumps(
                            data, indent = 2, ensure_ascii = False)),
                    ParseMode.HTML,
                    disable_notification = True)
                with server.env.begin(server.chats_db, write = True) as txn:
                    txn.delete(str(u.effective_chat.id).encode())

    @dispatcher_decorators.errorHandler
    def error_handler(update: object, context: CallbackContext) -> None:
        """Log the error and send a telegram message to notify the developer."""

        server.log_bug(
            context.error,
            'Exception while handling an update',
            not isinstance(context.error, NetworkError),
            update = update.to_dict() if isinstance(update, Update) else str(update),
            user_data = context.user_data,
            chat_data = context.chat_data
        )
