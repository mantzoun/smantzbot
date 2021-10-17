#!/usr/bin/env python3

import sys
import logging
import subprocess
import datetime
import time
from threading import Thread, Lock
import mysql.connector as mysql
from telegram import Update, ForceReply , Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

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

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello " + update.effective_user.username + "!")

def fortune_command(update: Update, context: CallbackContext) -> None:
    ret = subprocess.getoutput('fortune -a')
    update.message.reply_text(ret)

def query_alarms(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    response = ""

    db_mutex.acquire()

    for a in alarm_list:
        if a.chat_id == chat_id:
            response += a.query_str()
            response += "\n"

    if response == "":
        response = "No active alarms"

    bot.send_message(chat_id, response)

    db_mutex.release()

def set_alarm(update: Update, context: CallbackContext) -> None:
    if update.message != None:
        time_str = update.message.text[10:].split("-", 1)
        chat_id = update.message.chat.id
    elif update.edited_message != None:
        time_str = update.edited_message.text[10:].split("-", 1)
        chat_id = update.edited_message.chat.id
    else:
        logging.info("Error parsing command")
        return

    db_mutex.acquire()

    error = False
    timestamp = 0
    response = "Alarm format is DD/MM/YYY HH:MM - Alarm tag"

    if len(time_str) != 2:
        error = True
    else:
        try:
            dt = time_str[0].strip()
            at = time_str[1].strip()

            timestamp = int(round((time.mktime(datetime.datetime.strptime(dt, "%d/%m/%Y %H:%M").timetuple()))))
        except:
            error = True;

    if error == False:
        query = "INSERT INTO ALARMS (timestamp, chat_id, date_str, alarm_str) VALUES (%s, %s, %s, %s)"
        values = (str(timestamp), str(chat_id), dt, at)

        try:
            cursor.execute(query, values)

            db.commit()
            a_item = AlarmItem(cursor.lastrowid, chat_id, timestamp, dt, at)
            add_alarm_to_alarm_list(a_item)
            #display_alarm_list()
            response = "Alarm registered, alarm ID: " + str(a_item.alarm_id)
            logger.info("Alarm registered " + a_item.str())
        except:
            logger.warning("Error adding alarm to database")
            response = "Error adding alarm to database"

    db_mutex.release()

    bot.send_message(chat_id, response)

def add_alarm_to_alarm_list(alarm: AlarmItem):
    index = 0;
    for a in alarm_list:
        if a.timestamp > alarm.timestamp:
            break;
        index += 1

    alarm_list.insert(index, alarm)

def populate_alarm_list() -> None:
    query = "SELECT * FROM ALARMS"
    cursor.execute(query)

    res = cursor.fetchall()

    for x in res:
        a_item = AlarmItem(x[0], x[2], x[1], x[3], x[4])
        add_alarm_to_alarm_list(a_item)

def display_alarm_list() -> None:
    for alarm in alarm_list:
        print(alarm.str())

def timer_thread():
    while True:
        ts = datetime.datetime.now().timestamp()
        logger.info("Timer loop")
        db_mutex.acquire()
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

        db_mutex.release()

        time.sleep(30)

def main() -> None:
    global bot
    global alarm_list
    global db
    global cursor
    global db_mutex

    updater = Updater("BOT_KEY")
    bot = Bot("BOT_KEY")
    alarm_list = []

    logger.info("Bot started")

    db = mysql.connect(
        host = "localhost",
        user = "",
        passwd = "",
        database = 'MANTZBOT'
    )

    cursor = db.cursor()

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


    populate_alarm_list()
    #display_alarm_list()

    db_mutex = Lock()

    try:
        t = Thread(target = timer_thread, args = ())
        t.start()
    except:
        logger.error("Can't start timer thread")
        sys.exit()

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("fortune", fortune_command))
    dispatcher.add_handler(CommandHandler("set_alarm", set_alarm))
    dispatcher.add_handler(CommandHandler("query_alarms", query_alarms))

    #dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, show_help))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
