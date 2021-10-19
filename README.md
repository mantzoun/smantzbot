# MantzBot

MantzBot is a Python3 script that implements a Telegram Bot.

## Installation

MantzBot depends on the following libraries:
   * sys
   * logging
   * subprocess
   * time
   * datetime
   * threading
   * enum
   * mysql.connector
   * telegram
   * telegram.ext

In addition, it requires credentials for a MySQL server, where it has full access to a database, created beforehand to be used by MantzBot.

## Configuration

Replace BOT_KEY with your Telegram HTTP API Token

```
updater = Updater("BOT_KEY")
bot = Bot("BOT_KEY")
```

Provide the database connection information to mysql.connector
```
db = mysql.connect(
    host = "localhost",
    user = "",
    passwd = "",
    database = "MANTZBOT"
)
```

## Usage     

```
./smantzbot.py
```

## License
[MIT](https://choosealicense.com/licenses/mit/)
