from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

from server_list import server_list

Base = declarative_base()


class Config(Base):
    __tablename__ = 'configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    expire_date = Column(DateTime, nullable=False)
    speed = Column(Integer, nullable=False)
    server_id = Column(Integer, ForeignKey('servers.id'), nullable=False)

    def __repr__(self):
        return f"<Config(id={self.id}, name='{self.name}', expire_date='{self.expire_date}', speed='{self.speed}')>"


class Server(Base):
    __tablename__ = 'servers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String, nullable=False)
    password = Column(String, nullable=False)
    configs = relationship('Config', backref='server', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Server(id={self.id}, ip='{self.ip}', password='{self.password}')>"


def setup_database():
    engine = create_engine('sqlite:///vpn_database.db')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    keys = server_list.keys()
    for key in keys:
        server = Server(ip=key, password=server_list[key])
        session.add(server)
    session.commit()
    return engine


if __name__ == "__main__":
    engine = setup_database()
    Session = sessionmaker(bind=engine)
    session = Session()

    server = Server(ip="192.168.1.1", password="securepassword")
    config1 = Config(name="Config1", expire_date=datetime(2024, 1, 1), speed=100, server=server)
    config2 = Config(name="Config2", expire_date=datetime(2024, 6, 1), speed=200, server=server)

    session.add(server)
    session.commit()

    for server in session.query(Server).all():
        print(server)
        for config in server.configs:
            print(config)