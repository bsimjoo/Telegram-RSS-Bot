import json
import subprocess
from os.path import exists

class __reporter__:
    def __init__(self, data:dict):
        commit = subprocess.check_output(["git", "describe", "--always"]).strip().decode()
        if data.get('commit') == commit:
            self.data = data
        else:
            self.data = {'commit':commit, 'tags':dict(), 'bugs_count':0}
        
    def bug(self, tag, message=None):
        tags = self.data['tags']
        current_tag = tags.get(tag, {'count':0})
        current_tag['count'] += 1
        current_tag['message'] = message
        tags[tag] = current_tag
        self.data['bugs_count'] = len(tags)

class BugReporter:
    def __init__(self, file_path = 'bugs.json'):
        if exists(file_path):
            self.reports = json.load(open(file_path))
        else:
            self.reports = dict()
        self.file_path = file_path

    def __call__(self, group):
        data = self.reports.get(group,dict())
        reporter = __reporter__(data)
        self.reports[group] = reporter.data
        return reporter
    
    def dump(self):
        json.dump(self.reports, open(self.file_path, 'w'), indent = 2, ensure_ascii = False)
    
    def dumps(self):
        return json.dumps(self.reports, indent = 2, ensure_ascii = False)
