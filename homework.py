import logging
import os
import time
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv
from http import HTTPStatus as HTTP


load_dotenv()


"""Set logger."""
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'main.log',
    maxBytes=50000000,
    backupCount=5
)
handler2 = StreamHandler()
logger.addHandler(handler)
logger.addHandler(handler2)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s ((%(funcName)s))'
)
handler.setFormatter(formatter)


"""Get environment varibles."""
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot: telegram.Bot, message: str):
    """Бот отправляет сообщение о статусе."""
    try:
        logger.info('Sending message')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Message was sent')
    except Exception as error:
        raise Exception(f'Failed to send the message. Error: {error}')


def get_api_answer(current_timestamp):
    """Получаем полный список домашек."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logger.info('Connecting API')
        response = requests.get(ENDPOINT, params=params, headers=HEADERS)
    except Exception as error:
        raise Exception(f'Failed to connect to API. Error: {error}')

    if response.status_code != HTTP.OK:
        raise Exception('Api answer is not 200.')

    return response.json()


def check_response(response):
    """Получаем список домашек."""
    if not isinstance(response, dict):
        raise TypeError('Homeworks are not dict.')

    homeworks = response.get('homeworks')

    if 'homeworks' not in response and 'current_date' not in response:
        raise KeyError('Response dont have required keys.')

    if 'homeworks' not in response:
        raise KeyError("'homeworks' key is missing.")

    if not isinstance(homeworks, list):
        raise TypeError('homeworks object is not a list.')

    return homeworks


def parse_status(homework):
    """Генерируем строку для отправки."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(f'Status {homework_status} is not valid')
        raise KeyError('Unknown key.')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка на наличие всех переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    previous_status = ''

    while True:
        try:
            answer = get_api_answer(current_timestamp)
            homeworks = check_response(answer)
            if homeworks:
                homework = homeworks[0]
            message = parse_status(homework)
            if message != previous_status:
                send_message(bot, message)
            else:
                logger.debug('Message is not unique')

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
