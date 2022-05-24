#!/usr/bin/env python3
import os
from datetime import datetime

import requests
import schedule
from sqlalchemy.exc import NoResultFound, DataError

from spreadsheet import main
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from database import Supply, Counter, TemporarySupply, engine

RANGE = 'B2:D10000'
COUNTER = 5  # Время запуска в секундах
URL = 'https://www.cbr-xml-daily.ru/daily_json.js'

session = sessionmaker(bind=engine)
s = session()


class OrdersList:
    def __init__(self):
        self.data = None  # данные из таблицы
        self.usd_daily = None  # курс доллара
        self.current_date = None  # текущая дата
        self.count_query = self.counter()  # счетчик количества строк в гугл таблице

    def check_cur_date(self):
        now = datetime.now().strftime('%Y-%m-%d')
        if now != self.current_date or self.current_date is None:
            self.current_date = now
            return False
        return True

    @staticmethod
    def exchange():
        """Функция получения курса доллара"""
        response = requests.get(URL).json()
        return response['Valute']['USD']['Value']

    @staticmethod
    def counter():
        """Подключение к таблице Counter
        В данной таблице хранится количество строк
        в Гугл таблице
        """
        count_query = s.query(Counter).first()
        if count_query is None:
            add_count = Counter(count=0)
            s.add(add_count)
            s.commit()
            count_query = s.query(Counter).first()
        return count_query

    def clear_table(self, model, count_update=False):
        try:
            s.query(model).delete(synchronize_session='fetch')
            if count_update:
                self.count_query.count = 0
            s.execute(f'ALTER SEQUENCE "{model.__name__}_id_seq" RESTART WITH 1')
            s.commit()
        except Exception:
            s.rollback()

    def table_filling(self, model, data, count_update=False):
        """Функция заполнения таблицы в БД"""
        for row in data:
            try:
                rub_price = round(float(row[1]) * self.usd_daily, 2)
                date = datetime.strptime(row[2], '%d.%m.%Y')
                new_row = model(order=row[0], usd_price=float(row[1]), delivery=date, rub_price=rub_price)
                s.add(new_row)
                s.commit()
            except (DataError, ValueError, IndexError):
                s.rollback()
                return False
        if count_update:
            self.count_query.count = len(data)
            s.commit()
        return True

    @staticmethod
    def send_telegram(messages: list):
        token = os.getenv('TOKEN')
        url = "https://api.telegram.org/bot"
        chat_id = os.getenv('CHAT_ID')
        url += token
        method = url + "/sendMessage"

        response = requests.post(method, data={
            "chat_id": chat_id,
            "text": messages
        })

        if response.status_code != 200:
            raise Exception("post_text error")

    def check_delivery_time(self, data):
        """Функция проверки просроченных задач с отправкой в телеграм"""
        now = datetime.now().strftime('%d.%m.%Y')
        message = f'Нарушены сроки поставки на {now}:\n\n'
        data_sort = sorted(data, key=lambda x: datetime.strptime(x[2], "%d.%m.%Y").strftime("%Y-%m-%d"))

        for row in data_sort:
            if row[2] < now:
                message += f'Заказ {row[0]}, срок поставки {row[2]}.\n'
            elif row[2] == now:
                message += f'Заказ {row[0]}, срок поставки истекает сегодня.\n'
            else:
                break
        self.send_telegram(messages=[message])

    def check_data(self):
        # Очистить данные, если excel таблица пустая
        if not self.data.get('values'):
            self.clear_table(Supply, count_update=True)
            return 'Таблица очищена'

        self.clear_table(TemporarySupply)

        rows = self.data['values']
        if [] in rows:
            return 'Некорректные данные. Проверьте записи в Гугл таблице'
        # Заполнение пустой таблицы в БД
        if self.count_query.count == 0:
            query = self.table_filling(Supply, rows, count_update=True)
            if not query:
                return 'Некорректные данные. Проверьте записи в Гугл таблице'
            return 'Таблица заполнена'

        # Заполнение обновлёнными данными временной таблицы в БД
        query = self.table_filling(TemporarySupply, rows)
        if not query:
            return 'Некорректные данные. Проверьте записи в Гугл таблице'

        # Поиск изменений
        text_query = text('("order", "usd_price", "delivery") '
                          'FROM (SELECT "Supplies".order, "Supplies".usd_price, "Supplies".delivery '
                          'FROM "Supplies" '
                          'UNION ALL SELECT "TemporarySupplies".order, "TemporarySupplies".usd_price, '
                          '"TemporarySupplies".delivery '
                          'FROM "TemporarySupplies") tb1 '
                          'GROUP BY "order", "usd_price", "delivery" '
                          'HAVING count(*) = 1 '
                          'ORDER BY "order"')
        union_query = s.query(text_query)
        orders_set = set()
        for item in union_query:
            items_list = item[0].replace('(', '').replace(')', '').split(',')
            orders_set.add(items_list[0])
        # Корректировка данных в таблице БД
        for order in orders_set:
            try:
                res = s.query(TemporarySupply).filter(TemporarySupply.order == order).one()
                rub_price = round(float(res.usd_price) * self.usd_daily, 2)
                # Обновить запись
                print('Обновление записи')
                update = s.query(Supply).filter(Supply.order == order).update(
                    {"usd_price": float(res.usd_price),
                     "delivery": res.delivery,
                     "rub_price": rub_price},
                    synchronize_session='fetch'
                )
                if not update:
                    # Создать запись
                    print('Создание записи')
                    add_order = Supply(order=order, usd_price=float(res.usd_price), delivery=res.delivery, rub_price=rub_price)
                    s.add(add_order)
                    self.count_query.count += 1
                s.commit()
            except NoResultFound:
                # Удалить запись
                print('Удаление записи')
                del_order = s.query(Supply).filter(Supply.order == order).one()
                s.delete(del_order)
                self.count_query.count -= 1
                s.commit()
        return 'Success'

    def run(self):
        print('start')
        self.data = main(RANGE)
        if not self.check_cur_date():
            self.usd_daily = self.exchange()
            self.check_delivery_time(self.data['values'])
        print(self.check_data())


if __name__ == '__main__':
    res = OrdersList()
    schedule.every(COUNTER).seconds.do(res.run)
    while True:
        schedule.run_pending()
