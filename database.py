import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, Date, String

load_dotenv()

connect = os.getenv('CONNECT_DB')
engine = create_engine(connect)

Base = declarative_base()


def my_default():
    return 5


class Supply(Base):
    __tablename__ = 'Supplies'

    id = Column(Integer, primary_key=True)
    order = Column(Integer, nullable=False)
    usd_price = Column(Float)
    delivery = Column(Date)
    rub_price = Column(Float)


# Таблица временных (новых) данных
class TemporarySupply(Base):
    __tablename__ = 'TemporarySupplies'

    id = Column(Integer, primary_key=True)
    order = Column(Integer, nullable=False)
    usd_price = Column(Float)
    delivery = Column(Date)
    rub_price = Column(Float)


class Counter(Base):
    __tablename__ = 'Counters'

    id = Column(Integer, primary_key=True)
    count = Column(Integer, nullable=False, default=0)


Base.metadata.create_all(engine)
