FROM python:3.7.9-slim-buster

RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && pip install psycopg2

RUN mkdir /app

COPY requirements.txt /app/

RUN python -m pip install -r /app/requirements.txt

COPY .env /app/

COPY client_secret.json /app/

COPY database.py /app/

COPY main.py /app/

COPY spreadsheet.py /app/

COPY token.json /app/

WORKDIR /app

ENTRYPOINT ["python", "main.py"]
