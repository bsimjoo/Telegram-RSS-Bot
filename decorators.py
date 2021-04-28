import functools
from typing import List
from typing import Union as u
import BugReporter
import logging
from telegram.ext import (BaseFilter, CallbackContext, CommandHandler,
                          ConversationHandler, Dispatcher, Filters, Handler,
                          MessageHandler)
from telegram import Update


def auth(auth_users_id:u[List[u[str,int]],str,int], error:u[str,callable]):
    def decorator_auth(func):
        @functools.wraps(func)
        def wrapper(u:Update, c:CallbackContext):
            run = False
            if isinstance(auth_users_id,list):
                user_id = type(auth_users_id[0])(u.effective_user.id)
                run = user_id in auth_users_id
            else:
                user_id = type(auth_users_id)(u.effective_user.id)
                run = user_id == auth_users_id
            
            if run:
                return func(u,c)
            else:
                if callable(error):
                    return error(u,c)
                else:
                    u.effective_chat.send_message(error)
        
        return wrapper
    return decorator_auth

def HandlerDecorator (handlerClass,**kwargs):
    def decorator_handler(func):
        return handlerClass(callback = func, **kwargs)
    return decorator_handler

def MessageHandlerDecorator(self,filters = Filters.all, group=1, **kwargs):
    def decorator_message(func):
        return MessageHandler(filters, func, kwargs)
    return decorator_message
        
def CommandHandlerDecorator(_func=None, command=None, *args, **kwargs):
    def decorator_command(func):
        if not isinstance(command,str):
            command = func.__name__
        return CommandHandler(command,func,*args,**kwargs)
    
    if _func:
        return decorator_command(_func)
    else:
        return decorator_command

class DispatcherDecorators:
    def __init__(self, dispatcher:Dispatcher):
        self.dispatcher = dispatcher
    
    def commandHandler(self, _func=None, command=None, group=1, *args, **kwargs):
        def decorator_command(func):
            if not isinstance(command,str):
                command = func.__name__
            logging.debug(f'add command handler. command:{command} => {func}')
            try:
                self.dispatcher.add_handler(CommandHandler(command,func,*args,**kwargs), group)
            except:
                logging.exception('exception while trying to add a command')
                BugReporter.exception('exception while trying to add a command')
                
            
            return func
        
        if _func:
            return decorator_command(_func)
        else:
            return decorator_command

    def messageHandler(self, _func=None, filters=Filters.all, group=1, *args, **kwargs):
        def decorator_message(func):
            logging.debug(f'add message handler. handler: {func}')
            try:
                self.dispatcher.add_handler(MessageHandler(filters, func,*args, kwargs), group)
            except:
                logging.exception('exception while trying to add a command')
                BugReporter.exception('exception while trying to add a command')

            return func
        
        if _func:
            return decorator_message(_func)
        else:
            return decorator_message

    def addHandler(self, handler_:Handler = None, group=1):
        def decorator_handler(handler:Handler):
            logging.debug(f'add {type(handler).__name__}. handler: {handler.callback}')
            try:
                self.dispatcher.add_handler(handler, group)
            except:
                logging.exception('exception while trying to add a command')
                BugReporter.exception('exception while trying to add a command')
            return handler
        if handler_:
            return decorator_handler(handler_)
        else:
            return decorator_handler

class ConversationDecorator:
    def __init__(self, entry_points:List[Handler], **kwargs):
        self.entry_points = entry_points
        self.states = dict()
        self.fallbacks = []
        self.__kwargs = kwargs
    
    def state(self, *states):
        def decorator_state(handler:Handler):
            for state in states:
                if not state in self.states:
                    self.states[state] = []
                self.states[state].append(handler)
            return handler
        return decorator_state

    def fallback(self, handler:Handler):
        self.fallbacks.append(handler)
        return handler

    def get_handler(self):
        return ConversationHandler(self.entry_points, self.state, self.fallbacks, **self.__kwargs)
