# Configuration guide
Create your-own copy of `config-example.conf` and name it as `user-config.conf`.

| Name | required | Default value | Type | Describe |
|:----:|:--------:|:-------------:|:-----|:---------|
| `token` | :heavy_check_mark::heavy_check_mark: | `None` | `string` | The bot token that owner received from @botfather. Follow Telegram instructions to [create a new bot user](https://core.telegram.org/bots#3-how-do-i-create-a-bot) |
| `source` | :heavy_check_mark: | https://pcworms.blog.ir/rss/ | `URL` | Source of RSS feeds |
| `language` | :heavy_check_mark: | en-us | `string` | The language name that stored in `strings.json` or `Default-strings.json` file |
| `strings-file` | :heavy_check_mark: | Default-strings.json | `path` | A `Json` file that contains all languages and strings that your bot need |
| `log-level` | :heavy_check_mark: | `info` | `info`, `warning`, `error`, `critical` | Log level |
| `log-file` | | log.log | `path` | optionally you can redirect logs to a file |
| `db-path` | :heavy_check_mark: | db.lmdb | `Directory` | Directory of [LMDB database](https://en.wikipedia.org/wiki/Lightning_Memory-Mapped_Database) |
| `bug-reporter` | | `off` | `off`, `offline`, `online` |Bug-reporter is a service that count exceptions. If value is `online` you must install Cherrypy. Read [Bug-Reporter in Readme.md](../README.md#beetle-bug-reporter-). Following configuration needed if using bug-reporter |
| `reporter-config-file` | | Bug-reporter.conf | `path` | Another config file that contains [Cherrypy configuration](https://docs.cherrypy.org/en/latest/config.html) |
| `bugs-file` | :white_check_mark: | ./bugs.json | `path` | Required if your using Bug reporter (`offline` or `online` mode) |
| `use-git` | | `false` | `boolean` | Bug-reporter can use git to get repository information like commit or source repository, then it can generate a link to line that exception raised. |
| `git-source` | | https://github.com/bsimjoo/Telegram-RSS-Bot | `URL` | If your using a custom repository then you can specify your repository url here |
| `git-path` | | `/usr/bin/git` | `path` | If git is not in `PATH` environment then you set its path here. |
