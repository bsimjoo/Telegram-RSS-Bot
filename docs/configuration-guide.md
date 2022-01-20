# Configuration guide

## Version 2.x.x
Create Your-own copy of `config-example.jsonc` and name it as `user-config.jsonc`.

### token
The bot token that owner received from @botfather. Follow Telegram instructions to [create a new bot user](https://core.telegram.org/bots#3-how-do-i-create-a-bot)

|Required|Too important|
|:------:|:----------------:|
|Type|`string`|
|Default|`place holder` - YOUR BOT TOKEN|

### db-path
Directory of [LMDB database](https://en.wikipedia.org/wiki/Lightning_Memory-Mapped_Database)

|Required|Yes|
|:------:|:----------------:|
|Type|`path`|
|Default|db.lmdb|
### feed-configs:
This property will able you to personalize the way that bot will reed a feed

#### source 
Source of feeds

|Required|Yes|
|:------:|:----------------:|
|Type|`url`|
|Default|https://pcworms.blog.ir/rss|

#### parse
Specify format of feeds. Telegram-RSS-Bot uses BeautifulSoup to read feeds, so value must match BeautifulSoup requirements.

|Required|Yes|
|:------:|:----------------:|
|Type|`url`|
|Default|https://pcworms.blog.ir/rss|

### Selectors
Telegram-RSS-Bot uses CSS-Selector to find feeds and read them.

- feeds-selector: css-selector for each feed
- time-selector: time of feed.
- time-attribute: if time stored in attribute, specify it here
- link-selector: selector of feed link. could be null.
- link-attribute: if link stored in attribute, specify it here
- title-selector: selector for feed title
- title-attribute: if title stored in attribute, specify it here
- content-selector: feed contents; the main caption.
- feed-skip-condition: a condition to skip a feed. if selector had a result Bot will skip that post.
  - format: title/REGEX, feed/CSS-SELECTOR, content/CSS-SELECTOR", link/REGEX
- remove-elements-selector: this elements won't be in message.

### language
The language name that stored in `strings.json` or `Default-strings.json` file

|Required|Yes|
|:------:|:----------------:|
|Type|`string`|
|Default|en-us|

### strings-file
A `Json` file that contains all languages and strings that your bot need

|Required|Yes|
|:------:|:----------------:|
|Type|`path`|
|Default|default-strings.json|

### log-level
Log level

|Required|Yes|
|:------:|:----------------:|
|Type|choice - `info`, `warning`, `error`, `critical`|
|Default|`info`|

### log-file
optionally you can redirect logs to a file

|Required|No|
|:------:|:----------------:|
|Type|`path`|
|Default|`Null`|

### bug-reporter
Bug-reporter module counts exceptions and report them in a json or on a http server. If you need to run http server you must install Cherrypy. Read [Bug-Reporter in Readme.md](../README.md#beetle-bug-reporter-)

- off: `"bug-reporter": "off"`
- offline:
  ```json
  "bug-reporter": {
    "bugs-file": "bugs.json",
    "use-git": true,
    "git-path": "/usr/bin/git"
  }
  ```
- online:
  ```jsonc
  "bug-reporter":{
    "bugs-file": "bugs.json",
    "use-git": true,
    "git-path": "/usr/bin/git",
    "git-source": "https://github.com/bsimjoo/Telegram-RSS-Bot",
    "http-config":{
      // CHERRYPY CONFIG
      "server.socket_host": "0.0.0.0",
      "server.socket_port": 7191,
      "log.screen": false
    }
  }
  ```

## Version 1.x.x
Create your-own copy of `config-example.conf` and name it as `user-config.conf`.

### token
The bot token that owner received from @botfather. Follow Telegram instructions to [create a new bot user](https://core.telegram.org/bots#3-how-do-i-create-a-bot)

|Required|Too important|
|:------:|:----------------:|
|Type|`string`|
|Default|`place holder` - YOUR BOT TOKEN|

### source
Source of xml RSS feeds

|Required|Yes|
|:------:|:----------------:|
|Type|`url`|
|Default|https://pcworms.blog.ir/rss|

### language
The language name that stored in `strings.json` or `Default-strings.json` file

|Required|Yes|
|:------:|:----------------:|
|Type|`string`|
|Default|en-us|

### strings-file
A `Json` file that contains all languages and strings that your bot need

|Required|Yes|
|:------:|:----------------:|
|Type|`path`|
|Default|default-strings.json|

### log-level
Log level

|Required|Yes|
|:------:|:----------------:|
|Type|choice - `info`, `warning`, `error`, `critical`|
|Default|`info`|

### log-file
optionally you can redirect logs to a file

|Required|No|
|:------:|:----------------:|
|Type|`path`|
|Default|`Null`|

### db-path
Directory of [LMDB database](https://en.wikipedia.org/wiki/Lightning_Memory-Mapped_Database)

|Required|Yes|
|:------:|:----------------:|
|Type|`path`|
|Default|db.lmdb|

### bug-reporter
Bug-reporter module counts exceptions and report them in a json or on a http server. If value is `online` you must install Cherrypy. Read [Bug-Reporter in Readme.md](../README.md#beetle-bug-reporter-)

|Required|No|
|:------:|:----------------:|
|Type|choice - `off`, `offline`, `online`|
|Default|`off`|

Add this configurations if using bug-reporter:
- **reporter-config-file**: Another config file that contains [Cherrypy configuration](https://docs.cherrypy.org/en/latest/config.html)
  - Required: if Bug-Reporter mode is `online`
  - Type: `path`
  - Default: Bug-Reporter.conf
- **bugs-file**: A json file for bug-reporter output. bug reporter wil save and restore exception in this file
  - Required: if Bug-Reporter isn't off
  - Type: `path`
  - Default: bugs.json
- **use-git**: If value is true, bug-reporter will get commit, branch, and source from git.
  - Required: No
  - Type: `boolean`
  - Default: `false`
- **git-path**: specify git executable file. useful if git isn't present in path variable.
  - Required: No
  - Type: `path`
  - Default: /usr/bin/git
- **git-source**: Manually specify a repo. This feature is used to create a direct link to the code line which risen exception. This property will be obtained from git if it does not exist.
  - Required: No
  - Type: `URL`
  - Default: https://github.com/bsimjoo/Telegram-RSS-Bot
