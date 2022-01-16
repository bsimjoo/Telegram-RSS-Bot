import argparse
import html
from xml.sax.handler import feature_external_ges
import bs4
import commentjson
import logging
import os
import pickle
import re
import sys

from telegram.files.document import Document
import BugReporter
import Handlers
import io
from threading import Timer
from urllib.request import urlopen
import lmdb
from bs4 import BeautifulSoup as Soup
from bs4 import Comment
from dateutil.parser import parse as parse_date
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,ParseMode)
from telegram.error import Unauthorized
from telegram.ext import Updater


import time
from functools import wraps


def retry(tries=4, delay=3, backoff=2):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    logging.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


class BotHandler:

    #All supported tags by telegram seprated by '|'
    # this program will handle images it self
    SUPPORTED_HTML_TAGS = '|'.join(('a','b','strong','i','em','code','pre','s','strike','del','u'))
    SUPPORTED_TAG_ATTRS = {'a':'href', 'img':'src', 'pre':'language'}
    MAX_MSG_LEN = 4096
    MAX_CAP_LEN = 1024

    def __init__(
        self,
        Token,
        feed_configs,
        env,
        chats_db,
        data_db,
        strings: dict,
        bug_reporter = False,
        debug = False,
        request_kwargs=None):
        
        self.updater = Updater(Token, request_kwargs=request_kwargs)
        self.bot = self.updater.bot
        self.dispatcher = self.updater.dispatcher
        self.token = Token
        self.env = env
        self.chats_db = chats_db
        self.data_db = data_db
        self.adminID = self.get_data('adminID', [], DB = data_db)
        self.ownerID = self.get_data('ownerID', DB = data_db)
        self.admins_pendding = {}
        self.admin_token = []
        self.strings = strings
        #`source` now is a property of `feed_config`
        self.feed_configs = feed_configs
        self.source = feed_configs['source']
        self.interval = self.get_data('interval', 5*60, data_db)
        self.__check = True
        self.bug_reporter = bug_reporter if bug_reporter else None
        self.debug = False

        if debug:
            Handlers.add_debuging_handlers(self)

        Handlers.add_users_handlers(self)
        Handlers.add_admin_handlers(self)
        Handlers.add_owner_handlers(self)
        Handlers.add_other_handlers(self)
        Handlers.add_unknown_handlers(self)

        # New configurations:
        # - feed-format: specify feed fromat like xml or ...
        # - feeds-list-selector: how to find list of all feeds
        # - title-selector: how to find title
        # - link-selector: how to get link of source
        # - content-selector: how to get content
        # - skip-condition: how to check skip condition
        #   - format: feed/{selector}, content/{selector}, title/{regex}, link/{regex}, none

        self.__skip = lambda feed: False
        skip_condition = feed_configs.get('feed-skip-condition')
        if isinstance(skip_condition, str):
            self.__skip_field, skip_condition = skip_condition.split('/')
            if self.__skip_field == 'feed':
                self.__skip = lambda feed: bool(feed.select(skip_condition))
            elif self.__skip_field == 'content':
                self.__skip = lambda content: bool(content.select(skip_condition))
            elif self.__skip_field == 'title':
                match = re.compile(skip_condition).match
                self.__skip = lambda title: bool(match(title))
            elif self.__skip_field == 'link':
                match = re.compile(skip_condition).match
                self.__skip = lambda link: bool(match(link))

    def log_bug(self, exc:Exception, msg='', report = True, disable_notification = False,**args):
        info = BugReporter.exception(msg, exc, report = self.bug_reporter and report)
        logging.exception(msg, exc_info=exc)
        msg = html.escape(msg)
        escaped_info = {k:html.escape(str(v)) for k,v in info.items()}
        message = (
            '<b>An exception was raised</b>\n'
            '<i>L{line_no}@{file_name}: {exc_type}</i>\n'
            f'{msg}\n\n'
            '<pre>{tb_string}</pre>'
        ).format_map(escaped_info)

        if args:
            message+='\n\nExtra info:'
            msg+='\n\nExtra info'
            for key, value in args.items():
                message+=f'\n<pre>{key} = {html.escape(commentjson.dumps(value, indent = 2, ensure_ascii = False))}</pre>'
                msg+=f'\n{key} = {commentjson.dumps(value, indent = 2, ensure_ascii = False, default=str)}'
        
        if len(message)<=self.MAX_MSG_LEN:
            self.bot.send_message(chat_id = self.ownerID, text = str(message), parse_mode = ParseMode.HTML, disable_notification = disable_notification)
        else:
            f = io.StringIO(message)
            self.bot.send_document(chat_id= self.ownerID,
                document= f,
                filename= '{file_name}_{line_no}.html'.format_map(info),
                caption= 'log of an unhandled exception')

    def __get_content (self, tag):
        if isinstance(tag, bs4.NavigableString):
            return tag.string
        else:
            return ''.join([str(c) for c in tag.contents])

    def purge(self, html, images=True) -> Soup:
        tags = self.SUPPORTED_HTML_TAGS
        if images:
            tags+='|img'
        if not isinstance(html, str):
            html = str(html)
        pattern = r'</?(?!(?:%s)\b)\w+[^>]*/?>'%tags
        purge = re.compile(pattern).sub      #This regex will purge any unsupported tag
        soup = Soup(purge('', html), 'html.parser')
        comments = soup.findAll(text=lambda text:isinstance(text, Comment))
        for c in comments:
            c.extract()
        for tag in soup.descendants:
            #Remove any unsupported attribute
            if tag.name in self.SUPPORTED_TAG_ATTRS:
                attr = self.SUPPORTED_TAG_ATTRS[tag.name]
                if attr in tag.attrs:
                    tag.attrs = {attr: tag[attr]}
            else:
                tag.attrs = dict()
        return soup

    @retry(10)
    def get_feeds(self):
        with urlopen(self.feed_configs['source']) as f:
            return f.read().decode('utf-8')

    def summarize(self, soup:Soup, length, read_more):
        offset = len(read_more)
        len_ = len(str(soup))
        if len_>length:
            offset += len_ - length
            removed = 0
            for element in reversed(list(soup.descendants)):
                if (not element.name) and len(str(element))>offset-removed:
                    s = str(element)
                    wrap_index = s.rfind(' ',0 , offset-removed)
                    if wrap_index == -1:
                        element.replace_with(s[:-offset+removed])
                        removed = offset
                    else:
                        element.replace_with(s[:wrap_index])
                    removed = offset
                else:
                    element.replace_with('')
                    removed += len(str(element))
                if removed >= offset:
                    break
            soup.append(read_more)
        return str(soup), len_>length

    # in this version fead reader uses css selector to get feeds.
    # 
    # New configurations:
    # - parse: specify feed fromat like xml or ...
    # - feeds-selector: how to get all feeds
    # - title-selector: how to find title
    # - link-selector: how to get link of source
    # - date-selector: how to get feed date
    # - content-selector: how to get content
    # - feed-skip-condition: how to check skip condition
    #   - format: feed/{selector}, content/{selector}, title/{regex}, none
    # - remove-elements-selector: skip any element that has this attribute

    def read_feed(self, index=0):
        feeds_page = None
        try:
            feeds_page = self.get_feeds()
        except Exception as e:
            self.log_bug(e,'exception while trying to get last feed', False, True)
            return None, None
        
        soup_page = Soup(feeds_page, self.feed_configs.get('feed-format', 'xml'))
        feeds_list = soup_page.select(self.feed_configs['feeds-selector'])
        title, link, content, time = None, None, None, None
        for feed in feeds_list[index::-1]:
            try:
                if self.__skip_field == 'feed':
                    if self.__skip(feed):
                        continue    #skip this feed

                title_selector = self.feed_configs['title-selector']
                if title_selector:
                    # title-selector could be None (null)
                    if self.feed_configs['title-attribute']:
                        title = str(feed.select_one(title_selector).attrs[self.feed_configs['title-attribute']])
                    else:
                        title = str(feed.select_one(title_selector).text)

                    if self.__skip_field == 'title':
                        if self.__skip(title):
                            continue

                link_selector = self.feed_configs['link-selector']
                if link_selector:
                    # link-selector could be None (null)
                    if self.feed_configs['link-attribute']:
                        link = str(feed.select_one(link_selector).attrs[self.feed_configs['link-attribute']])
                    else:
                        link = str(feed.select_one(link_selector).text)

                    if self.__skip_field == 'link':
                        if self.__skip(link):
                            continue
                
                time_selector = self.feed_configs['time-selector']
                if time_selector:
                    # date-selector could be None (null)
                    if self.feed_configs['time-attribute']:
                        time = str(feed.select_one(time_selector).attrs[self.feed_configs['time-attribute']])
                    else:
                        time = str(feed.select_one(time_selector).text)
                
                content_selector = self.feed_configs['content-selector']
                if content_selector:
                    content = Soup(self.__get_content(feed.select(content_selector)[0]),features="lxml")

                    if self.__skip_field == 'content':
                        if self.__skip(content):
                            continue
                
            except Exception as e:
                self.log_bug(e,'Exception while reading feed', feed = str(feed))
                break
        
            yield {
                'title': title,
                'link': link,
                'content': content,
                'date': time
                }

    def render_feed(self, feed: dict, header: str):
        title = feed['title']
        post_link = feed['link']
        content = feed['content']
        messages = [{
            'type': 'text',
            'text': header+'\n',
            'markup': []
        }]
        if title:
            title = f'<b>{title}</b>'
            if post_link:
                title = f'<a href="{post_link}">{title}</a>'
            messages[0]['text']+=title
        overflow = False
        try:
            if content:
                #Remove elements with selector
                remove_elem = self.feed_configs.get('remove-elements')
                if remove_elem:
                    for elem in content.select():
                        elem.replace_with('')
                content = self.purge(content)
                images = content.find_all('img')
                first = True

                if not len(images):
                    content, overflow = self.summarize(content, self.MAX_MSG_LEN, self.get_string('read-more'))
                    messages[0]['text'] += '\n'+content
                else:
                    left, img_link, right = None, None, str(content)
                    
                    for img in images:
                        last_message = messages[-1]
                        split_by = str(img)
                        if img.parent.name == 'a':
                            split_by = str(img.parent)
                            img_link = img.parent['href']
                        left, right = right.split(split_by, 1)

                        if first:
                            if left:
                                length = self.MAX_MSG_LEN if last_message['type'] == 'text' else self.MAX_CAP_LEN
                                left, overflow = self.summarize(left, length, self.get_string('read-more'))
                                last_message['text'] += '\n'+left
                                if right and not overflow:
                                    msg = {
                                        'type': 'image',
                                        'src': img['src'],
                                        'text': '',
                                        'markup': []
                                    }
                                    if img_link:
                                        msg['markup'] = [[InlineKeyboardButton(self.get_string('image-link'), img_link)]]
                                    messages.append(msg)
                            else:
                                last_message['type'] = 'image'
                                last_message['src'] = img['src']
                                if img_link:
                                    last_message['markup'] = [[InlineKeyboardButton(self.get_string('image-link'), img_link)]]
                            first = False
                        else:
                            length = self.MAX_MSG_LEN if last_message['type'] == 'text' else self.MAX_CAP_LEN
                            left, overflow = self.summarize(left, length, self.get_string('read-more'))
                            last_message['text'] += left
                            if right and not overflow:
                                msg = {
                                    'type': 'image',
                                    'src': img['src'],
                                    'text': '',
                                    'markup': []
                                }
                                if img_link:
                                    msg['markup'] = [[InlineKeyboardButton(self.get_string('image-link'), img_link)]]
                                messages.append(msg)
                        if overflow:
                            break
                    #End for img
                    if not overflow:
                        length = self.MAX_MSG_LEN if messages[-1]['type'] == 'text' else self.MAX_CAP_LEN
                        right, overflow = self.summarize(right, length, self.get_string('read-more'))
                        messages[-1]['text'] += right
                    
                if post_link:
                    messages[-1]['markup'].append([InlineKeyboardButton(self.get_string('goto-post'), post_link)])
            return messages
        except Exception as e:
            self.log_bug(e,'Exception while rendering feed', feed = str(feed), messages = str(messages))
            return None

    def send_feed(self, messages, chats):
        deathlist = [] #Delete IDs that are no longer available
        try:
            for chat_id, chat_data in chats:
                for msg in messages:
                    try:
                        if msg['type'] == 'text':
                            self.bot.send_message(
                                chat_id,
                                msg['text'],
                                parse_mode = ParseMode.HTML,
                                reply_markup = InlineKeyboardMarkup(msg['markup']) if msg['markup'] else None,
                                disable_web_page_preview = True
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
                    except Unauthorized as e:
                        self.log_bug(e,'handled an exception while sending a feed to a user. removing chat', report=False, chat_id = chat_id, chat_data = chat_data)
                        deathlist.append(chat_id)
                        break
                    except Exception as e:
                        self.log_bug(e, 'Exception while sending a feed to a user', message = msg, chat_id = chat_id, chat_data = chat_data)
                        break
        except Exception as e:
            self.log_bug(e,'Exception while trying to send feed', messages = messages)

        for chat_id in deathlist:
            with self.env.begin(self.chats_db, write = True) as txn:
                txn.delete(str(chat_id).encode())

    def iter_all_chats(self):
        deathlist = []
        with env.begin(self.chats_db) as txn:
            for key, value in txn.cursor():
                data = pickle.loads(value)
                if not isinstance(data,dict):
                    deathlist.append(key)
                    self.log_bug(ValueError('chat data is not a dict'), 'chat data is not a dict', data = data)
                    continue
                yield key.decode(), data
        with env.begin(self.chats_db, write = True) as txn:
            for key in deathlist:
                txn.delete(key.encode())

    def check_new_feed(self):
        last_date = self.get_data('last-feed-date', DB = self.data_db)
        latest_date = last_date
        for feed in self.read_feed():
            feed_date = parse_date(feed['date']) if feed['date'] else None
            if feed_date is not None and (last_date is None or latest_date < feed_date):  # if feed_date is not None and last_date not exist or last feed's date is older than the new one
                self.set_data('last-feed-date', feed_date, DB = self.data_db)
                latest_date = feed_date
            if feed_date is None or (last_date is not None and last_date < feed_date):
                messages = self.render_feed(feed, header= self.get_string('new-feed')+f'\nlast_date: {last_date}\nfeed_date: {feed_date}')
                self.send_feed(messages, self.iter_all_chats())
                if feed_date is None or last_date is None:
                    break   #just send last feed
            else:
                break   #no new feed
        if self.__check:
            self.check_thread = Timer(self.interval, self.check_new_feed)
            self.check_thread.start()


    def get_data(self, key, default = None, DB = None, do = lambda data: pickle.loads(data)):
        DB = DB if DB else self.chats_db
        data = None
        with self.env.begin(DB) as txn:
            data = txn.get(key.encode(), default)
        if data is not default and callable(do):
            return do(data)
        else:
            return data

    def set_data(self, key, value, DB = None, over_write = True, do = lambda data: pickle.dumps(data)):
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
        self.__check = False
        self.check_thread.cancel()
        if self.check_thread.is_alive():
            print('waiting for check thread to finish')
            self.check_thread.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser('main.py',
        description='Open source Telegram RSS-Bot server by bsimjoo\n'+\
            'https://github.com/bsimjoo/Telegram-RSS-Bot'
        )
    
    parser.add_argument('-r','--reset',
    help='Reset stored data about chats or bot data',
    default=False,required=False,choices=('data','chats','all'))

    parser.add_argument('-c','--config',
    help='Specify config file',
    default='user-config.jsonc', required=False, type=argparse.FileType('r'))

    args = parser.parse_args(sys.argv[1:])
    config = dict()
    with args.config as cf:
        config = commentjson.load(cf)

    token = config.get('token')
    if not token:
        logging.error("No Token, terminating")
        sys.exit()
    
    log_file_name = config.get('log-file')
    logging.basicConfig(
        format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file_name,
        level = logging._nameToLevel.get(config.get('log-level','INFO').upper(),logging.INFO))
    env = lmdb.open(config.get('db-path','db.lmdb'), max_dbs = 3)
    chats_db = env.open_db(b'chats')
    data_db = env.open_db(b'config')        #using old name for compatibility

    if args.reset:
        answer = input(f'Are you sure you want to Reset all "{args.reset}"?(yes | anything else means no)')
        if answer != 'yes':
            print('canceled')
        else:
            if args.reset in ('data', 'all'):
                with env.begin(data_db, write=True) as txn:
                    d=env.open_db()
                    txn.drop(d)
            if args.reset in ('chats', 'all'):
                with env.begin(chats_db, write=True) as txn:
                    d=env.open_db()
                    txn.drop(d)
            print('Reset done. now you can run the bot again')
            sys.exit()

    language = config.get('language','en-us')
    strings_file = config.get('strings-file', 'default-strings.json')
    checks=[
        (strings_file, language),
        (strings_file, 'en-us'),
        ('Default-strings.json', language),
        ('Default-strings.json', 'en-us')
    ]
    strings = None
    for file, language in checks:
        if os.path.exists(file):
            with open(file,encoding='utf8') as f:
                strings = commentjson.load(f)
            if language in strings:
                strings = strings[language]
                logging.info(f'using "{language}" language from "{file}" file')
                break
            else:
                logging.error(f'"{language}" language code not found in "{file}"')
        else:
            logging.error(f'file "{file}" not found')

    if not strings or strings == dict():
        logging.error('Cannot use a strings file. exiting...')
        sys.exit(1)

    bug_reporter_config = config.get('bug-reporter','off')
    if bug_reporter_config != 'off' and isinstance(bug_reporter_config, dict):
        bugs_file = bug_reporter_config.get('bugs-file','bugs.json')
        use_git = bug_reporter_config.get('use-git',False)
        git = bug_reporter_config.get('git-command','git')
        git_source = bug_reporter_config.get('git-source')
        BugReporter.quick_config(bugs_file, use_git, git, git_source)
        
        if 'http-config' in bug_reporter_config:
            try:
                from BugReporter import OnlineReporter
                import cherrypy
                
                conf = config.get('http-config',{
                    'global':{
                        'server.socket_host': '0.0.0.0',
                        'server.socket_port': 7191,
                        'log.screen': False
                    }
                })
                cherrypy.log.access_log.propagate = False
                cherrypy.tree.mount(OnlineReporter(),'/', config=conf)
                cherrypy.config.update(conf)
                cherrypy.engine.start()
                
            except ModuleNotFoundError:
                logging.error('Cherrypy module not found, please first make sure that it is installed and then use http-bug-reporter')
                logging.info(f'Can not run http bug reporter, skipping http, saving bugs in {bugs_file}')
            except:
                logging.exception("Error occurred while running http server")
                logging.info(f'Can not run http bug reporter, skipping http, saving bugs in {bugs_file}')
            else:
                logging.info(f'reporting bugs with http server and saving them as {bugs_file}')
        else:
            logging.info(f'saving bugs in {bugs_file}')

    debug = config.get('debug',False)

    use_proxy = config.get('use-proxy', False)
    proxy_info = None
    if use_proxy:
        proxy_info = config.get('proxy-info')

    bot_handler = BotHandler(token, config.get('feed-configs'), env, chats_db, data_db, strings, bug_reporter_config != 'off', debug, proxy_info)
    bot_handler.run()
    bot_handler.idle()
    if bug_reporter_config != 'off':
        logging.info('saving bugs report')
        BugReporter.dump()
    if 'http-config' in bug_reporter_config:
        logging.info('stoping http reporter')
        cherrypy.engine.stop()
    env.close()
    
