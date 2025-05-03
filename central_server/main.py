import os
import telebot
import redis
import paramiko
import subprocess
import database
import datetime

from dotenv import load_dotenv
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker


load_dotenv()

bot = telebot.TeleBot(os.getenv("TOKEN"))

r = redis.Redis()

engine = database.setup_database()


def is_latin(text):
    return all('a' <= char.lower() <= 'z' or char.isspace() for char in text)


@bot.message_handler(commands=['start'])
def start_message(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("Создать VPN"))
    bot.send_message(message.chat.id, "Привет администратор! Я бот для управления Jester VPN.", reply_markup=markup) 


@bot.message_handler(content_types=['text'])
def handle_text(message):
    status = r.get(message.chat.id)
    if status:
        status = status.decode()
    if message.text == "Создать VPN":
        bot.send_message(message.chat.id, "Введите имя покупателя(Латиница)")
        r.set(message.chat.id, "Waiting_for_name", ex=86400)
    elif status == 'Waiting_for_name':
        name = message.text
        if is_latin(name):
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(text="50mbit", callback_data=50))
            markup.add(telebot.types.InlineKeyboardButton(text="100mbit", callback_data=100))
            markup.add(telebot.types.InlineKeyboardButton(text="300mbit", callback_data=300))
            bot.send_message(message.chat.id, "Теперь выберите максимальную пропускную способность", reply_markup=markup)
            r.set(message.chat.id, name, ex=86400)
        else:
            bot.send_message(message.chat.id, "Имя должно содержать только латинские символы.")
    else:
        bot.send_message(message.chat.id, "Я не знаю такой команды.")


def check_config_availability(session, speed):
    servers = session.query(database.Server).all()
    if not servers:
        return False
    for server in servers:
        speed_sum = session.query(func.sum(database.Config.speed)).filter(database.Config.server_id == server.id).scalar() or 0
        if speed_sum + speed <= 600:
            return server
    return False


def get_available_port(session, server):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server.ip, username='root', password=server.password)
    stdin, stdout, stderr = client.exec_command("comm -23 <(seq 1024 65535 | sort) <(ss -tuln | awk '{print $5}' | grep -oE '[0-9]+$' | sort -n | uniq) | head -n 1")
    if stderr.read().decode() != '':
        print(f"Error: {stderr.read().decode()}")
        return None
    return int(stdout.read().strip())


def get_error_message(stderr):
    error = stderr.read().decode()
    if error != '':
        print(f"Error: {error}")
    return error


def run_vpn_script(server, port, name, speed):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server.ip, username='root', password=server.password)
    stdin, stdout, stderr = client.exec_command(f"cd Jester && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python3 Jester/create_vpn_user.py {name} {port} {speed}")
    print(stdout.read().decode())
    get_error_message(stderr)


def create_vpn_config(session, name, speed, server):
    port = get_available_port(session, server)
    if not port:
        bot.send_message(server.ip, "Нет доступных портов.")
        return
    run_vpn_script(server, port, name, speed)
    config = database.Config(name=name, speed=speed, server=server, expire_date=datetime.datetime.now() + datetime.timedelta(days=30))
    session.add(config)
    session.commit()
    return config


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data in ["50", "100", "300"]:
        name = r.get(call.message.chat.id)
        if name:
            speed = int(call.data)
            session = sessionmaker(bind=engine)()
            if check_config_availability(session, speed):
                server = check_config_availability(session, speed)
                if not server:
                    bot.send_message(call.message.chat.id, "Нет доступных серверов.")
                    return
                create_vpn_config(session, name, speed, server)

            r.delete(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "Произошла ошибка. Попробуйте снова.")
    else:
        bot.send_message(call.message.chat.id, "Я не знаю такой команды.")


bot.polling(none_stop=True)
