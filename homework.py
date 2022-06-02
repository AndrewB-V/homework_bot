import logging
import os
import time

import requests
import telegram
import dotenv

import exceptions

dotenv.load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f'OAuth {PRACTICUM_TOKEN}'}
VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания."
}


logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except exceptions.MessageError:
        logger.error("Ошибка при отправке сообщения")
    finally:
        logger.info("Сообщение отправлено")


def get_api_answer(current_timestamp):
    """Получение данных с API YP."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    try:
        logger.info("отправляем api-запрос")
        data = {
            'url': ENDPOINT,
            'headers': HEADERS,
            'params': params
        }
        response = requests.get(**data)

    except ValueError as error:
        logger.error(f'{error}: не получили api-ответ')
        raise error
    error_message = (
        f'Проблемы соединения с сервером'
        f'ошибка {response.status_code}'
    )
    if response.status_code == requests.codes.ok:
        return response.json()
    logger.error(error_message)
    raise TypeError(error_message)


def check_response(response) -> dict:
    """Проверка данные api."""
    homework_error = "Домашняя работа не найдена!"
    dict_error = "dict KeyError"
    if isinstance(response, dict) is False:
        raise TypeError("api answer is not dict")
    try:
        homework_list = response["homeworks"]
    except KeyError:
        logger.error(dict_error)
        raise KeyError(dict_error)
    try:
        homework_list[0]
    except IndexError:
        logger.error(homework_error)
        raise IndexError(homework_error)
    return homework_list


def parse_status(homework):
    """Выделяет статут домашней работы."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    if homework_status is not None:
        verdict = VERDICTS[homework_status]
    else:
        raise KeyError("Ошибка словаря")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    env_error = "Ошибка в переменных окружения"
    if not check_tokens():
        logger.critical(env_error)
        os.system.exit(0)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    tmp_status = None
    errors = True
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            homework_status = homework.get("status")
            if homework_status != tmp_status:
                tmp_status = homework_status
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.debug("Статус ДЗ не изменился")
                current_timestamp = homework.get("current timestamp")
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if str(error) != errors:
                send_message(bot, error)
                errors = str(error)
            logger.error(error)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='logger.log',
        filemode='w',
        format='%(asctime)s - %(levelname)s - \
 %(message)s- %(name)s - %(lineno)d'
    )
    main()
