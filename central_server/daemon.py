import datetime
import database
import sqlalchemy

from apscheduler.schedulers.blocking import BlockingScheduler

engine = database.setup_database()
Session = sqlalchemy.orm.sessionmaker(bind=engine)


def check_database():
    session = Session()
    configs = session.query(database.Config).all()
    for config in configs:
        if config.expire_date < datetime.datetime.now():
            session.delete(config)
            print(f"Deleted expired config: {config}")
    session.commit()


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(check_database, 'interval', days=1)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
