import json
import subprocess
import logging
import os

class BugReporter:
    def __init__(self, file_path = 'bugs.json', use_git=True, git='git', git_source=None):
        self.commit = None
        self.git_source = git_source
        self.bugs = dict()
        self.build_state = 'passing'
        self.bugs_count = 0
        self.__update_data__()
        self.use_git = use_git
        self.git = git
        if use_git:
            self.get_git_info()
        self.file_path = file_path
        self.load_file(file_path)

    def __update_data__(self):
        self.data={
            'commit':self.commit,
            'bugs':self.bugs,
            'build_state':self.build_state,
            'bugs_count':self.bugs_count
        }

    def load_file(self, file_path):
        if os.path.exists(file_path):
            self.file_path = file_path
            data=dict()
            try:
                with open(file_path, encoding='utf-8') as f:
                    data = json.load(f)
            except:
                logging.exception('Can not parse bugs file')
                return
            if self.use_git:
                #compare commit
                if self.commit != data.get('commit') or not data.get('commit'):
                    return
            
            self.bugs = data.get('bugs',dict())
            self.build_state = data.get('build_state','passing')
            self.bugs_count = data.get('bugs_count',0)
        self.__update_data__()
        

    def get_git_info(self):
        dir = os.path.dirname(__file__)
        if dir != '':
            os.chdir(dir)
        try:
            short_hash = subprocess.check_output([self.git, 'describe', '--always'], stderr=subprocess.STDOUT).strip().decode()
            self.commit = subprocess.check_output([self.git, 'rev-parse', short_hash], stderr=subprocess.STDOUT).strip().decode()
        except subprocess.CalledProcessError:
            logging.error('There was an error - command exited with non-zero code')
            return
        except:
            logging.exception('Unknown error')
            return
        
        if not self.git_source:
            lines=[]
            try:
                lines = subprocess.check_output([self.git, 'remote', '-v'], stderr=subprocess.STDOUT).decode().strip().split('\n')
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
                    self.git_source = r
                    break
        self.__update_data__()
    
    def bug(self, tag_name, message=None, **more):
        tag = self.bugs.get(tag_name,{'count':0,'message':None})
        tag['message'] = message
        tag['count']+=1
        tag.update(more)
        self.bugs[tag_name] = tag
        self.bugs_count = len(self.bugs)
        self.build_state = 'failing'
        self.__update_data__()

    def dump(self):
        json.dump(self.data, open(self.file_path, 'w', encoding='utf8'), indent = 2, ensure_ascii = False)
    
    def dumps(self):
        return json.dumps(self.data, indent = 2, ensure_ascii = False)
