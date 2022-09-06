import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


load_dotenv()


"""Настройка логирования."""
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'main.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s ((%(funcName)s))'
)
handler.setFormatter(formatter)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')

RETRY_TIME = 20
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot: telegram.Bot, message: str):
    """Бот отправляет сообщение о статусе."""
    if message:
        bot.send_message(os.getenv('TELEGRAM_CHAT_ID'), message)


def get_api_answer(current_timestamp):
    """Получаем полный список домашек."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, params=params, headers=HEADERS)
    return response.json()


def check_response(response):
    """Получаем список домашек."""
    try:
        return response['homeworks']
    except Exception as error:
        logger.exception(error)


def parse_status(homeworks):
    """Генерируем строку для отправки."""
    try:
        homework = homeworks[0]
    except IndexError:
        return None

    homework_name = homework['homework_name']
    homework_status = homework['status']

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка на наличие всех переменных окружения."""
    varibles = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    return varibles
    # Finish it


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=os.getenv('TELEGRAM_TOKEN'))
    current_timestamp = int(time.time())
    previous_status = ''

    while True:
        try:
            answer = get_api_answer(current_timestamp)
            answer = get_api_answer(1)
            homeworks = check_response(answer)
            message = parse_status(homeworks)
            if message != previous_status:
                send_message(bot, message)

            current_timestamp = time.time()

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.exception(error)

        finally:
            previous_status = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
