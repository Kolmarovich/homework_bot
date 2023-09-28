import telegram
import time
import requests
import logging
import os
import exceptions
from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception:
        logging.error('Ошибка отправки сообщения в Telegram')
        raise exceptions.MessageError('Не удалось отправить сообщение')
    else:
        logging.debug('Отправка сообщения прошла успешно')


def get_api_answer(timestamp):
    """Ответ API."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            url=ENDPOINT, headers=HEADERS, params=payload
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            logging.error('Нет доступа к API')
            raise exceptions.IncorrectResponseCode(
                'Не удалось получить ответ от API')
        return homework_statuses.json()
    except requests.RequestException as error:
        logging.error(f"Произошла ошибка при выполнении запроса: {error}")


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    if "homeworks" not in response and "current_date" not in response:
        logging.error('Отсутствие ожидаемых ключей в ответе API')
        raise exceptions.EmptyResponse('Пустой ответ API.')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Cтруктура данных не является списком.')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутсвует ключ - homework_name')
    if 'status' not in homework:
        raise ValueError('В ответе отсутсвует статус работы status')
    homework_name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        logging.error('Неожиданный статус домашней работы, '
                      'обнаруженный в ответе API')
        raise exceptions.UndocumentedStatus('Недокументированный статус'
                                            ' домашней работы')
    for key, verdict in HOMEWORK_VERDICTS.items():
        if status == key:
            return (f'Изменился статус проверки работы "{homework_name}". '
                    f'{verdict}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует необходимое кол-во'
                         ' переменных окружения')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                new_homework = homework[0]
                status = parse_status(new_homework)
                send_message(bot, status)
            else:
                logging.debug('Отсутствие в ответе новых статусов')
                message = 'Нет новых статусов'
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s, %(levelname)s, Путь - %(pathname)s, '
            'Файл - %(filename)s, Функция - %(funcName)s, '
            'Номер строки - %(lineno)d, %(message)s'
        ),
        handlers=[logging.FileHandler('log.txt', encoding='UTF-8'),
                  logging.StreamHandler()])
    main()
