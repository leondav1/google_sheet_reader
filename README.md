# Google sheet reader

Первое, что нужно сделать, это клонироать репозиторий:
```angular2html
$ https://github.com/leondav1/google_sheet_reader.git
$ cd google_sheet_reader
```
Создайте виртуальную среду для установки зависимостей и активируйте ее:
```angular2html
$ python -m venv env
$ source env/bin/activate
```
Затем установите зависимости:
```angular2html
(env)$ pip install -r requirements.txt
```
Настройте Google Workspac
Перейти на страницу https://developers.google.com/workspace/guides/get-started
и настройте Google Workspace
После насройки web клиента скачайте `client_secret_...json`, переименуйте его в `client_secret.json` и переместите в папку проекта

Создайте файл `.env`
```angular2html
touch .env
sudo nano .env
```
и добавьте в него подключение к БД (у вас должна быть установлена БД postgresql):
```angular2html
CONNECT_DB='postgresql://login:password@localhost:5432/your_name_db'
```
Для отправки сообщения необходимо:
Зарегистрировать телеграм бота в BotFather
Добавить в `.env` файл следующие переменные:
```angular2html
TOKEN=ЗДЕСЬ_ТОКЕН_КОТОРЫЙ_ВЫДАЛ_BotFather
CHAT_ID=ЗДЕСЬ_ЧИСЛО
```
Сборка проекта Docker
```angular2html
docker build -t google_sheet_reader .
```
Запуск контейнера Docker
```angular2html
docker run --network="host" -i -t google_sheet_reader
```
