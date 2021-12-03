#!/usr/bin/env python3

import sys
import logging
import subprocess
import datetime
import time
from threading import Thread, Lock
import mysql.connector as mysql
from telegram import Update, ForceReply , Bot, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from enum import Enum
from googlesearch import search

import config

class Cmd(Enum):
    HELP = 0
    SET  = 1
    DEL  = 2
    QRY  = 3
    FORT = 4
    STRT = 5
    TZ   = 6

cmd_strings = {}
cmd_strings[Cmd.HELP] = "/help"
cmd_strings[Cmd.SET]  = "/set_alarm"
cmd_strings[Cmd.DEL]  = "/delete_alarm"
cmd_strings[Cmd.QRY]  = "/query_alarms"
cmd_strings[Cmd.FORT] = "/fortune"
cmd_strings[Cmd.STRT] = "/start"
cmd_strings[Cmd.TZ]   = "/timezone"


class AlarmItem:
    def __init__(self, a_id, c_id, t_stamp, t_str, a_info):
        self.alarm_id = a_id
        self.chat_id = c_id
        self.timestamp = t_stamp
        self.time_str = t_str
        self.alarm_info = a_info

    def str(self):
        return ("Alarm ID: " + str(self.alarm_id) + " Chat Id: " + str(self.chat_id) +
                " Timestamp: " + str(self.timestamp) + " Date: " + self.time_str + " Text: " + self.alarm_info)
    def query_str(self):
        return ("Alarm ID: " + str(self.alarm_id) +
                ", " + self.time_str + ", " + self.alarm_info)
    alarm_id = 0
    alarm_id = 0
    chat_id = 0
    timestamp = 0
    time_str = ""
    alarm_info = ""

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

def is_valid_user(chat_id: int) -> bool:
    if chat_id in config.valid_chats:
        return True
    return False

def sql_connect() -> None:
    global db
    global cursor

    db_mutex.acquire()

    db = mysql.connect(
        host = "localhost",
        user = config.user,
        passwd = config.password ,
        database = 'MANTZBOT'
    )

    cursor = db.cursor()

def sql_disconnect() -> None:
    cursor.close()
    db.close()

    db_mutex.release()

def parse_command(update: Update):
    command = ""
    chat_id = 0
    result = 0
    message = None

    if update.message != None:
        command = update.message.text
        chat_id = update.message.chat.id
        message = update.message
    elif update.edited_message != None:
        command = update.edited_message.text
        chat_id = update.edited_message.chat.id
        message = update.edited_message
    else:
        result = -1
        logging.info("Error parsing command")

    return message, command, chat_id, result

def unknown_cmd(update: Update, context: CallbackContext) -> None:
    #Unknown command, do a google search with the provided string
    message, command, _, _ = parse_command(update)

    try:
        for i in search(query=command, stop = 1, pause = 2):
            res = i

        message.reply_text("Please type <b>/help</b> for available commands\n" +
            "search result for " + command + "\n" + res,
            parse_mode = ParseMode.HTML)
    except Exception as e:
        print(str(e))
        message.reply_text("Please type <b>/help</b> for available commands", parse_mode = ParseMode.HTML)

def start_cmd(update: Update, context: CallbackContext) -> None:
    message, _, chat_id, _ = parse_command(update)
    message.reply_text("Hello " + update.effective_user.first_name + "!. Chat ID is " + str(chat_id))

def help_cmd(update: Update, context: CallbackContext) -> None:
    message = parse_command(update)[0]
    message.reply_text("These are the supported commands:\n" +
            "<b>" + cmd_strings[Cmd.STRT] + "</b>" + "\n" +
            "\t\tSay hello to MantzBot\n" +
            "<b>" + cmd_strings[Cmd.FORT] + "</b>" + "\n" +
            "\tGet a fortune cookie from fortune-mod (possibly NSFW)\n" +
            "<b>" + cmd_strings[Cmd.SET] + "</b>" + "\n" +
            "\tSet an alarm notification. For example:\n" +
            "\t" + cmd_strings[Cmd.SET] + " 25/03/2021 08:00 - Independence Day\n" +
            "<b>" + cmd_strings[Cmd.QRY] + "</b>" + "\n" +
            "\tGet a list of active alarms for this chat\n" +
            "<b>" + cmd_strings[Cmd.DEL] + "</b>" + "\n" +
            "\tDelete an alarm notification, using the Alarm's ID. For example:\n" +
            "\t" + cmd_strings[Cmd.DEL] + " 17\n" +
            "<b>" + cmd_strings[Cmd.TZ] + "</b>" + "\n" +
            "\tSet or display the timezone offset for this chat. For example:\n" +
            "\t" + cmd_strings[Cmd.TZ] + " +3\n" +
            "<b>" + cmd_strings[Cmd.HELP] + "</b>" + "\n" +
            "\tDisplay this help message\n",
            parse_mode = ParseMode.HTML)

def fortune_cmd(update: Update, context: CallbackContext) -> None:
    message = parse_command(update)[0]
    ret = subprocess.getoutput('fortune -a')
    message.reply_text(ret)

def get_printable_alarms(chat_id: int) -> str:
    response = ""

    sql_connect()

    for a in alarm_list:
        if a.chat_id == chat_id:
            response += a.query_str()
            response += "\n"

    if response == "":
        response = "No active alarms"

    sql_disconnect()

    return response

def query_alarms_cmd(update: Update, context: CallbackContext) -> None:
    message, command, chat_id, result = parse_command(update)

    if result != 0:
        message.reply_text("Error parsing command")
        return

    message.reply_text(get_printable_alarms(chat_id))

def delete_alarm_cmd(update: Update, context: CallbackContext) -> None:
    message, command, chat_id, result = parse_command(update)

    if result != 0:
        message.reply_text("Error parsing command")
        return

    error = False
    timestamp = 0
    response = "Please provide a valid Alarm ID"

    args = command.split(" ", 1)

    sql_connect()

    try:
        alarm_id = int(args[1])
    except:
        error = True

    if error == False:
        for a in alarm_list:
            if a.chat_id == chat_id and a.alarm_id == alarm_id:
                alarm_list.remove(a)
                response = "Alarm deleted"

                try:
                    query = "DELETE FROM ALARMS WHERE id = "+ str(alarm_id) +" AND chat_id = " + str(chat_id) +" ;"
                    cursor.execute(query)
                    db.commit()
                except:
                    logger.warning("Error removing alarm from database")
                    response = "Error removing alarm from database"

    sql_disconnect()
    message.reply_text(response)

def set_alarm_cmd(update: Update, context: CallbackContext) -> None:
    message, command, chat_id, result = parse_command(update)

    if result != 0:
        message.reply_text("Error parsing command")
        return

    error = False
    timestamp = 0
    response = "Alarm format is DD/MM/YYY HH:MM - Alarm tag"

    args_tmp = command.split(" ", 1)

    if len(args_tmp) != 2:
        error = True
    else:
        args = args_tmp[1].split("-", 1)

        if len(args) != 2:
            error = True
        else:
            try:
                alarm_time = args[0].strip()
                alarm_info = args[1].strip()

                timestamp = int(round((time.mktime(datetime.datetime.strptime(alarm_time, "%d/%m/%Y %H:%M").timetuple()))))
            except:
                error = True;

    if error == False:
        sql_connect()

        query = "INSERT INTO ALARMS (timestamp, chat_id, date_str, alarm_str) VALUES (%s, %s, %s, %s)"
        values = (str(timestamp), str(chat_id), alarm_time, alarm_info)
        logger.info("query values " + str(timestamp) + " " + str(chat_id) + " " + alarm_time + " " + alarm_info)

        try:
            cursor.execute(query, values)

            db.commit()
            a_item = AlarmItem(cursor.lastrowid, chat_id, timestamp, alarm_time, alarm_info)
            add_alarm_to_alarm_list(a_item)

            response = "Alarm registered, alarm ID: " + str(a_item.alarm_id)
            logger.info("Alarm registered " + a_item.str())
        except Exception as e:
            logger.warning("Error adding alarm to database: " + str(e))
            response = "Error adding alarm to database"

        sql_disconnect()

    message.reply_text(response)

def timezone_cmd(update: Update, context: CallbackContext) -> None:
    message = parse_command(update)[0]

    message.reply_text("placeholder")

def add_alarm_to_alarm_list(alarm: AlarmItem):
    index = 0;
    for a in alarm_list:
        if a.timestamp > alarm.timestamp:
            break;
        index += 1

    alarm_list.insert(index, alarm)

def populate_alarm_list():
    sql_connect()

    query = "SELECT * FROM ALARMS"
    cursor.execute(query)

    res = cursor.fetchall()

    for x in res:
        a_item = AlarmItem(x[0], x[2], x[1], x[3], x[4])
        add_alarm_to_alarm_list(a_item)

    sql_disconnect()

def display_alarm_list() -> None:
    for alarm in alarm_list:
        print(alarm.str())

def timer_thread():
    while True:
        ts = datetime.datetime.now().timestamp()
        logger.info("Timer loop")

        sql_connect()

        while len(alarm_list) > 0 and alarm_list[0].timestamp < ts:
            alarm = alarm_list.pop(0)
            message = alarm.time_str + ", " + alarm.alarm_info + " (Alarm id: " + str(alarm.alarm_id) + ")"

            bot.send_message(alarm.chat_id, message)

            try:
                query = "DELETE FROM ALARMS WHERE id = " + str(alarm.alarm_id)
                cursor.execute(query)
                db.commit()
            except:
                logger.warning("Could not remove alarm from database, id " + str(alarm.alarm_id))

        sql_disconnect()

        time.sleep(30)

def init_sql_tables() -> int:
    sql_connect()
    ret = 0;

    cursor.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = 'ALARMS'""")

    if cursor.fetchone()[0] == 1:
        logger.info("Table found")
    else:
        try:
            cursor.execute("CREATE TABLE ALARMS (id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, "
                "timestamp INT, "
                "chat_id BIGINT, "
                "date_str VARCHAR(20), "
                "alarm_str VARCHAR(255))")
            logger.info("Table created")
        except:
            logger.warning("Could not create table")
            ret = -1

    sql_disconnect()
    return ret

def main() -> None:
    global bot
    global alarm_list
    global db_mutex

    updater = Updater(config.token)
    bot = Bot(config.token)
    alarm_list = []

    logger.info("Bot started")

    db_mutex = Lock()

    init_sql_tables()

    populate_alarm_list()

    try:
        t = Thread(target = timer_thread, args = ())
        t.start()
    except:
        logger.error("Can't start timer thread")
        sys.exit()

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_cmd))
    dispatcher.add_handler(CommandHandler("fortune", fortune_cmd))
    dispatcher.add_handler(CommandHandler("set_alarm", set_alarm_cmd))
    dispatcher.add_handler(CommandHandler("query_alarms", query_alarms_cmd))
    dispatcher.add_handler(CommandHandler("delete_alarm", delete_alarm_cmd))
    dispatcher.add_handler(CommandHandler("help", help_cmd))
    dispatcher.add_handler(CommandHandler("timezone", timezone_cmd))

    dispatcher.add_handler(MessageHandler(Filters.command, unknown_cmd))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
