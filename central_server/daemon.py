import datetime
import database
import sqlalchemy
import paramiko
import telebot
import dotenv
import os
import psycopg2

from apscheduler.schedulers.blocking import BlockingScheduler

dotenv.load_dotenv()
TOKEN = os.getenv("TOKEN")

bot = telebot.TeleBot(TOKEN)

engine = database.setup_database()
Session = sqlalchemy.orm.sessionmaker(bind=engine)


def check_database():
    with Session() as session:
        configs = session.query(database.UserTariff).all()
        for config in configs:
            if config.expires_at < datetime.datetime.now():
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(config.server.ip, username='root', password=config.server.password)
                    client.exec_command(f"docker kill xray-{config.uuid} && docker rm xray-{config.uuid} && docker system prune -a -f && docker volume prune -f")
                    client.close()
                except Exception as e:
                    bot.send_message(950479413, f"Error cleaning up expired config on server {config}: {e}")
                    continue
                session.delete(config)
                print(f"Deleted expired config: {config}")
                bot.send_message(config.user_id, "📅 Ваш тарифный план истёк. Пожалуйста, приобретите новый, чтобы продолжить использовать VPN.")

        session.commit()


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(check_database, 'interval', days=1)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
