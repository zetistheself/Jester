import random
import string
import os
import server_manager

from server_list import server_list
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean, delete
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, timedelta

Base = declarative_base()


def setup_database():
    engine = create_engine(f"sqlite:///{os.path.abspath('vpn_database.db')}")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)  # создаём sessionmaker один раз

    with Session() as session:  # используем его здесь
        for ip, password in server_list.items():
            if session.query(Server).filter_by(ip=ip).first() is None:
                session.add(Server(ip=ip, password=password))
                session.commit()

    return engine


def generate_unique_key(session, length: int = 6) -> str:
    while True:
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        exists = session.query(UserTariff).filter_by(vpn_key=key).first()
        if not exists:
            return key


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    tariffs = relationship('UserTariff', back_populates='user', cascade="all, delete-orphan")
    payments = relationship('Payments', back_populates='user', cascade="all, delete-orphan")


class UserTariff(Base):
    __tablename__ = 'user_tariffs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    tariff_name = Column(String, nullable=False)
    uuid = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    vpn_key = Column(String, nullable=False)
    speed = Column(Integer, nullable=False)
    server_id = Column(Integer, ForeignKey('servers.id'), nullable=False)

    user = relationship('User', back_populates='tariffs')
    payment = relationship('Payments', back_populates='tariff', uselist=False)


class Payments(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    payment_id = Column(String, unique=True, nullable=False)
    config_was_generated = Column(Boolean, default=False)
    amount = Column(String, nullable=False)
    speed = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    tariff_id = Column(Integer, ForeignKey('user_tariffs.id'))

    tariff = relationship('UserTariff', back_populates='payment')
    user = relationship('User', back_populates='payments')


class Server(Base):
    __tablename__ = 'servers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String, nullable=False)
    password = Column(String, nullable=False)
    user_tariffs = relationship('UserTariff', backref='server', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Server(id={self.id}, ip='{self.ip}', password='{self.password}')>"


class ServerOrdering(Base):
    __tablename__ = 'serverordering'

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey('servers.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    payment_id = Column(String, nullable=False)
    speed = Column(Integer, nullable=False)


engine = setup_database()
Session = sessionmaker(bind=engine)


def check_config_was_generated(payment_id):
    session = Session()
    try:
        return session.query(Payments).filter(Payments.payment_id == payment_id).first().config_was_generated
    except Exception:
        return False
    finally:
        session.close()


def get_user_tariffs(user_id: int):
    session = Session()
    try:
        return session.query(UserTariff).filter(UserTariff.user_id == user_id).all()
    except Exception as e:
        print(f"Error fetching user tariffs: {e}")
        return []
    finally:
        session.close()


def add_payment(user_id, payment_id, amount, speed):
    session = Session()
    try:
        payment = Payments(user_id=user_id, payment_id=payment_id, amount=amount, speed=speed)
        session.add(payment)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error adding payment: {e}")
    finally:
        session.close()


def add_user_tariff(user_id, speed, payment_id):
    session = Session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            user = User(id=user_id)
            session.add(user)
            session.commit()

        uuid = generate_unique_key(session).lower()

        server_ordering = session.query(ServerOrdering).filter(ServerOrdering.payment_id == payment_id).first()
        server = session.query(Server).get(server_ordering.server_id)

        key = server_manager.create_vpn_config(uuid, speed, server)
        if not key:
            return "Operation blocked", ''

        tariff = UserTariff(
            user_id=user.id,
            tariff_name=str(speed) + " мбит/сек",
            uuid=uuid,
            expires_at=datetime.now() + timedelta(days=30),
            vpn_key=key,
            speed=speed,
            server_id=server.id,
        )
        user.tariffs.append(tariff)

        payment = session.query(Payments).filter(Payments.payment_id == payment_id).first()
        if payment:
            payment.config_was_generated = True
            tariff.payment = payment

        session.delete(server_ordering)
        session.commit()
        return "OK", key
    finally:
        session.close()


def delete_old_orderings(session):
    ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)

    session.execute(
        delete(ServerOrdering).where(ServerOrdering.created_at < ten_minutes_ago)
    )
    session.commit()
