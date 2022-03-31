import logging
import os
import sys
import time
from http import HTTPStatus
from urllib.error import HTTPError

import requests
from dotenv import load_dotenv
from telegram import Bot

from exceptions import EmptyList, HTTPStatusCodeIncorrect, NeedToken

load_dotenv()


PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES: dict = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message: str) -> None:
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.info(f'Отправлено сообщение: {message}')
    except Exception as error:
        logging.error(f'Cбой при отправке сообщения, ошибка {error}')


def get_api_answer(current_timestamp: int) -> dict:
    """Получение ответа от API."""
    timestamp: int = current_timestamp or int(time.time())
    params: dict = {'from_date': timestamp}
    headers: dict = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    try:
        response: dict = requests.get(
            url=ENDPOINT,
            headers=headers,
            params=params
        )
    except requests.RequestException as error:
        message_error = f'Сбой при запросе к endpoint: {error}'
        logging.error(message_error, exc_info=True)
        raise
    except HTTPError as error:
        logging.error(error, exc_info=True)
    if response.status_code != HTTPStatus.OK:
        logging.error(
            f'Статус ответа API не 200, статус {response.status_code}'
        )
        raise HTTPStatusCodeIncorrect
    return response.json()


def check_response(response: dict) -> list:
    """Проверка ответа от API."""
    if not isinstance(response, dict):
        raise TypeError('Нужен словарь!')
    try:
        homeworks: list = response.get('homeworks')
    except Exception as error:
        logging.error(f'Ошибка в получении списка домашних работ, {error}')
    else:
        if not isinstance(homeworks, list):
            logging.error()
            raise TypeError('Нужен список!')
        if len(homeworks) == 0:
            logging.error('Empty homeworks list')
            raise EmptyList
        return homeworks


def parse_status(homework: dict) -> str:
    """Получение статуса работы."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except Exception as error:
        logging.error(f'Нет ключа в homework, {error}')
        raise KeyError
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error('Некорректный статус работы')
        raise KeyError


def check_tokens() -> bool:
    """Проверка необходимых токенов."""
    for i in [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]:
        if i is None:
            return False
        else:
            return True


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[logging.StreamHandler(sys.stdout)],
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    )

    last_message = []

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while check_tokens():
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            message = parse_status(homeworks[0])
            if message in last_message:
                logging.debug('Статус домашней работы не изменился')
            else:
                last_message.append(message)
                send_message(bot, message)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message not in last_message:
                last_message.append(message)
                send_message(bot, message)
            time.sleep(RETRY_TIME)
    else:
        logging.critical('Tokens!')
        raise NeedToken


if __name__ == '__main__':
    main()
