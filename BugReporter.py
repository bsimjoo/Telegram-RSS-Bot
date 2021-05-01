import json
import subprocess
import logging
import os
import traceback
import sys

commit = None
running_version = None
git_source = None
bugs = dict()
build_state = 'passing'
bugs_count = 0
file_path = None

def quick_config(file_path_ = 'bugs.json', use_git_=True, git_='git', git_source_=None):
    global git_source, git, use_git, file_path
    file_path = file_path_
    use_git = use_git_
    git = git_
    git_source = git_source_
    if use_git_:
        get_git_info()
    
    load_file(file_path)

def get_data():
    return {
        'commit':commit,
        'running_version': running_version,
        'bugs':bugs,
        'build_state':build_state,
        'bugs_count':bugs_count
    }

def load_file(file_path_):
    global file_path, bugs, build_state, bugs_count
    if os.path.exists(file_path_):
        file_path = file_path_
        data=dict()
        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)
        except:
            logging.exception('Can not parse bugs file')
            return
        if use_git:
            #compare commit
            if commit != data.get('commit') or not data.get('commit'):
                return
        
        bugs = data.get('bugs',dict())
        bugs_count = len(bugs)
        build_state = 'failing' if bugs_count else 'passing'
    

def get_git_info():
    global commit, git_source, running_version
    dir = os.path.dirname(__file__)
    if dir != '':
        os.chdir(dir)
    try:
        short_commit = subprocess.check_output([git, 'describe', '--always'], stderr=subprocess.STDOUT).strip().decode()
        commit = subprocess.check_output([git, 'rev-parse', short_commit], stderr=subprocess.STDOUT).strip().decode()
        running_version = subprocess.check_output([git, 'describe', '--tags'], stderr=subprocess.STDOUT).strip().decode()
    except subprocess.CalledProcessError:
        logging.error('There was an error - command exited with non-zero code')
        return
    except:
        logging.exception('Unknown error')
        return
    
    if not git_source:
        lines=[]
        try:
            lines = subprocess.check_output([git, 'remote', '-v'], stderr=subprocess.STDOUT).decode().strip().split('\n')
        except subprocess.CalledProcessError:
            logging.error('There was an error - command exited with non-zero code')
            return
        except:
            logging.exception('Unknown error')
            return
        #get first fetch remote
        for l in lines:
            r = l.split()
            if r[2] == '(fetch)':
                r = r[1]
                if r.endswith('.git'):
                    r = r[:-4]
                git_source = r
                break

def bug(tag_name, message=None, **more):
    global bugs, bugs_count, build_state
    tag = bugs.get(tag_name,{'count':0,'message':None})
    tag['message'] = message
    tag['count']+=1
    tag.update(more)
    bugs[tag_name] = tag
    bugs_count = len(bugs)
    build_state = 'failing'

def exception(custom_msg='', exc_info=None, report = True, **args):
    exception_type, ex, tb = None, None, None
    if isinstance(exc_info, BaseException):
        exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
    elif not isinstance(exc_info, tuple):
        exc_info = sys.exc_info()
    exception_type, ex, tb = exc_info
    tb_list = traceback.format_exception(exception_type, ex, tb)
    tb_string = ''.join(tb_list)
    s = traceback.extract_tb(tb)
    f = s[0]
    lineno = f.lineno
    filename = os.path.basename(f.filename)
    if report:
        bug(f'L{lineno}@{filename}: {exception_type}', f'{custom_msg}\n{tb_string}', line=lineno, file=filename, **args)
    return {
        'exc_type'  : exception_type,
        'line_no'  : lineno,
        'file_name': filename,
        'tb_string': tb_string,
        'traceback': tb
    }

def dump():
    json.dump(get_data(), open(file_path, 'w', encoding='utf8'), indent = 2, ensure_ascii = False)

def dumps():
    return json.dumps(get_data(), indent = 2, ensure_ascii = False)


class OnlineReporter:
    import cherrypy

    @cherrypy.expose
    def index(self):
        res = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bugs</title>
            <link rel="shortcut icon" type="image/png" href="https://bsimjoo.github.io/Telegram-RSS-Bot/media/bug.png"/>
            <style>
                html, body{
                    background-color: #1b2631;
                    color:  #d6eaf8;
                }
                pre, ssh-pre{
                    width:80%;
                    max-height: 30%;
                    margin: auto;
                    background-color: #873600;
                    color:  white;
                    border-radius: 10px;
                    padding: 10px;
                    overflow-x: auto;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                a:visited{
                    color: #a569bd
                }
            </style>
        </head>
        <body>
            <h1 style="background-color: #d6eaf8; border-radius:10px; color:black">🐞 Bugs</h1>
            <p><b>What is this?</b> This project uses a simple web
            server to report bugs (exceptions) in a running application.</p>
            <h6><a href="/json">Show raw JSON</a>&bul;<a href="/gotocommit">go to commit</a></h6>'''

        if bugs_count:
            res+=f'<h2>😔 {bugs_count} bug(s) found</h2>'
            for tag, content in bugs.items():
                link = ''
                if 'file' in content and use_git:
                    lineno = content['line']
                    filename = content['file']
                    if os.path.exists(filename):
                        link = f' <a href="{git_source}/blob/{commit}/{filename}#L{lineno}">🔸may be here: L{lineno}@{filename}</a></h3>'
                res+=f'<h3>&bull;Tag: <kbd>"{tag}"</kbd> Count: {content["count"]} {link}</h3>'
                if content["message"]:
                    res+=f'<pre>{content["message"]}</pre>'
        else:
            res+='<h1 align="center">😃 NO 🐞 FOUND 😉</h1>'

        res+='</body></html>'
        return res

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def json(self):
        return get_data()

    @cherrypy.expose
    def gotocommit(self):
        import cherrypy
        if use_git:
            raise cherrypy.HTTPRedirect('/'.join((git_source,'tree',commit)))
        else:
            raise cherrypy.NotFound
            